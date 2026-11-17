import os
import sys
import time
import math
import queue
import threading
import datetime
import codecs
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import serial  # type: ignore
import serial.tools.list_ports  # type: ignore


def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


BAUD = 115200

BG, PANEL, FG, MUTED = "#1b1b1b", "#242424", "#d4d4d4", "#8a8a8a"
TEAL, AMBER, CORAL, GREEN, GRAY = "#5b9aa0", "#d9a441", "#d0605a", "#6b9b6b", "#3a3a3a"
TEAL_HI, CARD, EDGE = "#7cc4c9", "#202020", "#303030"


def iso_box(c, x, y, w, d, h, top, left, right, tag):
    ax, ay = w * 0.87, -w * 0.5
    bx, by = -d * 0.87, -d * 0.5
    p = (x, y)
    a = (x + ax, y + ay)
    b = (x + bx, y + by)
    ab = (x + ax + bx, y + ay + by)

    def high(point):
        return (point[0], point[1] - h)

    def flat(*points):
        return [v for point in points for v in point]

    c.create_polygon(flat(p, a, high(a), high(p)), fill=right, outline=BG, tags=tag)
    c.create_polygon(flat(p, b, high(b), high(p)), fill=left, outline=BG, tags=tag)
    c.create_polygon(flat(high(p), high(a), high(ab), high(b)), fill=top, outline=BG, tags=tag)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            self.iconbitmap(resource_path("laserlink.ico"))
        except tk.TclError:
            pass

        self.title("Laser Link - Receiver")
        self.configure(bg=BG)
        self.geometry("1100x860")
        self.minsize(900, 700)

        self.ser = None
        self.port = ""
        self.want = False
        self.reader_thread = None
        self.stop_event = threading.Event()
        self.events = queue.Queue()
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")

        self.conn = "disconnected"
        self.received_bytes = 0
        self.received_chars = 0
        self.errors = 0
        self.last_data_time = 0.0
        self.activity = []
        self.packets = []
        self.s, self.ox, self.oy = 1.0, 0.0, 0.0

        self.style_ui()
        self.build()
        self.refresh_ports(auto=True)
        self.draw_static()
        self.tick()
        self.process_events()

    # ---------- UI styling ----------
    def style_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, bordercolor=GRAY)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("TButton", background=PANEL, foreground=FG, padding=6, borderwidth=1)
        style.map("TButton", background=[("active", GRAY)])
        style.configure("TCombobox", fieldbackground=PANEL, foreground=FG, background=PANEL)
        style.configure("Horizontal.TProgressbar", background=TEAL, troughcolor=PANEL)

    def build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(top, text="LASER LINK", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(top, text="  receiver", style="Muted.TLabel", font=("Segoe UI", 12)).pack(side="left")

        self.badge = tk.Canvas(top, width=170, height=24, bg=BG, highlightthickness=0)
        self.badge.pack(side="right")
        self.dot = self.badge.create_oval(4, 5, 18, 19, fill=GRAY, outline="")
        self.btxt = self.badge.create_text(26, 12, anchor="w", fill=FG, text="disconnected", font=("Segoe UI", 10))

        self.cv = tk.Canvas(self, width=940, height=440, bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=12, pady=4)
        self.cv.bind("<Configure>", self.on_resize)

        row = ttk.Frame(self)
        row.pack(fill="x", padx=12, pady=4)
        ttk.Label(row, text="Port").pack(side="left")
        self.portbox = ttk.Combobox(row, width=9)
        self.portbox.pack(side="left", padx=6)
        self.cbtn = ttk.Button(row, text="Connect", width=11, command=self.toggle)
        self.cbtn.pack(side="left")
        ttk.Button(row, text="Refresh", command=self.refresh_ports).pack(side="left", padx=6)
        ttk.Label(row, text="   Serial baud").pack(side="left")
        self.baud_label = ttk.Label(row, text=str(BAUD), style="Muted.TLabel")
        self.baud_label.pack(side="left", padx=6)
        ttk.Button(row, text="Save received", command=self.save_received).pack(side="right")

        row = ttk.Frame(self)
        row.pack(fill="x", padx=12, pady=(5, 3))
        ttk.Label(row, text="Received data", style="Muted.TLabel").pack(side="left")
        self.stats = ttk.Label(row, text="0 bytes  |  0 characters  |  0 errors", style="Muted.TLabel")
        self.stats.pack(side="right")

        self.output = tk.Text(
            self, height=9, bg=PANEL, fg=FG, insertbackground=FG, selectbackground="#365b5e",
            bd=0, wrap="word", font=("Consolas", 11), padx=10, pady=8
        )
        self.output.pack(fill="both", expand=True, padx=12, pady=3)
        self.output.insert("end", "Received messages will appear here when the receiver ESP32 sends decoded data.\n")
        self.output.config(state="disabled")

        row = ttk.Frame(self)
        row.pack(fill="x", padx=12, pady=3)
        ttk.Button(row, text="Clear display", command=self.clear_display).pack(side="left")
        ttk.Button(row, text="Insert demo data", command=self.demo_data).pack(side="left", padx=6)
        ttk.Label(row, text="Demo data is local UI testing only", style="Muted.TLabel").pack(side="left")

        self.prog = ttk.Progressbar(self, maximum=100)
        self.prog.pack(fill="x", padx=12, pady=(3, 2))

        ttk.Label(self, text="Connection history", style="Muted.TLabel").pack(anchor="w", padx=12)
        self.hist = tk.Text(self, height=3, bg=PANEL, fg=FG, bd=0, state="disabled", font=("Consolas", 9))
        self.hist.pack(fill="x", padx=12, pady=2)
        self.status = ttk.Label(self, text="Ready - connect the receiver ESP32 when available", style="Muted.TLabel", anchor="w")
        self.status.pack(fill="x", padx=12, pady=(2, 8))

    # ---------- status and history ----------
    def say(self, message):
        self.status.config(text=message)

    def log(self, message):
        self.hist.config(state="normal")
        self.hist.insert("end", f"{datetime.datetime.now():%H:%M:%S}  {message}\n")
        self.hist.see("end")
        self.hist.config(state="disabled")

    def set_state(self, state, note=""):
        self.conn = state
        color = {
            "connected": GREEN,
            "connecting": AMBER,
            "reconnecting": AMBER,
            "error": CORAL
        }.get(state, GRAY)
        self.badge.itemconfig(self.dot, fill=color)
        self.badge.itemconfig(self.btxt, text=state)
        self.cbtn.config(text="Disconnect" if self.want else "Connect")
        if note:
            self.say(note)

    # ---------- serial ports ----------
    def refresh_ports(self, auto=False):
        ports = list(serial.tools.list_ports.comports())
        devices = [p.device for p in ports]
        current = self.portbox.get()
        self.portbox["values"] = devices

        if current in devices:
            self.portbox.set(current)
        elif auto:
            usb_serial = [p.device for p in ports if any(tag in (p.description or "").upper()
                          for tag in ("CP210", "CH340", "USB SERIAL", "USB-SERIAL"))]
            if usb_serial:
                self.portbox.set(usb_serial[0])
            elif devices:
                self.portbox.set(devices[0])

        if not auto:
            self.say(f"{len(ports)} serial port(s) found")

    def toggle(self):
        if self.want:
            self.disconnect()
            return

        port = self.portbox.get().strip()
        if not port:
            self.say("Select a receiver COM port first")
            return

        self.port = port
        self.want = True
        self.stop_event.clear()
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.set_state("connecting", f"Opening {port} at {BAUD} baud...")
        self.log(f"Connecting to {port}")
        self.reader_thread = threading.Thread(target=self.reader_worker, args=(port,), daemon=True)
        self.reader_thread.start()

    def disconnect(self):
        self.want = False
        self.stop_event.set()
        ser = self.ser
        self.ser = None
        if ser:
            try:
                ser.close()
            except Exception:
                pass
        self.set_state("disconnected", "Disconnected")
        self.log("Disconnected")

    def reader_worker(self, port):
        connection = None
        try:
            connection = serial.Serial(port, BAUD, timeout=0.15)
            self.ser = connection
            self.events.put(("state", "connected", f"Listening on {port} at {BAUD} baud"))
            self.events.put(("log", f"Connected to {port}"))
            while self.want and not self.stop_event.is_set():
                chunk = connection.read(256)
                if chunk:
                    self.events.put(("data", chunk))
        except Exception as exc:
            if self.want and not self.stop_event.is_set():
                self.events.put(("error", str(exc)))
        finally:
            if connection:
                try:
                    connection.close()
                except Exception:
                    pass
            if self.ser is connection:
                self.ser = None
            if self.want and self.stop_event.is_set():
                self.events.put(("state", "disconnected", "Disconnected"))

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "state":
                    self.set_state(event[1], event[2])
                elif kind == "log":
                    self.log(event[1])
                elif kind == "error":
                    self.want = False
                    self.set_state("error", f"Serial error: {event[1]}")
                    self.log(f"Serial error: {event[1]}")
                    self.errors += 1
                    self.update_stats()
                elif kind == "data":
                    self.handle_data(event[1])
        except queue.Empty:
            pass

        self.after(40, self.process_events)

    # ---------- received data ----------
    def handle_data(self, raw):
        self.received_bytes += len(raw)
        text = self.decoder.decode(raw)
        self.received_chars += len(text)
        self.last_data_time = time.time()
        self.activity.append((self.last_data_time, len(raw)))
        self.packets.append(self.last_data_time)

        if text:
            self.output.config(state="normal")
            self.output.insert("end", text)
            self.output.see("end")
            self.output.config(state="disabled")

        self.update_stats()
        self.prog["value"] = min(100, len(raw) * 4)

    def update_stats(self):
        self.stats.config(
            text=f"{self.received_bytes} bytes  |  {self.received_chars} characters  |  {self.errors} errors"
        )

    def clear_display(self):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")
        self.received_bytes = 0
        self.received_chars = 0
        self.errors = 0
        self.activity.clear()
        self.update_stats()
        self.say("Display and counters cleared")

    def save_received(self):
        content = self.output.get("1.0", "end-1c")
        if not content:
            self.say("There is no received text to save")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="laserlink_received.txt"
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8", newline="") as file:
                file.write(content)
            self.say(f"Saved received text to {os.path.basename(path)}")
            self.log(f"Saved data to {os.path.basename(path)}")
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))

    def demo_data(self):
        sample = (
            "[LOCAL DEMO] LASERLINK receiver interface test.\n"
            "This text was inserted by the desktop application, not received over the laser.\n"
            "Connect the receiver ESP32 to display real decoded messages.\n\n"
        )
        self.handle_data(sample.encode("utf-8"))
        self.say("Demo data inserted locally - no hardware communication occurred")

    # ---------- responsive hardware visualisation ----------
    def X(self, x):
        return self.ox + x * self.s

    def Y(self, y):
        return self.oy + y * self.s

    def F(self, size, weight="", family="Segoe UI"):
        if weight:
            return (family, max(7, int(size * self.s)), weight)
        return (family, max(7, int(size * self.s)))

    def on_resize(self, event):
        self.s = max(0.5, min(event.width / 940, event.height / 440))
        self.ox = (event.width - 940 * self.s) / 2
        self.oy = (event.height - 440 * self.s) / 2
        self.draw_static()

    def box(self, x, y, w, d, h, top, left, right):
        scale = self.s
        iso_box(self.cv, self.X(x), self.Y(y), w * scale, d * scale, h * scale,
                top, left, right, "static")

    def draw_static(self):
        c = self.cv
        X, Y = self.X, self.Y
        c.delete("static")

        for a, b, right, bottom in [(10, 8, 930, 250), (10, 258, 930, 314), (10, 322, 930, 432)]:
            c.create_rectangle(X(a), Y(b), X(right), Y(bottom), fill=CARD, outline=EDGE, tags="static")

        c.create_text(X(24), Y(22), text="RECEIVER HARDWARE PATH", anchor="w",
                      fill=MUTED, font=self.F(9, "bold"), tags="static")
        c.create_text(X(24), Y(336), text="SERIAL DATA ACTIVITY  (last 8 s)", anchor="w",
                      fill=MUTED, font=self.F(9, "bold"), tags="static")

        base = 185
        # Receiver path runs left-to-right: optical sensor -> ESP32 -> PC.
        self.box(110, base, 75, 24, 28, "#5d5d5d", "#333333", "#404040")
        self.box(110, base - 30, 75, 12, 8, "#777777", "#444444", "#555555")
        self.box(350, base, 100, 56, 12, "#3c8a85", "#2a6360", "#327873")
        self.box(690, base, 90, 18, 12, "#3b3b3b", "#2f2f2f", "#343434")
        self.box(690, base - 30, 90, 10, 70, "#4a4a4a", "#2a2a2a", "#303030")

        for x, name, sub in [
            (147, "Optical sensor", "receiver module"),
            (400, "ESP32 #2", "USB serial"),
            (735, "PC", "receiver app")
        ]:
            c.create_text(X(x), Y(base + 24), text=name, fill=FG,
                          font=self.F(11, "bold"), tags="static")
            c.create_text(X(x), Y(base + 40), text=sub, fill=MUTED,
                          font=self.F(9), tags="static")

        c.create_line(X(205), Y(base - 22), X(335), Y(base - 22),
                      fill=MUTED, arrow="last", tags="static")
        c.create_text(X(270), Y(base - 36), text="decoded signal", fill=MUTED,
                      font=self.F(9), tags="static")
        c.create_line(X(465), Y(base - 22), X(675), Y(base - 22),
                      fill=MUTED, arrow="last", tags="static")
        c.create_text(X(570), Y(base - 36), text="USB", fill=MUTED,
                      font=self.F(9), tags="static")

        c.create_text(X(55), Y(base - 70), text="incoming light", fill=MUTED,
                      font=self.F(9), tags="static")
        c.create_line(X(900), Y(350), X(900), Y(416), fill="#2c2c2c",
                      dash=(2, 4), tags="static")
        c.create_text(X(24), Y(350), text="DATA", fill=MUTED,
                      font=self.F(8), tags="static")
        c.create_text(X(24), Y(408), text="IDLE", fill=MUTED,
                      font=self.F(8), tags="static")

    def tick(self):
        c, X, Y = self.cv, self.X, self.Y
        c.delete("dyn")
        now = time.time()

        self.activity = [(stamp, count) for stamp, count in self.activity if stamp >= now - 8]
        self.packets = [stamp for stamp in self.packets if now - stamp < 1.2]

        # Incoming beam is a conceptual illustration, not a measured optical waveform.
        beam_y = Y(145)
        beam_start, beam_end = X(40), X(110)
        recent = now - self.last_data_time < 0.35

        if self.conn == "connected":
            c.create_line(beam_start, beam_y, beam_end, beam_y,
                          fill="#2b4f52" if recent else GRAY,
                          width=max(1, 4 * self.s), dash=() if recent else (3, 6), tags="dyn")
        else:
            c.create_line(beam_start, beam_y, beam_end, beam_y,
                          fill=GRAY, width=1, dash=(3, 6), tags="dyn")

        # Data packets travel left-to-right: sensor -> ESP32 -> PC.
        for stamp in self.packets:
            progress = min(1.0, max(0.0, 1.0 - (now - stamp) / 1.2))
            x = 155 + progress * 570
            y = 145 + math.sin(progress * math.pi * 3) * 7
            radius = 4 * self.s
            c.create_oval(X(x) - radius, Y(y) - radius, X(x) + radius, Y(y) + radius,
                          fill=TEAL_HI, outline="", tags="dyn")

        # ESP32 activity indicator.
        led_x, led_y = X(400), Y(155)
        if recent:
            for radius, color in [(12, "#2b4f52"), (7, TEAL_HI)]:
                r = radius * self.s
                c.create_oval(led_x-r, led_y-r, led_x+r, led_y+r,
                              fill=color, outline="", tags="dyn")
        else:
            r = 4 * self.s
            c.create_oval(led_x-r, led_y-r, led_x+r, led_y+r,
                          fill=GRAY, outline="", tags="dyn")

        # Recent serial activity graph.
        high, low = 350, 408
        points = []
        previous_y = None
        for stamp, count in self.activity:
            x = 44 + (stamp - (now - 8)) / 8 * 856
            y = high if count else low
            if previous_y is not None and y != previous_y:
                points.extend([X(x), Y(previous_y)])
            points.extend([X(x), Y(y)])
            previous_y = y

        if len(points) >= 4:
            c.create_line(*points, fill="#2b4f52", width=max(2, 7 * self.s), tags="dyn")
            c.create_line(*points, fill=TEAL_HI, width=max(1, 2 * self.s), tags="dyn")

        c.create_text(X(918), Y(24), text=f"received {self.received_bytes} bytes",
                      fill=MUTED, anchor="e", font=self.F(9), tags="dyn")
        self.after(33, self.tick)

    def on_close(self):
        self.disconnect()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
