#!/usr/bin/env python3
"""
Cooler Display Manager — Windows & Cross-Platform Tkinter GUI
Controls the cooler_display daemon on Windows and Linux without requiring GTK.
Supports all 18+ display modes, live telemetry, and alert settings.
"""

import sys
import os
import subprocess
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import psutil

IS_WINDOWS = sys.platform.startswith("win")

def get_config_dir():
    if IS_WINDOWS:
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(appdata, "cooler-display")
    else:
        path = "/etc"
    os.makedirs(path, exist_ok=True)
    return path

def get_config_path():
    if IS_WINDOWS:
        return os.path.join(get_config_dir(), "cooler-display.conf")
    return "/etc/cooler-display.conf"

def get_pid_path():
    if IS_WINDOWS:
        return os.path.join(get_config_dir(), "cooler-display.pid")
    return "/run/cooler-display.pid"

CONFIG_PATH = get_config_path()
PID_PATH    = get_pid_path()
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DAEMON_SCRIPT = os.path.join(SCRIPT_DIR, "cooler_display.py")

MODE_GROUPS = [
    ("🌡️ Temperature", [
        ("cpu_temp",    "CPU Temperature (°C)"),
        ("gpu_temp",    "GPU Temperature (°C)"),
        ("nvme_temp",   "NVMe SSD Temperature (°C)"),
        ("hottest",     "Hottest Component (CPU vs GPU)"),
        ("alternating", "Alternating: CPU ↔ GPU every 5s"),
    ]),
    ("📊 Load & Usage", [
        ("cpu_load",        "CPU Load (%)"),
        ("gpu_load",        "GPU Load (%)"),
        ("ram_pct",         "RAM Usage (%)"),
        ("disk_pct",        "Disk Usage (%)"),
    ]),
    ("⚡ Performance", [
        ("cpu_freq_ghz10",  "CPU Frequency (GHz × 10, e.g. 34 = 3.4GHz)"),
        ("gpu_power",       "GPU Power Draw (Watts)"),
        ("gpu_fan",         "GPU Fan Speed (%)"),
        ("disk_mbps",       "Disk I/O Speed (MB/s)"),
    ]),
    ("🌐 Network", [
        ("net_dl_kbps",     "Download Speed (KB/s)"),
        ("net_ul_kbps",     "Upload Speed (KB/s)"),
        ("net_dl_mbps",     "Download Speed (Mbps)"),
    ]),
    ("🕐 Time & System", [
        ("clock_hour",      "Clock — Current Hour (0–23)"),
        ("clock_minute",    "Clock — Current Minute (0–59)"),
        ("uptime_hours",    "System Uptime (hours)"),
        ("ram_used_gb",     "RAM Used (GB)"),
    ]),
    ("🚨 Alert", [
        ("alert",           "Alert Mode — flashes when temp threshold exceeded"),
    ]),
]

def read_config():
    cfg = {"mode": "cpu_temp", "alert_enabled": "0", "alert_temp": "80", "alert_value": "99"}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return cfg

def write_config(cfg_dict):
    lines = [f'{k}="{v}"' for k, v in cfg_dict.items()]
    content = "\n".join(lines) + "\n"
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        if not IS_WINDOWS:
            try:
                subprocess.run(["sudo", "bash", "-c", f'echo "{content}" > {CONFIG_PATH}'], check=True)
                return True
            except Exception:
                pass
        return False

def get_running_pid():
    if os.path.exists(PID_PATH):
        try:
            with open(PID_PATH, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                return pid
        except Exception:
            pass
    # On Linux, check systemd if PID file absent
    if not IS_WINDOWS:
        try:
            res = subprocess.run(["systemctl", "is-active", "cooler-display.service"],
                                 capture_output=True, text=True, timeout=2)
            if res.stdout.strip() == "active":
                return -1  # Running via systemd
        except Exception:
            pass
    return None

def start_daemon():
    pid = get_running_pid()
    if pid is not None:
        return True
    if IS_WINDOWS:
        py_bin = "pythonw" if subprocess.run(["where", "pythonw"], capture_output=True).returncode == 0 else "python"
        subprocess.Popen([py_bin, DAEMON_SCRIPT], creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
        return True
    else:
        subprocess.run(["sudo", "systemctl", "start", "cooler-display.service"])
        return True

def stop_daemon():
    if IS_WINDOWS:
        pid = get_running_pid()
        if pid and pid > 0:
            try:
                p = psutil.Process(pid)
                p.terminate()
            except Exception:
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        if os.path.exists(PID_PATH):
            try:
                os.remove(PID_PATH)
            except Exception:
                pass
        return True
    else:
        subprocess.run(["sudo", "systemctl", "stop", "cooler-display.service"])
        return True

def restart_daemon():
    stop_daemon()
    time.sleep(1)
    start_daemon()


class CoolerDisplayWinApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cooler Display Manager")
        self.root.geometry("520x720")
        self.root.minsize(460, 600)

        self.cfg = read_config()
        self.selected_mode = tk.StringVar(value=self.cfg.get("mode", "cpu_temp"))

        self._setup_style()
        self._build_ui()
        self._refresh_loop()

    def _setup_style(self):
        style = ttk.Style()
        themes = style.theme_names()
        if "vista" in themes:
            style.theme_use("vista")
        elif "clam" in themes:
            style.theme_use("clam")

    def _build_ui(self):
        # Main container with canvas for scrolling
        canvas = tk.Canvas(self.root, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, padding="16")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=480)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Header ──
        header_frame = ttk.Frame(scroll_frame)
        header_frame.pack(fill="x", pady=(0, 12))

        title_lbl = ttk.Label(header_frame, text="🧊 Cooler Display Manager", font=("Segoe UI" if IS_WINDOWS else "Helvetica", 14, "bold"))
        title_lbl.pack(anchor="w")

        sub_lbl = ttk.Label(header_frame, text="Universal Driver for USB Digital Cooler Displays (Windows & Linux)", foreground="gray")
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # ── Service Control Card ──
        svc_frame = ttk.LabelFrame(scroll_frame, text=" Service Status ", padding="10")
        svc_frame.pack(fill="x", pady=6)

        stat_row = ttk.Frame(svc_frame)
        stat_row.pack(fill="x", pady=2)

        self.status_dot = ttk.Label(stat_row, text="●", foreground="gray", font=("Arial", 12))
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_text = ttk.Label(stat_row, text="Checking...", font=("Segoe UI", 10, "bold"))
        self.status_text.pack(side="left")

        btn_row = ttk.Frame(svc_frame)
        btn_row.pack(fill="x", pady=(8, 2))

        self.btn_start = ttk.Button(btn_row, text="▶ Start", command=self._on_start)
        self.btn_start.pack(side="left", padx=2)

        self.btn_stop = ttk.Button(btn_row, text="⏹ Stop", command=self._on_stop)
        self.btn_stop.pack(side="left", padx=2)

        self.btn_restart = ttk.Button(btn_row, text="↺ Restart", command=self._on_restart)
        self.btn_restart.pack(side="left", padx=2)

        # ── Live Telemetry Card ──
        telem_frame = ttk.LabelFrame(scroll_frame, text=" Live Telemetry ", padding="10")
        telem_frame.pack(fill="x", pady=6)

        self.telemetry_labels = {}
        metrics = [
            ("cpu_temp", "🌡️ CPU Temperature", "—"),
            ("gpu_temp", "🎮 GPU Temperature", "—"),
            ("cpu_load", "📊 CPU Load",        "—"),
            ("gpu_load", "🖥️ GPU Load",        "—"),
            ("ram",      "🧠 RAM Usage",       "—"),
            ("disk",     "🗄️ Disk Usage",      "—"),
            ("gpu_pwr",  "⚡ GPU Power",       "—"),
            ("net_dl",   "⬇️ Download Speed",  "—"),
            ("net_ul",   "⬆️ Upload Speed",    "—"),
            ("cpu_freq", "🔥 CPU Frequency",   "—"),
        ]

        for i, (key, title, default) in enumerate(metrics):
            row = ttk.Frame(telem_frame)
            row.pack(fill="x", pady=2)
            lbl = ttk.Label(row, text=title, foreground="gray")
            lbl.pack(side="left")
            val = ttk.Label(row, text=default, font=("Segoe UI", 9, "bold"))
            val.pack(side="right")
            self.telemetry_labels[key] = val

        # ── Display Mode Selector ──
        mode_frame = ttk.LabelFrame(scroll_frame, text=" Display Mode Selection ", padding="10")
        mode_frame.pack(fill="x", pady=6)

        for group_title, modes in MODE_GROUPS:
            grp_lbl = ttk.Label(mode_frame, text=group_title, font=("Segoe UI", 9, "bold"), foreground="#0066cc" if IS_WINDOWS else "blue")
            grp_lbl.pack(anchor="w", pady=(6, 2))
            for mode_id, mode_label in modes:
                rb = ttk.Radiobutton(mode_frame, text=mode_label, value=mode_id, variable=self.selected_mode)
                rb.pack(anchor="w", padx=12, pady=1)

        apply_btn = ttk.Button(mode_frame, text="✅ Apply Selected Mode", command=self._on_apply_mode)
        apply_btn.pack(fill="x", pady=(12, 4))

        # ── Alert Settings ──
        alert_frame = ttk.LabelFrame(scroll_frame, text=" High Temperature Alert ", padding="10")
        alert_frame.pack(fill="x", pady=6)

        arow1 = ttk.Frame(alert_frame)
        arow1.pack(fill="x", pady=2)
        ttk.Label(arow1, text="Temperature Threshold (°C):").pack(side="left")
        self.spin_alert_temp = ttk.Spinbox(arow1, from_=50, to=105, width=6)
        self.spin_alert_temp.set(int(self.cfg.get("alert_temp", "80")))
        self.spin_alert_temp.pack(side="right")

        arow2 = ttk.Frame(alert_frame)
        arow2.pack(fill="x", pady=2)
        ttk.Label(arow2, text="Flashing Alert Code (e.g. 99):").pack(side="left")
        self.spin_alert_val = ttk.Spinbox(arow2, from_=0, to=99, width=6)
        self.spin_alert_val.set(int(self.cfg.get("alert_value", "99")))
        self.spin_alert_val.pack(side="right")

        ttk.Label(alert_frame, text="Note: Select 'Alert Mode' in Display Mode above to activate.", foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

    def _on_start(self):
        threading.Thread(target=start_daemon, daemon=True).start()

    def _on_stop(self):
        threading.Thread(target=stop_daemon, daemon=True).start()

    def _on_restart(self):
        threading.Thread(target=restart_daemon, daemon=True).start()

    def _on_apply_mode(self):
        self.cfg["mode"] = self.selected_mode.get()
        self.cfg["alert_temp"] = str(int(self.spin_alert_temp.get()))
        self.cfg["alert_value"] = str(int(self.spin_alert_val.get()))
        if write_config(self.cfg):
            messagebox.showinfo("Success", f"Mode set to: {self.selected_mode.get()}\nDisplay updated!")
        else:
            messagebox.showerror("Error", "Could not save configuration.")

    def _refresh_loop(self):
        pid = get_running_pid()
        if pid is not None:
            self.status_dot.configure(foreground="#2ecc71")
            self.status_text.configure(text=f"Running (PID {pid if pid > 0 else 'Service'})")
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
        else:
            self.status_dot.configure(foreground="#e74c3c")
            self.status_text.configure(text="Stopped")
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")

        # Telemetry
        cpu_load = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        root_d = (os.environ.get("SystemDrive", "C:") + "\\") if IS_WINDOWS else "/"
        try:
            disk = psutil.disk_usage(root_d)
        except Exception:
            disk = psutil.disk_usage(".")

        self.telemetry_labels["cpu_load"].configure(text=f"{cpu_load:.0f} %")
        self.telemetry_labels["ram"].configure(text=f"{mem.percent:.0f} % ({mem.used/1024**3:.1f}/{mem.total/1024**3:.0f} GB)")
        self.telemetry_labels["disk"].configure(text=f"{disk.percent:.0f} %")

        freq = psutil.cpu_freq()
        if freq:
            self.telemetry_labels["cpu_freq"].configure(text=f"{freq.current:.0f} MHz")

        self.root.after(1200, self._refresh_loop)


def main():
    root = tk.Tk()
    app = CoolerDisplayWinApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
