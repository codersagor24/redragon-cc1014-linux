#!/usr/bin/env bash
# uninstall.sh — Remove Cooler Display Driver completely
set -e

if [ "$EUID" -ne 0 ]; then
    echo "[-] Please run as root: sudo ./uninstall.sh"
    exit 1
fi

echo "======================================================"
echo "  🗑️   Cooler Display Driver — Uninstaller"
echo "======================================================"

systemctl stop    cooler-display.service 2>/dev/null || true
systemctl disable cooler-display.service 2>/dev/null || true

rm -f /etc/systemd/system/cooler-display.service
rm -f /usr/local/bin/cooler_display.py
rm -f /usr/local/bin/cooler-display-ui
rm -f /etc/udev/rules.d/99-cooler-display.rules
rm -f /etc/cooler-display.conf
rm -f /usr/share/applications/cooler-display.desktop

systemctl daemon-reload
udevadm control --reload-rules 2>/dev/null || true
update-desktop-database /usr/share/applications/ 2>/dev/null || true

echo ""
echo "  ✅  Uninstalled successfully."
echo "======================================================"
