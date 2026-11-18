#!/usr/bin/env bash
# install.sh — Cooler Display Driver Installer
# Supports: Ubuntu/Debian (apt), Arch Linux (pacman), Fedora/RHEL (dnf), openSUSE (zypper)
set -e

if [ "$EUID" -ne 0 ]; then
    echo "[-] Please run as root: sudo ./install.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "======================================================"
echo "  🧊  Cooler Display Driver — Installer"
echo "======================================================"
echo ""

# ── 1. Install dependencies ───────────────────────────────
echo "[1/6] Installing dependencies..."
if command -v apt-get &>/dev/null; then
    echo "      Detected: Debian / Ubuntu (apt)"
    apt-get update -qq
    apt-get install -y python3-hid python3-psutil lm-sensors python3-gi gir1.2-gtk-3.0
elif command -v pacman &>/dev/null; then
    echo "      Detected: Arch Linux (pacman)"
    pacman -Sy --noconfirm python-hidapi python-psutil lm_sensors python-gobject gtk3
elif command -v dnf &>/dev/null; then
    echo "      Detected: Fedora / RHEL (dnf)"
    dnf install -y python3-hidapi python3-psutil lm_sensors python3-gobject gtk3
elif command -v zypper &>/dev/null; then
    echo "      Detected: openSUSE (zypper)"
    zypper install -y python3-hidapi python3-psutil sensors python3-gobject gtk3
else
    echo "      [!] Unknown distro — please install manually:"
    echo "          python3-hid, python3-psutil, lm-sensors, python3-gi, gtk3"
fi

# ── 2. udev rule ──────────────────────────────────────────
echo "[2/6] Installing udev rule (non-root USB access)..."
cp "$SCRIPT_DIR/99-cooler-display.rules" /etc/udev/rules.d/99-cooler-display.rules
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger               2>/dev/null || true

# ── 3. Config file ────────────────────────────────────────
echo "[3/6] Installing default config..."
if [ ! -f /etc/cooler-display.conf ]; then
    cat <<EOF > /etc/cooler-display.conf
mode="cpu_temp"
alert_enabled="0"
alert_temp="80"
alert_value="99"
EOF
fi

# ── 4. Daemon ─────────────────────────────────────────────
echo "[4/6] Installing daemon..."
cp "$SCRIPT_DIR/cooler_display.py" /usr/local/bin/cooler_display.py
chmod +x /usr/local/bin/cooler_display.py

# ── 5. GUI app ────────────────────────────────────────────
echo "[5/6] Installing GUI app..."
cp "$SCRIPT_DIR/cooler_display_ui.py" /usr/local/bin/cooler-display-ui
cp "$SCRIPT_DIR/cooler_display_ui_win.py" /usr/local/bin/cooler_display_ui_win.py 2>/dev/null || true
chmod +x /usr/local/bin/cooler-display-ui /usr/local/bin/cooler_display_ui_win.py 2>/dev/null || true

# Desktop entry
cp "$SCRIPT_DIR/cooler-display.desktop" /usr/share/applications/cooler-display.desktop
update-desktop-database /usr/share/applications/ 2>/dev/null || true

# ── 6. Systemd service ────────────────────────────────────
echo "[6/6] Enabling systemd service..."
cp "$SCRIPT_DIR/cooler-display.service" /etc/systemd/system/cooler-display.service
systemctl daemon-reload
systemctl enable cooler-display.service
systemctl restart cooler-display.service

echo ""
echo "======================================================"
echo "  ✅  Installation complete!"
echo ""
echo "  • Service is running in the background"
echo "  • Launch GUI: cooler-display-ui"
echo "                (or search 'Cooler Display' in your app menu)"
echo "  • Service logs: journalctl -u cooler-display.service -f"
echo "  • Uninstall:    sudo ./uninstall.sh"
echo "======================================================"
