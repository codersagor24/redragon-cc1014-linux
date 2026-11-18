<div align="center">

# 🧊 Universal Digital Cooler Display Driver
### Cross-Platform Driver & GUI Manager for USB HID CPU Cooler Displays (Linux & Windows 10/11)

[![Linux](https://img.shields.io/badge/OS-Linux-FCC624?logo=linux&logoColor=black)](https://kernel.org)
[![Windows](https://img.shields.io/badge/OS-Windows_10%2F11-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![USB ID](https://img.shields.io/badge/USB-5131%3A2007-orange)]()
[![GUI](https://img.shields.io/badge/GUI-GTK3%20%7C%20Tkinter-blueviolet)]()

*Real-time CPU & GPU temperature, utilization, and telemetry driver with 18+ display modes and desktop GUI for both Linux and Windows.*

</div>

---

## 📖 Overview

Many CPU air coolers and AIO liquid coolers (such as the **Redragon CC-1014**, **darkFlash Nebula** series, and similar OEM variants) feature built-in **7-segment digital temperature displays** connected to your motherboard's internal USB 2.0 header (`5131:2007`).

This project provides a **lightweight, open-source, universal driver and GUI manager** that works seamlessly across **both Linux and Windows**, replacing bloated proprietary OEM utilities with a clean, low-resource daemon and modern desktop control panel.

---

## ✨ Features

- 🐧 **Linux Support** — Native systemd service, udev rules, GTK3 desktop interface, multi-distro installer
- 🪟 **Windows Support** — Silent background daemon, auto-start on login, native Tkinter GUI, one-click `.bat` scripts
- 🌡️ **18+ Display Modes** — CPU/GPU/NVMe temps, RAM %, Disk %, GPU power, Network speed (KB/s, Mbps), Clock, and more
- 🖥️ **Desktop GUI** — Real-time telemetry grid, one-click mode switcher, service start/stop controls
- 🚨 **High-Temp Alert** — Flashing warning alert on cooler display when configurable temperature threshold is exceeded
- ⚡ **Ultra Lightweight** — Consumes minimal CPU cycles and runs silently in the background

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

## 🪟 Windows Setup (Windows 10 / 11)

### 1. Requirements
- Ensure **Python 3.8+** is installed ([python.org](https://www.python.org/downloads/)).
  *(Make sure to check **"Add Python to PATH"** during Python setup).*

### 2. Quick Install
1. [Download this repository as ZIP](https://github.com/codersagor24/redragon-cc1014-linux/archive/refs/heads/master.zip) and extract it.
2. Right-click **`windows_install.bat`** and click **Open** (or double-click it).
3. The installer will automatically:
   - Install required Python dependencies (`hidapi`, `psutil`)
   - Create your user configuration in `%APPDATA%\cooler-display\`
   - Set up silent auto-start on Windows boot
   - Start the driver immediately

### 3. Using the Windows GUI
Double-click **`run_gui.bat`** to launch the GUI Manager to switch display modes and view live telemetry!

- **To start driver:** Double-click `windows_start.bat`
- **To stop driver:** Double-click `windows_stop.bat`
- **To uninstall:** Double-click `windows_uninstall.bat`

---

## 🐧 Linux Setup

### Option 1: One-Click Installer (Recommended)

```bash
wget https://raw.githubusercontent.com/codersagor24/redragon-cc1014-linux/master/cooler-display-installer.run
chmod +x cooler-display-installer.run
sudo ./cooler-display-installer.run
```

### Option 2: Clone & Install

```bash
git clone https://github.com/codersagor24/redragon-cc1014-linux.git
cd redragon-cc1014-linux
sudo ./install.sh
```

### Linux GUI Manager
Launch from your application menu: **Cooler Display Manager**  
Or run in terminal: `cooler-display-ui`

The GUI lets you:
- 👁️ **See live stats** — CPU temp, GPU temp, NVMe temp, CPU load, GPU load, RAM, Disk, GPU power, Network speed (download/upload), CPU frequency
- ▶️ **Start / Stop / Restart** the background service
- 🔄 **Switch between 18+ display modes** across 6 categories
- 🚨 **Configure temperature alert thresholds** (e.g., flash `99` if CPU hits 80°C+)

---

## 🛠️ Display Modes

You can switch modes with one click inside the GUI or by editing `/etc/cooler-display.conf`.

### 🌡️ Temperature
| Mode Key | Name | What Shows on Cooler Display |
| :--- | :--- | :--- |
| `cpu_temp` *(default)* | **CPU Temperature** | CPU package temperature in °C |
| `gpu_temp` | **GPU Temperature** | NVIDIA GPU temperature in °C |
| `nvme_temp` | **NVMe SSD Temperature** | M.2 NVMe SSD drive temperature in °C |
| `hottest` | **Hottest Component** | Whichever of CPU or GPU is currently running hotter |
| `alternating` | **Alternating Mode** | Cycles between CPU and GPU temp every 5 seconds |

### 📊 Load & Utilization
| Mode Key | Name | What Shows on Cooler Display |
| :--- | :--- | :--- |
| `cpu_load` | **CPU Load** | Total CPU utilization percentage (0–99%) |
| `gpu_load` | **GPU Load** | GPU core utilization percentage (0–100%) |
| `ram_pct` | **RAM Usage %** | System memory usage percentage (0–100%) |
| `disk_pct` | **Disk Usage %** | Root disk storage utilization percentage (0–100%) |

### ⚡ Performance & Sensors
| Mode Key | Name | What Shows on Cooler Display |
| :--- | :--- | :--- |
| `cpu_freq_ghz10` | **CPU Frequency** | CPU speed in GHz × 10 (e.g., `34` = 3.4 GHz) |
| `gpu_power` | **GPU Power Draw** | GPU current power consumption in Watts |
| `gpu_fan` | **GPU Fan Speed** | GPU fan duty cycle percentage (0–100%) |
| `disk_mbps` | **Disk I/O** | Real-time disk read + write throughput in MB/s |

### 🌐 Network
| Mode Key | Name | What Shows on Cooler Display |
| :--- | :--- | :--- |
| `net_dl_kbps` | **Download Speed (KB/s)** | Live incoming network throughput (0–999 KB/s) |
| `net_ul_kbps` | **Upload Speed (KB/s)** | Live outgoing network throughput (0–999 KB/s) |
| `net_dl_mbps` | **Download Speed (Mbps)** | Live incoming network throughput in Megabits/s |

### 🕐 Time & System
| Mode Key | Name | What Shows on Cooler Display |
| :--- | :--- | :--- |
| `clock_hour` | **Current Hour** | 24-hour format hour (0–23) |
| `clock_minute` | **Current Minute** | Current minute (0–59) |
| `uptime_hours` | **System Uptime** | Hours system has been running since boot |
| `ram_used_gb` | **RAM Used (GB)** | Active physical memory in Gigabytes |

### 🚨 Alert Mode
| Mode Key | Name | Description |
| :--- | :--- | :--- |
| `alert` | **Temperature Alert** | Displays CPU temp normally, but flashes a configurable warning value (default: `99`) when CPU temperature reaches or exceeds the threshold (default: `80°C`). |

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
