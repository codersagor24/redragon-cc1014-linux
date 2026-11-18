#!/usr/bin/env python3
"""
Cooler Display Manager — GTK3 GUI
Controls the cooler-display systemd service and shows live system telemetry.
Supports all display modes: CPU/GPU temps, RAM, Disk, Network, Clock, Alert, and more.
"""

try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, GLib
except Exception:
    # Fallback to Tkinter GUI on Windows or headless environments without GTK3
    from cooler_display_ui_win import main as win_main
    if __name__ == "__main__":
        win_main()
    sys.exit(0)

import subprocess
import psutil
import time
import threading
import os
import sys
import glob

APP_NAME    = "Cooler Display Manager"
SERVICE     = "cooler-display.service"
CONFIG_PATH = "/etc/cooler-display.conf"

# ── All display modes ─────────────────────────────────────────────────────────
MODE_GROUPS = [
    ("🌡️  Temperature", [
        ("cpu_temp",    "CPU Temperature (°C)"),
        ("gpu_temp",    "GPU Temperature (°C)"),
        ("nvme_temp",   "NVMe SSD Temperature (°C)"),
        ("hottest",     "Hottest Component (CPU vs GPU)"),
        ("alternating", "Alternating: CPU ↔ GPU every 5s"),
    ]),
    ("📊  Load & Usage", [
        ("cpu_load",        "CPU Load (%)"),
        ("gpu_load",        "GPU Load (%)"),
        ("ram_pct",         "RAM Usage (%)"),
        ("disk_pct",        "Disk Usage (%)"),
    ]),
    ("⚡  Performance", [
        ("cpu_freq_ghz10",  "CPU Frequency (GHz × 10, e.g. 34 = 3.4GHz)"),
        ("gpu_power",       "GPU Power Draw (Watts)"),
        ("gpu_fan",         "GPU Fan Speed (%)"),
        ("disk_mbps",       "Disk I/O Speed (MB/s)"),
    ]),
    ("🌐  Network", [
        ("net_dl_kbps",     "Download Speed (KB/s)"),
        ("net_ul_kbps",     "Upload Speed (KB/s)"),
        ("net_dl_mbps",     "Download Speed (Mbps)"),
    ]),
    ("🕐  Time & System", [
        ("clock_hour",      "Clock — Current Hour (0–23)"),
        ("clock_minute",    "Clock — Current Minute (0–59)"),
        ("uptime_hours",    "System Uptime (hours)"),
        ("ram_used_gb",     "RAM Used (GB)"),
    ]),
    ("🚨  Alert", [
        ("alert",           "Alert Mode — flashes when temp threshold exceeded"),
    ]),
]

# Flat list for lookup
ALL_MODES = [(mid, mlbl) for _, modes in MODE_GROUPS for mid, mlbl in modes]


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


def read_config():
    cfg = {"mode": "cpu_temp", "alert_enabled": "0", "alert_temp": "80", "alert_value": "99"}
    try:
        with open(CONFIG_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return cfg


def write_config(cfg_dict):
    lines = [f'{k}="{v}"' for k, v in cfg_dict.items()]
    content = "\n".join(lines) + "\n"
    try:
        with open(CONFIG_PATH, "w") as f:
            f.write(content)
        return True
    except PermissionError:
        escaped = content.replace('"', '\\"')
        ok, _, _ = run_cmd(["bash", "-c", f'echo "{escaped}" > {CONFIG_PATH}'], use_sudo=True)
        return ok


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


def get_nvme_temperature():
    try:
        temps = psutil.sensors_temperatures()
        if "nvme" in temps:
            for e in temps["nvme"]:
                if e.current and e.current > 0:
                    return e.current
    except Exception:
        pass
    return None


def get_gpu_metrics():
    result = {"temp": None, "load": None, "power_w": None, "fan_pct": None}
    try:
        out = subprocess.check_output(
            ["nvidia-smi",
             "--query-gpu=temperature.gpu,utilization.gpu,power.draw,fan.speed",
             "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=1
        ).decode().strip().split("\n")[0].split(",")
        result["temp"]    = int(out[0].strip())
        result["load"]    = int(out[1].strip())
        result["power_w"] = int(float(out[2].strip()))
        result["fan_pct"] = int(out[3].strip())
    except Exception:
        pass
    return result


_last_net = None
_last_net_t = 0

def get_network_speed():
    global _last_net, _last_net_t
    try:
        io = psutil.net_io_counters()
        now = time.time()
        if _last_net and now > _last_net_t:
            dt = now - _last_net_t
            dl = (io.bytes_recv - _last_net.bytes_recv) / (1024 * dt)
            ul = (io.bytes_sent - _last_net.bytes_sent) / (1024 * dt)
            _last_net, _last_net_t = io, now
            return max(0, dl), max(0, ul)
        _last_net, _last_net_t = io, now
    except Exception:
        pass
    return 0.0, 0.0


# ── App ───────────────────────────────────────────────────────────────────────

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
        self.set_default_size(500, 700)
        self.set_resizable(True)
        self.set_border_width(0)
        self._selected_mode = "cpu_temp"
        self._cfg = read_config()
        self._selected_mode = self._cfg.get("mode", "cpu_temp")
        self._build_ui()
        GLib.timeout_add(1000, self._refresh_status)

    def _build_ui(self):
        # Main vertical box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        # ── Header ──
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header.set_margin_top(20)
        header.set_margin_bottom(14)
        header.set_margin_start(20)
        header.set_margin_end(20)

        title = Gtk.Label()
        title.set_markup('<span size="15000" weight="bold">🧊  Cooler Display Manager</span>')
        title.set_halign(Gtk.Align.START)
        sub = Gtk.Label(label="Linux driver for USB digital cooler displays")
        sub.set_halign(Gtk.Align.START)
        sub.get_style_context().add_class("dim-label")
        header.pack_start(title, False, False, 0)
        header.pack_start(sub,   False, False, 0)
        vbox.pack_start(header, False, False, 0)
        vbox.pack_start(Gtk.Separator(), False, False, 0)

        # ── Scrollable content ──
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scroll, True, True, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(20)
        content.set_margin_end(20)
        scroll.add(content)

        # Service card
        content.pack_start(self._section("Service"), False, False, 0)
        content.pack_start(self._build_service_card(), False, False, 0)

        # Live telemetry
        content.pack_start(self._section("Live Telemetry"), False, False, 0)
        content.pack_start(self._build_telemetry_card(), False, False, 0)

        # Display mode selector
        content.pack_start(self._section("Display Mode"), False, False, 0)
        content.pack_start(self._build_mode_card(), False, False, 0)

        # Alert settings
        content.pack_start(self._section("Alert Settings"), False, False, 0)
        content.pack_start(self._build_alert_card(), False, False, 0)

        self.show_all()

    # ── Section label ──

    def _section(self, text):
        lbl = Gtk.Label()
        lbl.set_markup(f"<b>{text}</b>")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_margin_top(4)
        return lbl

    # ── Service card ──

    def _build_service_card(self):
        frame = Gtk.Frame()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(12); box.set_margin_bottom(12)
        box.set_margin_start(16); box.set_margin_end(16)
        frame.add(box)

        self._status_dot = Gtk.Label(label="⬤")
        self._status_lbl = Gtk.Label(label="Checking...")
        self._status_lbl.set_halign(Gtk.Align.START)

        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_row.pack_start(self._status_dot, False, False, 0)
        status_row.pack_start(self._status_lbl, True, True, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._start_btn   = Gtk.Button(label="▶ Start")
        self._stop_btn    = Gtk.Button(label="⏹ Stop")
        self._restart_btn = Gtk.Button(label="↺ Restart")
        self._start_btn.get_style_context().add_class("suggested-action")
        self._stop_btn.get_style_context().add_class("destructive-action")
        self._start_btn.connect("clicked",   lambda b: self._svc("start"))
        self._stop_btn.connect("clicked",    lambda b: self._svc("stop"))
        self._restart_btn.connect("clicked", lambda b: self._svc("restart"))
        btn_box.pack_start(self._start_btn,   False, False, 0)
        btn_box.pack_start(self._stop_btn,    False, False, 0)
        btn_box.pack_start(self._restart_btn, False, False, 0)

        box.pack_start(status_row, True,  True,  0)
        box.pack_start(btn_box,    False, False, 0)
        return frame

    # ── Telemetry card ──

    def _build_telemetry_card(self):
        frame = Gtk.Frame()
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(8)
        grid.set_margin_top(12); grid.set_margin_bottom(12)
        grid.set_margin_start(16); grid.set_margin_end(16)
        frame.add(grid)

        def row(icon, label, r):
            il = Gtk.Label(label=icon); il.set_halign(Gtk.Align.START)
            ll = Gtk.Label(label=label); ll.set_halign(Gtk.Align.START)
            ll.get_style_context().add_class("dim-label")
            vl = Gtk.Label(label="—"); vl.set_halign(Gtk.Align.END); vl.set_hexpand(True)
            vl.set_markup("<b>—</b>")
            grid.attach(il, 0, r, 1, 1)
            grid.attach(ll, 1, r, 1, 1)
            grid.attach(vl, 2, r, 1, 1)
            return vl

        self._t_cpu_temp  = row("🌡️",  "CPU Temperature",    0)
        self._t_gpu_temp  = row("🎮",  "GPU Temperature",    1)
        self._t_nvme_temp = row("💾",  "NVMe Temperature",   2)
        self._t_cpu_load  = row("📊",  "CPU Load",           3)
        self._t_gpu_load  = row("🖥️",  "GPU Load",           4)
        self._t_ram       = row("🧠",  "RAM Usage",          5)
        self._t_disk      = row("🗄️",  "Disk Usage",         6)
        self._t_gpu_pwr   = row("⚡",  "GPU Power Draw",     7)
        self._t_net_dl    = row("⬇️",  "Download Speed",     8)
        self._t_net_ul    = row("⬆️",  "Upload Speed",       9)
        self._t_cpu_freq  = row("🔥",  "CPU Frequency",     10)
        return frame

    # ── Mode card ──

    def _build_mode_card(self):
        frame = Gtk.Frame()
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_top(12); outer.set_margin_bottom(12)
        outer.set_margin_start(16); outer.set_margin_end(16)
        frame.add(outer)

        self._mode_btns = {}
        first = None
        for group_name, modes in MODE_GROUPS:
            lbl = Gtk.Label()
            lbl.set_markup(f'<small><b>{group_name}</b></small>')
            lbl.set_halign(Gtk.Align.START)
            lbl.set_margin_top(6)
            outer.pack_start(lbl, False, False, 0)
            for mode_id, mode_label in modes:
                if first is None:
                    btn = Gtk.RadioButton.new_with_label(None, mode_label)
                    first = btn
                else:
                    btn = Gtk.RadioButton.new_with_label_from_widget(first, mode_label)
                if mode_id == self._selected_mode:
                    btn.set_active(True)
                btn.connect("toggled", self._on_mode_toggled, mode_id)
                self._mode_btns[mode_id] = btn
                outer.pack_start(btn, False, False, 0)

        apply = Gtk.Button(label="✅  Apply Mode & Restart Service")
        apply.get_style_context().add_class("suggested-action")
        apply.set_margin_top(10)
        apply.connect("clicked", self._on_apply)
        outer.pack_start(apply, False, False, 0)
        return frame

    # ── Alert card ──

    def _build_alert_card(self):
        frame = Gtk.Frame()
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(8)
        grid.set_margin_top(12); grid.set_margin_bottom(12)
        grid.set_margin_start(16); grid.set_margin_end(16)
        frame.add(grid)

        def lbl(text, row, col):
            l = Gtk.Label(label=text)
            l.set_halign(Gtk.Align.START)
            grid.attach(l, col, row, 1, 1)
            return l

        lbl("Temperature threshold (°C):", 0, 0)
        self._alert_temp = Gtk.SpinButton.new_with_range(50, 100, 1)
        self._alert_temp.set_value(int(self._cfg.get("alert_temp", "80")))
        grid.attach(self._alert_temp, 1, 0, 1, 1)

        lbl("Value to flash when triggered:", 1, 0)
        self._alert_val = Gtk.SpinButton.new_with_range(0, 99, 1)
        self._alert_val.set_value(int(self._cfg.get("alert_value", "99")))
        grid.attach(self._alert_val, 1, 1, 1, 1)

        hint = Gtk.Label()
        hint.set_markup('<small><span foreground="gray">Use Alert Mode above to enable. Display flashes between current temp and this value.</span></small>')
        hint.set_line_wrap(True)
        hint.set_halign(Gtk.Align.START)
        grid.attach(hint, 0, 2, 2, 1)
        return frame

    # ── Callbacks ──────────────────────────────────────────────────────────

    def _on_mode_toggled(self, btn, mode_id):
        if btn.get_active():
            self._selected_mode = mode_id

    def _on_apply(self, btn):
        self._cfg["mode"] = self._selected_mode
        self._cfg["alert_temp"]   = str(int(self._alert_temp.get_value()))
        self._cfg["alert_value"]  = str(int(self._alert_val.get_value()))
        write_config(self._cfg)
        self._svc("restart")
        # Find mode label
        label = next((l for mid, l in ALL_MODES if mid == self._selected_mode), self._selected_mode)
        self._toast(f"Mode set to:\n{label}")

    def _svc(self, action):
        def do():
            run_cmd(["systemctl", action, SERVICE], use_sudo=True)
            GLib.idle_add(self._refresh_status)
        threading.Thread(target=do, daemon=True).start()

    # ── Live refresh ───────────────────────────────────────────────────────

    def _refresh_status(self):
        status = get_service_status()
        active = status == "active"

        if active:
            self._status_dot.set_markup('<span foreground="#2ecc71">⬤</span>')
            self._status_lbl.set_text("Running")
        elif status in ("inactive", "failed", "dead"):
            self._status_dot.set_markup('<span foreground="#e74c3c">⬤</span>')
            self._status_lbl.set_text(f"Stopped ({status})")
        else:
            self._status_dot.set_markup('<span foreground="#f39c12">⬤</span>')
            self._status_lbl.set_text(f"Status: {status}")

        self._start_btn.set_sensitive(not active)
        self._stop_btn.set_sensitive(active)

        # Gather telemetry
        cpu_temp  = get_cpu_temperature()
        nvme_temp = get_nvme_temperature()
        gpu       = get_gpu_metrics()
        mem       = psutil.virtual_memory()
        disk      = psutil.disk_usage("/")
        cpu_load  = psutil.cpu_percent(interval=None)
        cpu_freq  = psutil.cpu_freq()
        dl, ul    = get_network_speed()

        def v(val, fmt):
            return fmt.format(val) if val is not None else "N/A"

        self._t_cpu_temp.set_markup(f"<b>{v(cpu_temp, '{:.0f} °C')}</b>")
        self._t_gpu_temp.set_markup(f"<b>{v(gpu['temp'], '{} °C')}</b>")
        self._t_nvme_temp.set_markup(f"<b>{v(nvme_temp, '{:.0f} °C')}</b>")
        self._t_cpu_load.set_markup(f"<b>{cpu_load:.0f} %</b>")
        self._t_gpu_load.set_markup(f"<b>{v(gpu['load'], '{} %')}</b>")
        self._t_ram.set_markup(f"<b>{mem.percent:.0f} %  ({mem.used/1024**3:.1f} / {mem.total/1024**3:.0f} GB)</b>")
        self._t_disk.set_markup(f"<b>{disk.percent:.0f} %  ({disk.used/1024**3:.0f} / {disk.total/1024**3:.0f} GB)</b>")
        self._t_gpu_pwr.set_markup(f"<b>{v(gpu['power_w'], '{} W')}</b>")
        self._t_net_dl.set_markup(f"<b>{dl:.0f} KB/s</b>")
        self._t_net_ul.set_markup(f"<b>{ul:.0f} KB/s</b>")
        if cpu_freq:
            self._t_cpu_freq.set_markup(f"<b>{cpu_freq.current:.0f} MHz  ({cpu_freq.current/1000:.2f} GHz)</b>")
        return True

    def _toast(self, msg):
        d = Gtk.MessageDialog(transient_for=self, flags=0,
                              message_type=Gtk.MessageType.INFO,
                              buttons=Gtk.ButtonsType.OK, text=msg)
        d.run(); d.destroy()


def main():
    app = CoolerDisplayApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
