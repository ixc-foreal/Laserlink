# LASERLINK

### Optical data transmission using a laser and ESP32

LASERLINK is an experimental optical communication project. Its desktop sender application communicates with an ESP32 over USB serial and provides a visual preview of the data being transmitted.

## Current sender application

The current sender is **`laser_sender.py`**. It uses Python's built-in Tkinter GUI toolkit and PySerial.

Features:
- Detect and select available serial ports
- Connect to an ESP32 over USB serial
- Set the transmission speed
- Send typed text
- Send the contents of a selected file
- Manually switch the laser output on or off and run a test blink
- Preview the hardware path, transmitted bits, and recent signal activity
- Reconnect when the USB serial connection is lost

The matching receiver application is **`laser_receiver.py`**. It uses the same Tkinter theme and hardware-visualisation style, listens for decoded data from a receiver ESP32 over USB serial, displays incoming text, tracks received bytes and characters, and can save received text to a file. Its **Insert demo data** button tests the desktop interface locally; demo text is not received over the laser.

The earlier **`laserlink.py`** CustomTkinter application is retained in the repository as the previous interface.

## Requirements

- Windows, for the packaged executable instructions below
- Python 3.10 or newer
- An ESP32 configured with firmware that understands the sender's serial command protocol
- A compatible laser transmitter circuit

Install the Python dependency:

```bash
python -m pip install -r requirements.txt
```

Tkinter is included with most standard Windows Python installations. PySerial is installed through `requirements.txt`.

## Run from source

Clone the repository:

```bash
git clone https://github.com/ixc-foreal/Laserlink.git
cd Laserlink
```

Install dependencies and launch the current sender:

```bash
python -m pip install -r requirements.txt
python laser_sender.py
```

Launch the receiver separately with:

```bash
python laser_receiver.py
```

Keep `laserlink.ico` in the same folder as both current applications; they use it for their window icon.

## Build a Windows executable

Install PyInstaller:

```bash
python -m pip install pyinstaller
```

From the project folder, build the standalone executable:

```bash
py -m PyInstaller --clean --noconfirm --onefile --windowed --icon=laserlink.ico --add-data "laserlink.ico;." --name=LASERLINK-Sender laser_sender.py
```

The sender executable will be created at `dist\LASERLINK-Sender.exe`. Build the receiver with:

```bash
py -m PyInstaller --clean --noconfirm --onefile --windowed --icon=laserlink.ico --add-data "laserlink.ico;." --name=LASERLINK-Receiver laser_receiver.py
```

This creates `dist\LASERLINK-Receiver.exe`. The `--add-data` option bundles the icon so each application can find it when running as a PyInstaller executable.

## Basic usage

1. Connect the ESP32 to the computer over USB.
2. Open LASERLINK Sender.
3. Select the ESP32 serial port. The app attempts to preselect a CP210x port when one is detected.
4. Click **Connect**.
5. Choose a transmission speed.
6. Enter a message and click **Send**, or use **Send file** to transmit a file's contents.
7. Use the signal preview and history area to observe the sender activity.

The sender and receiver desktop applications require compatible ESP32 firmware. The receiver application expects the receiver ESP32 to send decoded text bytes over USB serial at 115200 baud. The optical decoding itself must be implemented on the receiver ESP32. Until that hardware and firmware are available, use **Insert demo data** only to test the receiver interface.

## Repository files

| File | Purpose |
| --- | --- |
| `laser_sender.py` | Tkinter sender application |
| `laser_receiver.py` | Matching Tkinter receiver application |
| `laserlink.py` | Previous CustomTkinter application |
| `laserlink.ico` | Windows application icon |
| `laserlink_icon.png` | Project icon image |
| `requirements.txt` | Python package dependencies |

## Releases

See [GitHub Releases](https://github.com/ixc-foreal/Laserlink/releases) for downloadable builds.

The existing `v1.0.0` release is preserved. The updated sender source is in the repository; a new `v1.1.0` executable release should be published after the updated build has been tested with the ESP32 hardware.

## Safety

Never point a laser toward a person's or animal's eyes, vehicles, aircraft, or reflective surfaces. Use an appropriate low-power module and follow its safety documentation.

---

Built with curiosity, code, and a little bit of light.
