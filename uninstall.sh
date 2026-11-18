#!/usr/bin/env bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run as root (e.g., sudo ./uninstall.sh)"
  exit 1
fi

echo "[+] Stopping and disabling cooler-display.service..."
systemctl stop cooler-display.service || true
systemctl disable cooler-display.service || true

echo "[+] Removing installed files..."
rm -f /etc/systemd/system/cooler-display.service
rm -f /usr/local/bin/cooler_display.py
rm -f /etc/udev/rules.d/99-cooler-display.rules

systemctl daemon-reload
udevadm control --reload-rules || true
udevadm trigger || true

echo "[✓] Uninstalled successfully."
