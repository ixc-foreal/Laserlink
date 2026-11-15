# 🔴 LASERLINK

### Optical Data Transmission System using Laser & ESP32

LASERLINK is an experimental optical communication system that transmits digital information using a laser and an ESP32 microcontroller.

The project converts messages into digital data and sends them through an optical transmission system, exploring how information can be communicated using light.

---

## ⚡ Features

- 🖥️ Full-screen desktop control interface
- 🔌 ESP32 serial port connection
- 🔴 Laser-based message transmission
- 💬 Send custom text messages
- 📤 Dedicated Transmit panel
- 📥 Receiver panel for future optical data reception
- ▣ Projection panel for displaying received data
- 🪟 Standalone Windows application

---

## 🛠️ Technologies Used

- **Python**
- **CustomTkinter** — Desktop user interface
- **PySerial** — ESP32 serial communication
- **ESP32** — Microcontroller control
- **Laser Module** — Optical data transmission

---

## 🚀 Installation

### Option 1: Download the Windows Application

Download the latest `laser_link.exe` from the **Releases** section and run it on a Windows PC.

### Option 2: Run from Source

Clone this repository:

```bash
git clone https://github.com/YOUR-USERNAME/LASERLINK.git
cd LASERLINK
```

Install the required Python packages:

```bash
pip install customtkinter pyserial
```

Run the application:

```bash
python laserlink.py
```

---

## 🖥️ How It Works

1. Connect the ESP32 to your computer.
2. Open the LASERLINK application.
3. Select the ESP32 serial port.
4. Connect to the device.
5. Enter a message.
6. Press **TRANSMIT VIA LASER**.
7. The ESP32 processes the data and controls the laser transmission.

The receiver-side system is currently under development.

---

## 🔮 Future Development

- 📡 Live optical data receiver
- 🔢 Real-time binary data visualization
- 📺 Enhanced projection interface
- ⚡ Faster optical transmission speeds
- 🛡️ Error detection and improved communication reliability

---

## 📦 Project Status

🟢 **Transmitter System:** Working  
🟡 **Receiver System:** Under Development  
🔵 **Desktop Application:** Available

---

## 📸 Project Preview

LASERLINK is being developed as an experimental project exploring practical optical communication using affordable hardware.

---

### ⚠️ Safety Note

Avoid pointing laser modules toward people, animals, vehicles, or reflective surfaces. Always use the optical transmitter responsibly.

---

**Built with curiosity, code, and a little bit of light. 🔴⚡**
