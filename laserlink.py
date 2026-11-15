import customtkinter as ctk
import serial
import serial.tools.list_ports

# ---------------- CONFIG ----------------

BAUD_RATE = 115200
ser = None

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ---------------- SERIAL FUNCTIONS ----------------

def get_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


def refresh_ports():
    ports = get_ports()

    if ports:
        port_menu.configure(values=ports)
        port_var.set(ports[0])
        set_status("READY — SELECT YOUR ESP32")
    else:
        port_menu.configure(values=["No ports found"])
        port_var.set("No ports found")
        set_status("NO DEVICE DETECTED", "#ff5c5c")


def set_status(message, color="#8b949e"):
    status_label.configure(text=f"●  {message}", text_color=color)


def connect_esp32():
    global ser

    try:
        port = port_var.get()

        if port == "No ports found":
            set_status("NO VALID PORT SELECTED", "#ff5c5c")
            return

        if ser and ser.is_open:
            ser.close()

        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        set_status(f"CONNECTED TO {port}", "#39d98a")

    except Exception as error:
        set_status(f"CONNECTION FAILED: {error}", "#ff5c5c")


def disconnect_esp32():
    global ser

    if ser and ser.is_open:
        ser.close()

    set_status("DEVICE DISCONNECTED")


def transmit():
    if not ser or not ser.is_open:
        set_status("CONNECT TO ESP32 FIRST", "#ff5c5c")
        return

    message = message_box.get("1.0", "end-1c")

    if not message.strip():
        set_status("ENTER A MESSAGE FIRST", "#ffb020")
        return

    try:
        ser.write((message + "\n").encode("utf-8"))
        set_status("MESSAGE TRANSMITTED VIA LASER", "#39d98a")

    except Exception as error:
        set_status(f"TRANSMISSION FAILED: {error}", "#ff5c5c")


# ---------------- LIVE BINARY CONVERTER ----------------

def update_binary(event=None):
    """Convert the message into binary bytes in real time."""

    message = message_box.get("1.0", "end-1c")

    # Convert text → UTF-8 bytes → 8-bit binary
    binary = " ".join(
        format(byte, "08b")
        for byte in message.encode("utf-8")
    )

    binary_output.configure(state="normal")
    binary_output.delete("1.0", "end")
    binary_output.insert("1.0", binary)
    binary_output.configure(state="disabled")


# ---------------- PANEL SYSTEM ----------------

def clear_content():
    """Remove the current panel."""
    for widget in content_frame.winfo_children():
        widget.destroy()


def show_transmit():
    clear_content()

    # ----- Header -----

    panel_title = ctk.CTkLabel(
        content_frame,
        text="TRANSMIT",
        font=("Arial", 32, "bold")
    )
    panel_title.pack(anchor="w", pady=(20, 5), padx=40)

    panel_subtitle = ctk.CTkLabel(
        content_frame,
        text="Send data through the optical transmitter",
        font=("Arial", 14),
        text_color="#8b949e"
    )
    panel_subtitle.pack(anchor="w", padx=40, pady=(0, 25))

    # ----- Connection Card -----

    card = ctk.CTkFrame(content_frame, corner_radius=12)
    card.pack(fill="x", padx=40)

    ctk.CTkLabel(
        card,
        text="ESP32 DEVICE",
        font=("Arial", 13, "bold")
    ).pack(anchor="w", padx=20, pady=(18, 8))

    global port_var, port_menu

    port_var = ctk.StringVar(value="Select Port")

    port_menu = ctk.CTkOptionMenu(
        card,
        variable=port_var,
        values=["Select Port"],
        width=180
    )
    port_menu.pack(side="left", padx=(20, 8), pady=(0, 20))

    ctk.CTkButton(
        card,
        text="↻",
        width=45,
        command=refresh_ports
    ).pack(side="left", padx=5, pady=(0, 20))

    ctk.CTkButton(
        card,
        text="CONNECT",
        width=120,
        command=connect_esp32
    ).pack(side="right", padx=(8, 20), pady=(0, 20))

    ctk.CTkButton(
        card,
        text="DISCONNECT",
        width=110,
        fg_color="#444444",
        hover_color="#555555",
        command=disconnect_esp32
    ).pack(side="right", padx=5, pady=(0, 20))

    # ----- Message Input -----

    ctk.CTkLabel(
        content_frame,
        text="MESSAGE PAYLOAD",
        font=("Arial", 13, "bold"),
        text_color="#8b949e"
    ).pack(anchor="w", padx=40, pady=(30, 8))

    global message_box, binary_output

    message_box = ctk.CTkTextbox(
        content_frame,
        height=110,
        corner_radius=12,
        font=("Arial", 16)
    )
    message_box.pack(fill="x", padx=40)

    # Update binary every time the user types
    message_box.bind("<KeyRelease>", update_binary)

    # ----- Live Binary Output -----

    ctk.CTkLabel(
        content_frame,
        text="LIVE BINARY OUTPUT",
        font=("Arial", 13, "bold"),
        text_color="#8b949e"
    ).pack(anchor="w", padx=40, pady=(20, 8))

    binary_output = ctk.CTkTextbox(
        content_frame,
        height=100,
        corner_radius=12,
        font=("Consolas", 15)
    )
    binary_output.pack(fill="x", padx=40)

    # User should not edit the binary directly
    binary_output.configure(state="disabled")

    # ----- Transmit Button -----

    ctk.CTkButton(
        content_frame,
        text="⚡  TRANSMIT VIA LASER",
        height=55,
        corner_radius=12,
        font=("Arial", 16, "bold"),
        command=transmit
    ).pack(fill="x", padx=40, pady=25)

    refresh_ports()


def show_receive():
    clear_content()

    ctk.CTkLabel(
        content_frame,
        text="RECEIVER",
        font=("Arial", 32, "bold")
    ).pack(anchor="w", padx=40, pady=(20, 5))

    ctk.CTkLabel(
        content_frame,
        text="Optical receiver interface",
        font=("Arial", 14),
        text_color="#8b949e"
    ).pack(anchor="w", padx=40)

    ctk.CTkFrame(
        content_frame,
        height=2
    ).pack(fill="x", padx=40, pady=30)

    ctk.CTkLabel(
        content_frame,
        text="WAITING FOR RECEIVER MODULE",
        font=("Arial", 18, "bold"),
        text_color="#8b949e"
    ).pack(expand=True)


def show_projection():
    clear_content()

    ctk.CTkLabel(
        content_frame,
        text="PROJECTION",
        font=("Arial", 32, "bold")
    ).pack(anchor="w", padx=40, pady=(20, 5))

    ctk.CTkLabel(
        content_frame,
        text="Display received optical data",
        font=("Arial", 14),
        text_color="#8b949e"
    ).pack(anchor="w", padx=40)

    ctk.CTkLabel(
        content_frame,
        text="NO RECEIVED DATA YET",
        font=("Arial", 18, "bold"),
        text_color="#8b949e"
    ).pack(expand=True)


# ---------------- APP WINDOW ----------------

app = ctk.CTk()
app.title("LASERLINK")
app.state("zoomed")
app.resizable(True, True)


# ---------------- SIDEBAR ----------------

sidebar = ctk.CTkFrame(
    app,
    width=220,
    corner_radius=0
)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)


logo = ctk.CTkLabel(
    sidebar,
    text="LASERLINK\n🔴",
    font=("Arial", 25, "bold")
)
logo.pack(pady=(40, 40))


ctk.CTkLabel(
    sidebar,
    text="CONTROL PANELS",
    font=("Arial", 11, "bold"),
    text_color="#8b949e"
).pack(anchor="w", padx=25, pady=(0, 10))


ctk.CTkButton(
    sidebar,
    text="📤  TRANSMIT",
    anchor="w",
    height=45,
    command=show_transmit
).pack(fill="x", padx=15, pady=5)


ctk.CTkButton(
    sidebar,
    text="📥  RECEIVE",
    anchor="w",
    height=45,
    fg_color="transparent",
    hover_color="#333333",
    command=show_receive
).pack(fill="x", padx=15, pady=5)


ctk.CTkButton(
    sidebar,
    text="▣  PROJECTION",
    anchor="w",
    height=45,
    fg_color="transparent",
    hover_color="#333333",
    command=show_projection
).pack(fill="x", padx=15, pady=5)


sidebar_status = ctk.CTkLabel(
    sidebar,
    text="● SYSTEM READY",
    font=("Arial", 11, "bold"),
    text_color="#39d98a"
)
sidebar_status.pack(side="bottom", pady=25)


# ---------------- RIGHT SIDE ----------------

right_side = ctk.CTkFrame(
    app,
    corner_radius=0,
    fg_color="transparent"
)
right_side.pack(side="right", fill="both", expand=True)


# ---------------- CONTENT AREA ----------------

content_frame = ctk.CTkFrame(
    right_side,
    corner_radius=0,
    fg_color="transparent"
)
content_frame.pack(fill="both", expand=True)


# ---------------- PERMANENT STATUS BAR ----------------

status_frame = ctk.CTkFrame(
    right_side,
    height=45,
    corner_radius=0
)
status_frame.pack(fill="x", side="bottom")
status_frame.pack_propagate(False)

status_label = ctk.CTkLabel(
    status_frame,
    text="●  SYSTEM INITIALIZING",
    font=("Arial", 12, "bold"),
    text_color="#8b949e"
)
status_label.pack(side="left", padx=20)


# ---------------- START APPLICATION ----------------

show_transmit()
app.mainloop()