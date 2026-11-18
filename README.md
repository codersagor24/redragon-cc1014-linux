<div align="center">

# 🧊 Linux Digital Cooler Display Driver

### Open-Source Linux Driver for USB HID CPU Cooler Displays with Digital Temperature Screens

[![Linux](https://img.shields.io/badge/OS-Linux-FCC624?logo=linux&logoColor=black)](https://kernel.org)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![USB ID](https://img.shields.io/badge/USB-5131%3A2007-orange)]()
[![GUI App](https://img.shields.io/badge/GUI-GTK3-blueviolet?logo=gnome)]()

*Real-time CPU & GPU temperature, utilization, and frequency display — works natively on Linux without Windows or Wine.*

</div>

---

## 📖 Overview

Many CPU air coolers and AIO liquid coolers (such as the **Redragon CC-1014**, **darkFlash Nebula** series, and similar OEM variants) feature built-in **7-segment digital temperature displays** connected to your motherboard's internal USB 2.0 header.

On Linux, these devices are detected as:
```
ID 5131:2007 MSR Mini HID Device
```

Manufacturers only provide Windows-only software for these displays, leaving them **dark and unusable on Linux**. This project solves that — it's a fully native Linux driver that reads your CPU & GPU telemetry and feeds it directly to the display, with a GUI app to control everything.

---

## ✨ Features

- 🌡️ **Real-time display** — CPU temperature, GPU temperature, CPU load, frequency
- 🖥️ **GTK3 GUI app** — start/stop, switch display modes, monitor live data
- ⚙️ **Systemd service** — runs in the background, starts automatically on boot
- 📦 **Multi-distro installer** — Ubuntu, Debian, Arch, Fedora, openSUSE
- 🔌 **Auto device detection** — reconnects automatically if the device is unplugged
- 🛠️ **No Windows, no Wine** — 100% native Linux

---

## 🖥️ Supported Hardware

| Device | Type | USB ID | Status |
| :--- | :--- | :--- | :--- |
| **Redragon CC-1014** | Air Cooler | `5131:2007` | ✅ Confirmed Working |
| **Redragon CC-1015 / CC-101x Series** | Air Cooler | `5131:2007` | ✅ Fully Compatible |
| **darkFlash Nebula DN240D / DN360D** | AIO Liquid Cooler | `5131:2007` | ✅ Compatible |
| **darkFlash DH360D** | AIO Liquid Cooler | `5131:2007` | ✅ Compatible |
| **4FAN XZ Bit Case Display** | Telemetry Panel | `5131:2007` | ✅ Compatible |
| **Generic Witmod / Ruilian OEM Panels** | Air / Liquid Coolers | `5131:2007` | ✅ Compatible |

> 📄 For a comprehensive compatibility list including DeepCool, Thermalright, and Jonsbo — see [DEVICES.md](DEVICES.md).

---

## 🚀 Installation

### Option 1: One-Click Installer (Recommended)

Download and run the self-contained installer — no git required:

```bash
wget https://github.com/codersagor24/redragon-cc1014-linux/releases/latest/download/cooler-display-installer.run
chmod +x cooler-display-installer.run
sudo ./cooler-display-installer.run
```

### Option 2: Clone & Install

```bash
git clone https://github.com/codersagor24/redragon-cc1014-linux.git
cd redragon-cc1014-linux
sudo ./install.sh
```

The installer automatically:
1. Detects your Linux distro and installs dependencies
2. Sets up a udev rule for non-root USB access
3. Installs the background daemon
4. Installs the **GUI app** (`cooler-display-ui`)
5. Enables and starts the systemd service

---

## 🖱️ Using the GUI App

After installation, launch the app from your application menu:

> **Cooler Display Manager**

Or from terminal:
```bash
cooler-display-ui
```

The GUI lets you:
- 👁️ **See live stats** — CPU temp, GPU temp, CPU load, frequency
- ▶️ **Start / Stop** the background service
- 🔄 **Switch display modes** — CPU Temp, GPU Temp, CPU Load, or Alternating
- 📊 Check the current status at a glance

---

## 🛠️ Display Modes

| Mode | What Shows on Cooler Display |
| :--- | :--- |
| **CPU Temperature** (default) | CPU package temperature in °C |
| **GPU Temperature** | GPU temperature in °C |
| **CPU Load** | CPU utilization % (0–99) |
| **Hottest Component** | Whichever of CPU/GPU is currently hotter |
| **Alternating** | Cycles between CPU and GPU every 5 seconds |

Switch modes from the GUI, or edit the config at `/etc/cooler-display.conf`.

---

## 🛠️ Manual Service Management

```bash
# Check status
systemctl status cooler-display.service

# View live logs
journalctl -u cooler-display.service -f

# Restart
sudo systemctl restart cooler-display.service

# Stop
sudo systemctl stop cooler-display.service

# Uninstall completely
sudo ./uninstall.sh
```

---

## 🤝 Contributing

Contributions are welcome! If you have another compatible cooler or display panel:

1. Fork this repository
2. Add your device to [DEVICES.md](DEVICES.md)
3. Test on your hardware
4. Submit a Pull Request

> 💬 Open an [Issue](https://github.com/codersagor24/redragon-cc1014-linux/issues) if your device has a different USB ID or doesn't work out of the box.

---

## 📄 License

MIT License — free to use, modify, and distribute. See [LICENSE](LICENSE).
