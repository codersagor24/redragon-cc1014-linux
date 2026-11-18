#!/usr/bin/env bash
set -e

# Make sure the script is run with root privileges
if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run as root (e.g., sudo ./install.sh)"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[+] Installing Redragon CC-1014 Display Driver from $SCRIPT_DIR..."

# Detect Package Manager and Install Dependencies
if command -v apt-get &>/dev/null; then
    echo "[+] Detected Debian/Ubuntu based system (apt)..."
    apt-get update
    apt-get install -y python3-hid python3-psutil lm-sensors
elif command -v pacman &>/dev/null; then
    echo "[+] Detected Arch Linux based system (pacman)..."
    pacman -Sy --noconfirm python-hidapi python-psutil lm_sensors
elif command -v dnf &>/dev/null; then
    echo "[+] Detected Fedora/RHEL based system (dnf)..."
    dnf install -y python3-hidapi python3-psutil lm_sensors
elif command -v zypper &>/dev/null; then
    echo "[+] Detected openSUSE based system (zypper)..."
    zypper install -y python3-hidapi python3-psutil sensors
else
    echo "[!] Warning: Unknown package manager. Please ensure python3, hidapi, psutil, and lm-sensors are installed manually."
fi

# 1. Install udev rule
echo "[+] Installing udev rule..."
cp "$SCRIPT_DIR/99-cooler-display.rules" /etc/udev/rules.d/99-cooler-display.rules
udevadm control --reload-rules || true
udevadm trigger || true

# 2. Install daemon script
echo "[+] Installing daemon script to /usr/local/bin/cooler_display.py..."
cp "$SCRIPT_DIR/cooler_display.py" /usr/local/bin/cooler_display.py
chmod +x /usr/local/bin/cooler_display.py

# 3. Install and start systemd service
echo "[+] Installing and enabling systemd service..."
cp "$SCRIPT_DIR/cooler-display.service" /etc/systemd/system/cooler-display.service
systemctl daemon-reload
systemctl enable cooler-display.service
systemctl restart cooler-display.service

echo ""
echo "=========================================================="
echo " [✓] Installation complete! The display should now be on."
echo " Check live status: systemctl status cooler-display.service"
echo " View real-time logs: journalctl -u cooler-display.service -f"
echo "=========================================================="
