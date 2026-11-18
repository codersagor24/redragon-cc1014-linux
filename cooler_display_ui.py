#!/usr/bin/env python3
"""
Cooler Display Manager — GTK3 GUI for Linux Digital Cooler Display Driver
Controls the cooler-display systemd service and shows live system telemetry.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

import subprocess
import psutil
import time
import threading
import os
import sys

APP_NAME    = "Cooler Display Manager"
SERVICE     = "cooler-display.service"
DAEMON_PATH = "/usr/local/bin/cooler_display.py"
CONFIG_PATH = "/etc/cooler-display.conf"

DISPLAY_MODES = [
    ("cpu_temp",   "🌡️  CPU Temperature"),
    ("gpu_temp",   "🎮  GPU Temperature"),
    ("cpu_load",   "📊  CPU Load %"),
    ("hottest",    "🔥  Hottest Component"),
    ("alternating","🔄  Alternating (CPU/GPU)"),
]


def run_cmd(cmd, use_sudo=False):
    if use_sudo:
        cmd = ["sudo"] + cmd
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def get_service_status():
    ok, out, _ = run_cmd(["systemctl", "is-active", SERVICE])
    return out.strip()


def get_cpu_temperature():
    try:
        temps = psutil.sensors_temperatures()
        if "k10temp" in temps:
            for e in temps["k10temp"]:
                if e.label == "Tctl":
                    return e.current
            return temps["k10temp"][0].current
        if "coretemp" in temps:
            for e in temps["coretemp"]:
                if "Package" in e.label:
                    return e.current
            return temps["coretemp"][0].current
        for entries in temps.values():
            if entries:
                return entries[0].current
    except Exception:
        pass
    return None


def get_gpu_temperature():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=1
        )
        return int(out.decode().strip().split("\n")[0])
    except Exception:
        return None


def read_config():
    mode = "cpu_temp"
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                for line in f:
                    if line.startswith("DISPLAY_MODE="):
                        mode = line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
    return {"mode": mode}


def write_config(mode):
    try:
        with open(CONFIG_PATH, "w") as f:
            f.write(f'DISPLAY_MODE="{mode}"\n')
        return True
    except PermissionError:
        ok, _, _ = run_cmd(["bash", "-c", f'echo DISPLAY_MODE=\\"{mode}\\" > {CONFIG_PATH}'], use_sudo=True)
        return ok


class CoolerDisplayApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.github.codersagor24.cooler-display")
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(self)
        self.window.present()


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME)
        self.set_default_size(420, 520)
        self.set_resizable(False)
        self.set_border_width(0)

        try:
            self.set_icon_name("temperature-symbolic")
        except Exception:
            pass

        self._build_ui()
        self._refresh_status()

        # Refresh telemetry every second
        GLib.timeout_add(1000, self._refresh_status)

    # ─── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(outer)

        # Header bar
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header.set_margin_top(24)
        header.set_margin_bottom(16)
        header.set_margin_start(24)
        header.set_margin_end(24)

        title_lbl = Gtk.Label(label="🧊  Cooler Display Manager")
        title_lbl.set_halign(Gtk.Align.START)
        title_attrs = Pango.AttrList()
        title_attrs.insert(Pango.AttrSize.new(16 * 1024))
        title_attrs.insert(Pango.AttrWeight.new(Pango.Weight.BOLD, 0, -1))
        title_lbl.set_attributes(title_attrs)

        sub_lbl = Gtk.Label(label="Linux driver for USB digital cooler displays")
        sub_lbl.set_halign(Gtk.Align.START)
        sub_lbl.get_style_context().add_class("dim-label")

        header.pack_start(title_lbl, False, False, 0)
        header.pack_start(sub_lbl, False, False, 0)
        outer.pack_start(header, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        outer.pack_start(sep, False, False, 0)

        # Main content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(24)
        content.set_margin_end(24)
        outer.pack_start(content, True, True, 0)

        # Service status card
        content.pack_start(self._make_section_label("Service"), False, False, 0)
        content.pack_start(self._build_service_card(), False, False, 0)

        # Live telemetry card
        content.pack_start(self._make_section_label("Live Telemetry"), False, False, 0)
        content.pack_start(self._build_telemetry_card(), False, False, 0)

        # Display mode card
        content.pack_start(self._make_section_label("Display Mode"), False, False, 0)
        content.pack_start(self._build_mode_card(), False, False, 0)

        self.show_all()

    def _make_section_label(self, text):
        lbl = Gtk.Label(label=f"<b>{text}</b>")
        lbl.set_use_markup(True)
        lbl.set_halign(Gtk.Align.START)
        lbl.set_margin_top(4)
        return lbl

    def _build_service_card(self):
        frame = Gtk.Frame()
        frame.get_style_context().add_class("view")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        frame.add(box)

        self.status_icon = Gtk.Label(label="⬤")
        self.status_lbl  = Gtk.Label(label="Checking...")
        self.status_lbl.set_halign(Gtk.Align.START)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)

        self.start_btn  = Gtk.Button(label="Start")
        self.stop_btn   = Gtk.Button(label="Stop")
        self.restart_btn = Gtk.Button(label="Restart")

        self.start_btn.get_style_context().add_class("suggested-action")
        self.stop_btn.get_style_context().add_class("destructive-action")

        self.start_btn.connect("clicked", self._on_start)
        self.stop_btn.connect("clicked", self._on_stop)
        self.restart_btn.connect("clicked", self._on_restart)

        btn_box.pack_start(self.start_btn,   False, False, 0)
        btn_box.pack_start(self.stop_btn,    False, False, 0)
        btn_box.pack_start(self.restart_btn, False, False, 0)

        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.pack_start(self.status_icon, False, False, 0)
        status_box.pack_start(self.status_lbl,  True,  True,  0)

        box.pack_start(status_box, True,  True,  0)
        box.pack_start(btn_box,    False, False, 0)

        return frame

    def _build_telemetry_card(self):
        frame = Gtk.Frame()
        frame.get_style_context().add_class("view")
        grid = Gtk.Grid()
        grid.set_column_spacing(32)
        grid.set_row_spacing(10)
        grid.set_margin_top(14)
        grid.set_margin_bottom(14)
        grid.set_margin_start(16)
        grid.set_margin_end(16)
        frame.add(grid)

        def make_stat(icon, label_text, row):
            icon_lbl = Gtk.Label(label=icon)
            icon_lbl.set_halign(Gtk.Align.START)
            lbl = Gtk.Label(label=label_text)
            lbl.set_halign(Gtk.Align.START)
            lbl.get_style_context().add_class("dim-label")
            val = Gtk.Label(label="—")
            val.set_halign(Gtk.Align.END)
            val.set_hexpand(True)
            attrs = Pango.AttrList()
            attrs.insert(Pango.AttrWeight.new(Pango.Weight.BOLD, 0, -1))
            val.set_attributes(attrs)
            grid.attach(icon_lbl, 0, row, 1, 1)
            grid.attach(lbl,      1, row, 1, 1)
            grid.attach(val,      2, row, 1, 1)
            return val

        self.cpu_temp_val  = make_stat("🌡️",  "CPU Temperature", 0)
        self.gpu_temp_val  = make_stat("🎮",  "GPU Temperature", 1)
        self.cpu_load_val  = make_stat("📊",  "CPU Load",        2)
        self.cpu_freq_val  = make_stat("⚡",  "CPU Frequency",   3)

        return frame

    def _build_mode_card(self):
        frame = Gtk.Frame()
        frame.get_style_context().add_class("view")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        frame.add(box)

        cfg = read_config()
        current_mode = cfg.get("mode", "cpu_temp")

        self.mode_buttons = {}
        first_btn = None

        for mode_id, mode_label in DISPLAY_MODES:
            if first_btn is None:
                btn = Gtk.RadioButton.new_with_label(None, mode_label)
                first_btn = btn
            else:
                btn = Gtk.RadioButton.new_with_label_from_widget(first_btn, mode_label)

            if mode_id == current_mode:
                btn.set_active(True)

            btn.connect("toggled", self._on_mode_changed, mode_id)
            self.mode_buttons[mode_id] = btn
            box.pack_start(btn, False, False, 0)

        apply_btn = Gtk.Button(label="Apply Mode & Restart Service")
        apply_btn.get_style_context().add_class("suggested-action")
        apply_btn.set_margin_top(6)
        apply_btn.connect("clicked", self._on_apply_mode)
        box.pack_start(apply_btn, False, False, 0)

        self._selected_mode = current_mode
        return frame

    # ─── Callbacks ──────────────────────────────────────────────────────────

    def _on_mode_changed(self, btn, mode_id):
        if btn.get_active():
            self._selected_mode = mode_id

    def _on_apply_mode(self, btn):
        write_config(self._selected_mode)
        self._service_action("restart")
        self._show_toast(f"Mode set to: {self._selected_mode.replace('_', ' ').title()}")

    def _on_start(self, btn):
        self._service_action("start")

    def _on_stop(self, btn):
        self._service_action("stop")

    def _on_restart(self, btn):
        self._service_action("restart")

    def _service_action(self, action):
        def do():
            run_cmd(["systemctl", action, SERVICE], use_sudo=True)
            GLib.idle_add(self._refresh_status)
        threading.Thread(target=do, daemon=True).start()

    # ─── Status Refresh ─────────────────────────────────────────────────────

    def _refresh_status(self):
        status = get_service_status()
        active = status == "active"
        inactive = status in ("inactive", "failed", "dead")

        if active:
            self.status_icon.set_markup('<span foreground="#2ecc71">⬤</span>')
            self.status_lbl.set_text("Running")
        elif inactive:
            self.status_icon.set_markup('<span foreground="#e74c3c">⬤</span>')
            self.status_lbl.set_text(f"Stopped ({status})")
        else:
            self.status_icon.set_markup('<span foreground="#f39c12">⬤</span>')
            self.status_lbl.set_text(f"Status: {status}")

        self.start_btn.set_sensitive(not active)
        self.stop_btn.set_sensitive(active)

        # Update telemetry
        cpu_temp = get_cpu_temperature()
        gpu_temp = get_gpu_temperature()
        cpu_load = psutil.cpu_percent(interval=None)
        freq_info = psutil.cpu_freq()
        cpu_freq = freq_info.current if freq_info else None

        self.cpu_temp_val.set_text(f"{cpu_temp:.0f} °C" if cpu_temp else "N/A")
        self.gpu_temp_val.set_text(f"{gpu_temp} °C"    if gpu_temp else "N/A")
        self.cpu_load_val.set_text(f"{cpu_load:.0f} %")
        self.cpu_freq_val.set_text(f"{cpu_freq:.0f} MHz" if cpu_freq else "N/A")

        return True  # keep timer alive

    def _show_toast(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message,
        )
        dialog.run()
        dialog.destroy()


def check_root_for_sudo():
    """Warn the user if sudo won't work without a password."""
    ok, _, _ = run_cmd(["sudo", "-n", "true"])
    if not ok:
        print("Warning: sudo requires a password. Service controls may not work.", file=sys.stderr)


def main():
    check_root_for_sudo()
    app = CoolerDisplayApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
