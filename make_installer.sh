#!/usr/bin/env bash
# make_installer.sh — Build self-extracting .run installer
# Run this once to generate: cooler-display-installer.run
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$SCRIPT_DIR/cooler-display-installer.run"

echo "[*] Building self-extracting installer..."

# Create a tar.gz of all project files
cd "$SCRIPT_DIR"
tar czf /tmp/cooler_payload.tar.gz \
    cooler_display.py \
    cooler_display_ui.py \
    install.sh \
    uninstall.sh \
    cooler-display.service \
    cooler-display.desktop \
    99-cooler-display.rules

# Write the stub + payload into a single .run file
cat > "$OUT" << 'STUB_EOF'
#!/usr/bin/env bash
# Cooler Display Driver — Self-Extracting Installer
# Double-click or run: bash cooler-display-installer.run

set -e

echo "======================================================"
echo "  🧊  Cooler Display Driver — Self-Extracting Installer"
echo "======================================================"
echo ""

# Ask for sudo upfront
if [ "$EUID" -ne 0 ]; then
    echo "[*] Root access is required for installation."
    exec sudo bash "$0" "$@"
fi

# Extract payload to a temp directory
TMPDIR_INST="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_INST"' EXIT

echo "[*] Extracting files..."
PAYLOAD_LINE=$(awk '/^__PAYLOAD_BELOW__/{print NR+1; exit}' "$0")
tail -n +"$PAYLOAD_LINE" "$0" | tar xz -C "$TMPDIR_INST"

# Run installer
chmod +x "$TMPDIR_INST/install.sh"
bash "$TMPDIR_INST/install.sh"

exit 0
__PAYLOAD_BELOW__
STUB_EOF

# Append binary payload
cat /tmp/cooler_payload.tar.gz >> "$OUT"
chmod +x "$OUT"
rm -f /tmp/cooler_payload.tar.gz

echo ""
echo "[✓] Created: $OUT"
echo "    Users can install with:  sudo ./cooler-display-installer.run"
echo "    Or just double-click it in a file manager (if executable)."
