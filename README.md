# Redragon CC-1014 CPU Cooler Digital Display Driver for Linux

Linux driver and systemd daemon for the **Redragon CC-1014** CPU cooler digital temperature display (USB HID `ID 5131:2007`).

Reverse engineered from the official Redragon Windows utility (`PcInfoMonitorPro.exe`).

---

## 🚀 এক ক্লিকে ইনস্টলেশন (Quick 1-Command Install)

ভবিষ্যতে যেকোনো নতুন লিনাক্স (Ubuntu, Debian, Fedora, Arch Linux, Manjaro, ইত্যাদি) ইনস্টল করার পর এই ফোল্ডারে এসে টার্মিনালে শুধু একটি কমান্ড রান করবেন:

```bash
sudo ./install.sh
```

এই স্ক্রিপ্টটি স্বয়ংক্রিয়ভাবে:
1. প্রয়োজনীয় প্যাকেজ (`python3-hid`, `python3-psutil`, `lm-sensors`) ইনস্টল করবে।
2. USB পারমিশন udev রুল সেট করবে।
3. পাইথন প্রোগ্রামটি `/usr/local/bin/cooler_display.py` তে রাখবে।
4. ব্যাকগ্রাউন্ড `cooler-display.service` সিস্টেমডি সার্ভিস চালু ও বুট টাইমে অটো-রান কনফিগার করবে।

---

## 🛠 স্ট্যাটাস চেক ও কন্ট্রোল (Commands)

- **লাইভ স্ট্যাটাস দেখতে:**
  ```bash
  systemctl status cooler-display.service
  ```
- **রিয়েলটাইম লগ দেখতে:**
  ```bash
  journalctl -u cooler-display.service -f
  ```
- **সার্ভিস রিস্টার্ট করতে:**
  ```bash
  sudo systemctl restart cooler-display.service
  ```
- **আনইনস্টল করতে:**
  ```bash
  sudo ./uninstall.sh
  ```

---

## 💾 এই কোডটি নিরাপদে সেভ রাখার উপায় (Backup Options)

### উপায় ১: GitHub-এ সেভ রাখা (সবচেয়ে সুবিধাজনক ও নিরাপদ)
আপনার GitHub অ্যাকাউন্টে একটি নতুন Repository তৈরি করে (যেমন: `redragon-cc1014-linux`) নিচের কমান্ডগুলো দিয়ে পুশ করে রাখতে পারেন:

```bash
cd ~/redragon-cc1014-linux
git init
git add .
git commit -m "Initial commit of Redragon CC-1014 Linux driver"
git branch -M main
git remote add origin https://github.com/<your-username>/redragon-cc1014-linux.git
git push -u origin main
```
ভবিষ্যতে নতুন লিনাক্সে শুধু `git clone <repo-url>` করে `sudo ./install.sh` রান করলেই কাজ হয়ে যাবে!

### উপায় ২: পেনড্রাইভ বা পার্সোনাল হার্ডড্রাইভে সেভ রাখা
আপনার এক্সটার্নাল ড্রাইভ বা পেনড্রাইভে এই সম্পূর্ণ ফোল্ডারটি কপি করে রেখে দিন:
```bash
cp -r ~/redragon-cc1014-linux "/run/media/absagor/Sagor Personal/"
```

### উপায় ৩: একটি জিপ (.zip / .tar.gz) ফাইল হিসেবে ক্লাউডে (Google Drive) রাখা
```bash
tar -czvf ~/redragon-cc1014-linux.tar.gz -C ~ redragon-cc1014-linux
```
এই `redragon-cc1014-linux.tar.gz` ফাইলটি গুগল ড্রাইভে বা মেইলে সেভ রাখতে পারেন।

---

## 📊 রিভার্স-ইঞ্জিনিয়ার্ড HID প্রোটোকল (Protocol Details)

- **USB VID/PID**: `0x5131:0x2007` (Report ID: `0x00`)
- **Packet Size**: 65 Bytes
- `packet[0]`: `0x00` (Report ID)
- `packet[1]`: `0x40` (Header / Payload size 64)
- `packet[2]`: **CPU Temperature (°C)**
- `packet[3]`: **CPU Usage %**
- `packet[4..5]`: CPU Clock (MHz, 16-bit Big-Endian)
- `packet[6..7]`: CPU Fan RPM
- `packet[8..9]`: CPU Power (W)
- `packet[10]`: GPU Temperature (°C)
- `packet[11]`: GPU Usage %
- `packet[12..64]`: `0x00` Zero padding
