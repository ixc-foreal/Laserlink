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

The earlier **`laserlink.py`** CustomTkinter application is retained in the repository as the previous interface. Use `laser_sender.py` for the current sender.

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

Keep `laserlink.ico` in the same folder as `laser_sender.py`; the application uses it for its window icon.

## Build a Windows executable

Install PyInstaller:

```bash
python -m pip install pyinstaller
```

From the project folder, build the standalone executable:

```bash
py -m PyInstaller --clean --noconfirm --onefile --windowed --icon=laserlink.ico --add-data "laserlink.ico;." --name=LASERLINK-Sender laser_sender.py
```

The executable will be created at:

```text
dist\LASERLINK-Sender.exe
```

The `--add-data` option bundles the icon so the application can find it when running as a PyInstaller executable.

## Basic usage

1. Connect the ESP32 to the computer over USB.
2. Open LASERLINK Sender.
3. Select the ESP32 serial port. The app attempts to preselect a CP210x port when one is detected.
4. Click **Connect**.
5. Choose a transmission speed.
6. Enter a message and click **Send**, or use **Send file** to transmit a file's contents.
7. Use the signal preview and history area to observe the sender activity.

The sender expects compatible ESP32 firmware. The desktop application alone does not provide the receiver hardware or receiver-side software.

## Repository files

| File | Purpose |
| --- | --- |
| `laser_sender.py` | Current Tkinter sender application |
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
