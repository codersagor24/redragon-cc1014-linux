# Supported and Compatible Devices Guide

This document catalogs hardware compatibility for this driver and provides guidance for community contributors looking to add support for other digital displays.

---

## 🎯 Tier 1: Confirmed Working (Native Support)

These devices use the **Ruilian Micro Technology / Witmod HID Controller (`0x5131:0x2007`)** and the 65-byte output report protocol implemented directly in this repository.

| Manufacturer | Model | Type | Display Type | USB ID | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Redragon** | **CC-1014** | Air Cooler (Tower) | 7-Segment Digital LED | `5131:2007` | **Verified Working** |
| **Redragon** | **CC-1015 / CC-101x Series** | Air Cooler | 7-Segment Digital LED | `5131:2007` | **Fully Compatible** |

---

## 🔄 Tier 2: Hardware Siblings (Same `5131:2007` Controller)

The following devices share the exact same internal USB HID controller (`ID 5131:2007`, often identified in `lsusb` as `MSR MSR-101U Mini HID` or `Ruilian Micro / Witmod`). They accept the same or slightly tailored HID packet structure:

| Manufacturer | Model | Type | Notes |
| :--- | :--- | :--- | :--- |
| **darkFlash** | **Nebula DN240D** | 240mm AIO Liquid Cooler | Fixed-segment pump display with temp & usage |
| **darkFlash** | **Nebula DN360D** | 360mm AIO Liquid Cooler | Same pump display module as DN240D |
| **darkFlash** | **DH360D** | 360mm AIO Liquid Cooler | Digital LCD/segment cap |
| **Generic / OEM** | **4FAN XZ Bit** | PC Case Telemetry Display | Telemetry screen using 5131:2007 |
| **White-label ODM**| **Witmod / Ruilian OEM displays** | Various Air/AIO Coolers | Sold under various regional budget PC brands |

> [!TIP]
> If you own one of the Tier 2 devices, run `sudo ./install.sh`. If any byte offsets differ for secondary icons, please submit an issue or PR!

---

## 🔍 Tier 3: Other Popular Digital Coolers (Architecture Comparison)

Several other brands produce CPU coolers with integrated digital temperature displays. While they also connect via an internal USB 2.0 9-pin header, they use different USB microcontroller ICs and packet protocols:

### 1. DeepCool Digital Series
* **Models**: AK400 Digital, AK500 Digital, AK620 Digital, AG400 Digital, AG620 Digital, Assassin IV.
* **USB ID**: `34d8:0001` or `0483:5750`
* **Controller**: STMicroelectronics / Artery MCU
* **Protocol**: Typically uses a 16-byte or 64-byte HID feature report starting with `0x10` or `0x00`.

### 2. Thermalright Digital Series
* **Models**: Peerless Assassin 120 Digital, Phantom Spirit 120 Digital, Frost Commander 140 Digital.
* **USB ID**: Often uses WCH (WinChipHead) CH552 or similar USB microcontroller.
* **Protocol**: Proprietary HID packet stream.

### 3. Jonsbo Digital Series
* **Models**: CR-1000 EVO Digital, CR-1400 EVO Digital.
* **USB ID**: Holtek or standard Chinese USB HID vendor.

---

## 🤝 How to Add Support for New Coolers

We welcome contributions to expand this project into a unified Linux driver for all digital CPU coolers!

### Steps to contribute a new device:
1. Run `lsusb` and identify your cooler's Vendor ID and Product ID:
   ```bash
   lsusb
   ```
2. Inspect the raw HID reports sent by the official Windows software using Wireshark + USBPcap or reverse engineering the Windows utility (as done here).
3. Open a pull request:
   - Add your device VID/PID to the udev rules (`99-cooler-display.rules`).
   - Add a device profile or packet builder function to `cooler_display.py`.
   - Update this `DEVICES.md` table!
