import os
import sys
import datetime
import math
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog

import serial # type: ignore
import serial.tools.list_ports # type: ignore

def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base, filename)

BAUD = 115200
SPEEDS = [100, 250, 500, 1000, 2000, 4000]
SLOTS = 11  # start + 8 data + 2 stop

BG, PANEL, FG, MUTED = "#1b1b1b", "#242424", "#d4d4d4", "#8a8a8a"
TEAL, AMBER, CORAL, GREEN, GRAY = "#5b9aa0", "#d9a441", "#d0605a", "#6b9b6b", "#3a3a3a"
TEAL_HI, CARD, EDGE = "#7cc4c9", "#202020", "#303030"


def iso_box(c, x, y, w, d, h, top, left, right, tag):
    """Isometric box. (x, y) is the front-bottom corner."""
    ax, ay = w * 0.87, -w * 0.5
    bx, by = -d * 0.87, -d * 0.5
    P = (x, y)
    def pt(*v):
        return [p for q in v for p in q]
    A = (x + ax, y + ay)
    B = (x + bx, y + by)
    AB = (x + ax + bx, y + ay + by)
    H = lambda p: (p[0], p[1] - h)
    c.create_polygon(pt(P, A, H(A), H(P)), fill=right, outline=BG, tags=tag)
    c.create_polygon(pt(P, B, H(B), H(P)), fill=left, outline=BG, tags=tag)
    c.create_polygon(pt(H(P), H(A), H(AB), H(B)), fill=top, outline=BG, tags=tag)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.iconbitmap(resource_path("laserlink.ico"))
        self.title("Laser Link - Sender")
        self.configure(bg=BG)
        self.geometry("1100x860")
        self.minsize(900, 700)
        self.tx = None
        self.port = ""
        self.want = False
        self.busy = False
        self.conn = "disconnected"
        self.laser_idle = True
        self.bps = 1000
        self.vq = []
        self.vend = 0.0
        self.test_t0 = 0.0
        self.sent = 0
        self.cur_char = ""
        self.s, self.ox, self.oy = 1.0, 0.0, 0.0
        self.sig = []
        self.style_ui()
        self.build()
        self.refresh_ports(auto=True)
        self.draw_static()
        self.tick()
        self.watch()

    # ---------- UI ----------
    def style_ui(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, bordercolor=GRAY)
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("Muted.TLabel", foreground=MUTED)
        s.configure("TButton", background=PANEL, foreground=FG, padding=6, borderwidth=1)
        s.map("TButton", background=[("active", GRAY)])
        s.configure("TCheckbutton", background=BG, foreground=FG)
        s.configure("TEntry", fieldbackground=PANEL, foreground=FG, insertcolor=FG)
        s.configure("TCombobox", fieldbackground=PANEL, foreground=FG, background=PANEL)
        s.configure("Horizontal.TProgressbar", background=TEAL, troughcolor=PANEL)

    def build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(top, text="LASER LINK", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(top, text="  sender", style="Muted.TLabel", font=("Segoe UI", 12)).pack(side="left")
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
        ttk.Label(row, text="   Speed (bits/s)").pack(side="left")
        self.speed = ttk.Combobox(row, values=SPEEDS, width=7)
        self.speed.set(self.bps)
        self.speed.pack(side="left", padx=6)
        self.speed.bind("<<ComboboxSelected>>", lambda e: self.apply_speed())
        self.speed.bind("<Return>", lambda e: self.apply_speed())
        self.est = ttk.Label(row, text="", style="Muted.TLabel")
        self.est.pack(side="left")

        row = ttk.Frame(self)
        row.pack(fill="x", padx=12, pady=4)
        ttk.Button(row, text="Laser ON", command=lambda: self.laser(True)).pack(side="left")
        ttk.Button(row, text="Laser OFF", command=lambda: self.laser(False)).pack(side="left", padx=6)
        ttk.Button(row, text="Test blink", command=self.test_blink).pack(side="left")
        self.slow = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, text="Slow-motion preview (first 6 letters)", variable=self.slow).pack(side="right")

        row = ttk.Frame(self)
        row.pack(fill="x", padx=12, pady=4)
        self.msg = ttk.Entry(row, font=("Consolas", 12))
        self.msg.pack(side="left", fill="x", expand=True, ipady=4)
        self.msg.bind("<Return>", lambda e: self.send_text())
        ttk.Button(row, text="Send", width=9, command=self.send_text).pack(side="left", padx=6)
        ttk.Button(row, text="Send file", command=self.send_file).pack(side="left")

        self.prog = ttk.Progressbar(self, maximum=100)
        self.prog.pack(fill="x", padx=12, pady=2)

        ttk.Label(self, text="History", style="Muted.TLabel").pack(anchor="w", padx=12)
        self.hist = tk.Text(self, height=4, bg=PANEL, fg=FG, bd=0, state="disabled", font=("Consolas", 10))
        self.hist.pack(fill="x", padx=12, pady=2)
        self.status = ttk.Label(self, text="Ready", style="Muted.TLabel", anchor="w")
        self.status.pack(fill="x", padx=12, pady=(2, 8))
        self.update_est()

    def say(self, t):
        self.status.config(text=t)

    def set_state(self, st, note=""):
        self.conn = st
        col = {"connected": GREEN, "connecting": AMBER, "reconnecting": AMBER, "error": CORAL}.get(st, GRAY)
        self.badge.itemconfig(self.dot, fill=col)
        self.badge.itemconfig(self.btxt, text=st)
        self.cbtn.config(text="Disconnect" if self.want else "Connect")
        if note:
            self.say(note)

    # ---------- ports and connection ----------
    def refresh_ports(self, auto=False):
        ports = list(serial.tools.list_ports.comports())
        self.portbox["values"] = [p.device for p in ports]
        if auto:
            cp = [p.device for p in ports if "CP210" in (p.description or "")]
            if cp:
                self.portbox.set(cp[0])
        if not auto:
            self.say(f"{len(ports)} port(s) found")

    def toggle(self):
        if self.want:
            self.want = False
            self.drop()
            self.set_state("disconnected", "Disconnected")
        else:
            self.port = self.portbox.get()
            if not self.port:
                self.say("Pick a port first")
                return
            self.want = True
            self.set_state("connecting")
            self.try_connect()

    def drop(self):
        s, self.tx = self.tx, None
        if s:
            try:
                s.close()
            except Exception:
                pass

    def try_connect(self):
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self.conn_worker, args=(self.port,), daemon=True).start()

    def conn_worker(self, port):
        try:
            s = serial.Serial(port, BAUD, timeout=0.1, write_timeout=1)
            time.sleep(1.5)  # ESP32 restarts when the port opens
            s.reset_input_buffer()
            us = 1_000_000 // self.bps
            s.write(bytes([1, us >> 8, us & 255]))
            self.tx = s
            self.after(0, self.set_state, "connected", f"Connected on {port}")
        except Exception as e:
            self.after(0, self.set_state, "error", f"{e}")
        finally:
            self.busy = False

    def watch(self):
        if self.want and not self.busy:
            names = {p.device for p in serial.tools.list_ports.comports()}
            ok = self.tx is not None and self.tx.is_open and self.port in names
            if not ok:
                self.drop()
                self.set_state("reconnecting", "USB lost, reconnecting...")
                self.try_connect()
        self.after(1500, self.watch)

    def write(self, data):
        s = self.tx
        if not s:
            self.say("Connect first")
            return False
        try:
            s.write(bytes(data))
            return True
        except Exception:
            self.drop()
            self.say("USB write failed, reconnecting...")
            return False

    # ---------- controls ----------
    def bps_value(self):
        try:
            return max(16, min(20000, int(self.speed.get())))
        except ValueError:
            return self.bps

    def update_est(self):
        self.est.config(text=f"about {self.bps_value() / SLOTS:.0f} letters/sec")

    def apply_speed(self):
        self.bps = self.bps_value()
        self.update_est()
        us = 1_000_000 // self.bps
        if self.write([1, us >> 8, us & 255]):
            self.say(f"Speed set to {self.bps} bits/s")

    def laser(self, on):
        if self.write([2 if on else 3]):
            self.laser_idle = on

    def test_blink(self):
        if self.write([4]):
            self.test_t0 = time.time()
            self.laser_idle = True

    def send_text(self):
        t = self.msg.get()
        if t:
            self.msg.delete(0, "end")
            self.start_send(t.encode("utf-8", "replace"), t)

    def send_file(self):
        p = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if p:
            with open(p, "rb") as fh:
                raw = fh.read()
            self.start_send(raw, f"[file] {p.split('/')[-1].split(chr(92))[-1]}")

    def start_send(self, data, label):
        if not self.tx:
            self.say("Connect first")
            return
        data = bytes(c for c in data if c > 6)
        now = time.time()
        slow = self.slow.get()
        slot = max(1.0 / self.bps, 0.12) if slow else 1.0 / self.bps
        self.vend = max(now, self.vend)
        for b in (data[:6] if slow else data):
            self.vq.append({"b": b, "t0": self.vend, "slot": slot})
            self.vend += SLOTS * slot
        self.hist.config(state="normal")
        self.hist.insert("end", f"{datetime.datetime.now():%H:%M:%S}  {label}\n")
        self.hist.see("end")
        self.hist.config(state="disabled")
        threading.Thread(target=self.send_worker, args=(data,), daemon=True).start()

    def send_worker(self, data):
        per = SLOTS / self.bps
        done = 0
        for i in range(0, len(data), 64):
            chunk = data[i:i + 64]
            if not self.write(chunk):
                self.after(0, self.say, "Send interrupted: connection lost")
                break
            time.sleep(len(chunk) * per + 0.05)
            done += len(chunk)
            self.sent += len(chunk)
            self.after(0, self.prog.config, {"value": 100 * done / len(data)})
        else:
            self.after(0, self.say, f"Sent {len(data)} bytes")
        self.after(0, self.prog.config, {"value": 0})

    # ---------- scene ----------
    def X(self, x):
        return self.ox + x * self.s

    def Y(self, y):
        return self.oy + y * self.s

    def F(self, size, weight="", fam="Segoe UI"):
        return (fam, max(7, int(size * self.s)), weight) if weight else (fam, max(7, int(size * self.s)))

    def on_resize(self, e):
        self.s = max(0.5, min(e.width / 940, e.height / 440))
        self.ox = (e.width - 940 * self.s) / 2
        self.oy = (e.height - 440 * self.s) / 2
        self.draw_static()

    def box(self, x, y, w, d, h, top, left, right):
        S = self.s
        iso_box(self.cv, self.X(x), self.Y(y), w * S, d * S, h * S, top, left, right, "static")

    def draw_static(self):
        c, S, X, Y = self.cv, self.s, self.X, self.Y
        c.delete("static")
        base = 185
        for (a, b, cc, d) in [(10, 8, 930, 250), (10, 258, 930, 314), (10, 322, 930, 432)]:
            c.create_rectangle(X(a), Y(b), X(cc), Y(d), fill=CARD, outline=EDGE, tags="static")
        c.create_text(X(24), Y(22), text="HARDWARE", anchor="w", fill=MUTED, font=self.F(9, "bold"), tags="static")
        c.create_text(X(24), Y(336), text="LASER SIGNAL  (last 8 s, preview)", anchor="w", fill=MUTED, font=self.F(9, "bold"), tags="static")
        self.box(110, base, 90, 18, 12, "#3b3b3b", "#2f2f2f", "#343434")
        self.box(110, base - 30, 90, 10, 70, "#4a4a4a", "#2a2a2a", "#303030")
        self.box(330, base, 100, 56, 12, "#3c8a85", "#2a6360", "#327873")
        self.box(520, base, 26, 26, 34, "#5d5d5d", "#333", "#404040")
        self.box(665, base, 80, 22, 26, "#9a5d57", "#5c3835", "#7a4944")
        for x, name, sub in [(110, "PC", "this app"), (330, "ESP32 #1", "pin D5"), (520, "2N2222", "transistor switch"), (690, "Laser", "module")]:
            c.create_text(X(x), Y(base + 24), text=name, fill=FG, font=self.F(11, "bold"), tags="static")
            c.create_text(X(x), Y(base + 40), text=sub, fill=MUTED, font=self.F(9), tags="static")
        for x1, x2, lab in [(165, 255, "USB"), (415, 475, "10k"), (555, 625, "C to laser -")]:
            c.create_line(X(x1), Y(base - 22), X(x2), Y(base - 22), fill=MUTED, arrow="last", tags="static")
            c.create_text(X((x1 + x2) / 2), Y(base - 36), text=lab, fill=MUTED, font=self.F(9), tags="static")
        c.create_text(X(880), Y(base - 70), text="to receiver", fill=MUTED, font=self.F(9), tags="static")
        for lab, yy in [("ON", 350), ("OFF", 408)]:
            c.create_line(X(44), Y(yy), X(900), Y(yy), fill="#2c2c2c", dash=(2, 4), tags="static")
            c.create_text(X(24), Y(yy), text=lab, fill=MUTED, font=self.F(8), tags="static")
        self.base = base

    def tick(self):
        c, S, X, Y = self.cv, self.s, self.X, self.Y
        c.delete("dyn")
        t = time.time()
        base = 185
        self.vq = [e for e in self.vq if t < e["t0"] + SLOTS * e["slot"] + 1.0]
        act = next((e for e in self.vq if e["t0"] <= t < e["t0"] + SLOTS * e["slot"]), None)
        idx, bits, laser_on = -1, [], self.laser_idle and self.conn == "connected"
        if t < self.test_t0 + 1.8:
            laser_on = int((t - self.test_t0) / 0.3) % 2 == 0
        elif act:
            b = act["b"]
            bits = [0] + [(b >> i) & 1 for i in range(8)] + [1, 1]
            idx = min(SLOTS - 1, int((t - act["t0"]) / act["slot"]))
            laser_on = bits[idx] == 1
            self.cur_char = chr(b) if 32 <= b < 127 else "."
        self.sig.append((t, 1 if laser_on else 0))
        while self.sig and self.sig[0][0] < t - 8:
            self.sig.pop(0)

        # beam with glow
        tx_, ty_ = X(665 + 80 * 0.87), Y(base - 40 - 13)
        x_end = X(925)
        if laser_on:
            for w, col in [(22, "#2a1514"), (13, "#4a2220"), (6, "#a8453f"), (2, "#ffc4bd")]:
                c.create_line(tx_, ty_, x_end, ty_, fill=col, width=max(1, w * S), tags="dyn")
            for k in range(9):
                x = tx_ + ((t * 170 + k * 40) % 360) / 360 * (x_end - tx_)
                c.create_oval(x - 3 * S, ty_ - 3 * S, x + 3 * S, ty_ + 3 * S, fill="#ffd9d4", outline="", tags="dyn")
            for r, col in [(16, "#4a2220"), (10, "#a8453f"), (5, "#ffc4bd")]:
                c.create_oval(tx_ - r * S, ty_ - r * S, tx_ + r * S, ty_ + r * S, fill=col, outline="", tags="dyn")
        else:
            c.create_line(tx_, ty_, x_end, ty_, fill=GRAY, width=1, dash=(3, 6), tags="dyn")
            c.create_oval(tx_ - 4 * S, ty_ - 4 * S, tx_ + 4 * S, ty_ + 4 * S, fill=GRAY, outline="", tags="dyn")

        # ESP32 LED
        lx, ly = X(363), Y(base - 29)
        if laser_on:
            for r, col in [(12, "#4d3a12"), (7, AMBER)]:
                c.create_oval(lx - r * S, ly - r * S, lx + r * S, ly + r * S, fill=col, outline="", tags="dyn")
        else:
            c.create_oval(lx - 4 * S, ly - 4 * S, lx + 4 * S, ly + 4 * S, fill=GRAY, outline="", tags="dyn")

        # letters flying from the PC into the ESP32, and bits travelling to the laser
        wy = Y(base - 22)
        for e in self.vq:
            ch = chr(e["b"]) if 32 <= e["b"] < 127 else "."
            lead = 0.9
            if e["t0"] - lead <= t < e["t0"]:
                p = (t - (e["t0"] - lead)) / lead
                x = 110 + p * 220
                y = base - 95 - math.sin(math.pi * p) * 45 + p * 30
                c.create_rectangle(X(x - 14), Y(y - 14), X(x + 14), Y(y + 14), fill="#3a3118", outline=AMBER, width=max(1, 2 * S), tags="dyn")
                c.create_text(X(x), Y(y), text=ch, fill=AMBER, font=self.F(15, "bold", "Consolas"), tags="dyn")
            if e["slot"] >= 0.05:
                for k in range(SLOTS):
                    te = e["t0"] + k * e["slot"]
                    if te <= t < te + 0.7:
                        p = (t - te) / 0.7
                        x = 415 + p * 225
                        v = 1 if (k == 0 and False) else (0 if k == 0 else ([(e["b"] >> i) & 1 for i in range(8)] + [1, 1])[k - 1])
                        col = TEAL_HI if v else "#555"
                        c.create_rectangle(X(x - 7), Y(base - 22) - 7 * S, X(x + 7), Y(base - 22) + 7 * S, fill=col, outline="", tags="dyn")
        if act:
            x, y = 330, base - 78
            c.create_rectangle(X(x - 28), Y(y - 28), X(x + 28), Y(y + 28), fill="#2e2714", outline="#6b5320", width=max(1, 4 * S), tags="dyn")
            c.create_rectangle(X(x - 24), Y(y - 24), X(x + 24), Y(y + 24), fill=PANEL, outline=AMBER, width=max(1, 2 * S), tags="dyn")
            c.create_text(X(x), Y(y), text=self.cur_char, fill=AMBER, font=self.F(26, "bold", "Consolas"), tags="dyn")

        # bit chips
        lab = ["start", "b0", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "stop", "stop"]
        x0 = (940 - SLOTS * 54) / 2 + 20
        for i in range(SLOTS):
            x = x0 + i * 54
            if idx == i:
                c.create_rectangle(X(x - 4), Y(279), X(x + 52), Y(309), fill="#4d3a12", outline="", tags="dyn")
                fill, out, w = (TEAL_HI if bits[i] else "#555"), AMBER, 2
            elif act and i < idx:
                fill, out, w = ("#2b4f52" if bits[i] else "#2a2a2a"), GRAY, 1
            else:
                fill, out, w = PANEL, GRAY, 1
            c.create_rectangle(X(x), Y(283), X(x + 48), Y(305), fill=fill, outline=out, width=max(1, w * S), tags="dyn")
            c.create_text(X(x + 24), Y(270), text=lab[i], fill=MUTED, font=self.F(8), tags="dyn")
            c.create_text(X(x + 24), Y(294), text=str(bits[i]) if act else "-", fill="#101010" if idx == i else FG, font=self.F(12, "bold", "Consolas"), tags="dyn")
        if act:
            c.create_text(X(60), Y(286), text=self.cur_char, fill=AMBER, font=self.F(26, "bold", "Consolas"), tags="dyn")
            c.create_text(X(60), Y(306), text=f"0x{act['b']:02X}", fill=MUTED, font=self.F(9, "", "Consolas"), tags="dyn")
        else:
            c.create_text(X(60), Y(294), text="idle", fill=MUTED, font=self.F(11), tags="dyn")

        # live signal graph
        hi, lo = 350, 408
        pts, prev = [], None
        for ts, lv in self.sig:
            x = 44 + (ts - (t - 8)) / 8 * 856
            yy = hi if lv else lo
            if prev is not None and yy != prev:
                pts += [X(x), Y(prev)]
            pts += [X(x), Y(yy)]
            prev = yy
        if len(pts) >= 4:
            c.create_line(*pts, fill="#2b4f52", width=max(2, 7 * S), tags="dyn")
            c.create_line(*pts, fill=TEAL_HI, width=max(1, 2 * S), tags="dyn")
        c.create_line(X(900), Y(342), X(900), Y(416), fill=AMBER, tags="dyn")
        c.create_text(X(918), Y(24), text=f"sent {self.sent} bytes", fill=MUTED, anchor="e", font=self.F(9), tags="dyn")
        self.after(33, self.tick)


App().mainloop()