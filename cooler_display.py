#!/usr/bin/env python3
"""
Redragon CC-1014 / USB HID Cooler Display Daemon
Reads system telemetry and updates the digital display in real time.
USB HID VID: 0x5131, PID: 0x2007
"""

import sys
import time
import signal
import logging
import subprocess
import os
import glob
import psutil
import hid

VENDOR_ID       = 0x5131
PRODUCT_ID      = 0x2007
UPDATE_INTERVAL = 1.0        # seconds
CONFIG_PATH     = "/etc/cooler-display.conf"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("cooler_display")

running = True

def signal_handler(signum, frame):
    global running
    logger.info("Shutdown signal received (%s), stopping...", signum)
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


# ─── Config ───────────────────────────────────────────────────────────────────

def read_config():
    """Read settings from /etc/cooler-display.conf."""
    cfg = {
        "mode": "cpu_temp",
        "alert_enabled": "0",
        "alert_temp": "80",
        "alert_value": "99",
    }
    try:
        with open(CONFIG_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    cfg[key.strip()] = val.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning("Could not read config: %s", e)
    return cfg


# ─── CPU ──────────────────────────────────────────────────────────────────────

def get_cpu_temperature():
    """Read CPU package temperature from hardware sensors."""
    try:
        temps = psutil.sensors_temperatures()
        if "k10temp" in temps:
            for entry in temps["k10temp"]:
                if entry.label == "Tctl" and entry.current is not None:
                    return float(entry.current)
            for entry in temps["k10temp"]:
                if entry.current is not None:
                    return float(entry.current)
        if "coretemp" in temps:
            for entry in temps["coretemp"]:
                if "Package" in entry.label and entry.current is not None:
                    return float(entry.current)
            for entry in temps["coretemp"]:
                if entry.current is not None:
                    return float(entry.current)
        for name, entries in temps.items():
            for entry in entries:
                if entry.current is not None and entry.current > 0:
                    return float(entry.current)
    except Exception as e:
        logger.debug("psutil sensors error: %s", e)

    # sysfs hwmon fallback
    try:
        for name_file in glob.glob("/sys/class/hwmon/hwmon*/name"):
            with open(name_file) as f:
                name = f.read().strip()
            if name in ("k10temp", "coretemp"):
                dir_path = name_file.rsplit("/", 1)[0]
                for inp in glob.glob(f"{dir_path}/temp*_input"):
                    with open(inp) as f:
                        val = float(f.read().strip()) / 1000.0
                        if val > 0:
                            return val
    except Exception as e:
        logger.debug("sysfs hwmon error: %s", e)
    return None


# ─── GPU ──────────────────────────────────────────────────────────────────────

def get_gpu_metrics():
    """Read NVIDIA GPU metrics via nvidia-smi.
    Returns dict: temp, load, power_w, fan_pct, clock_mhz
    """
    result = {"temp": 0, "load": 0, "power_w": 0, "fan_pct": 0, "clock_mhz": 0}
    try:
        out = subprocess.check_output(
            ["nvidia-smi",
             "--query-gpu=temperature.gpu,utilization.gpu,power.draw,fan.speed,clocks.current.graphics",
             "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=1
        ).decode().strip().split("\n")[0].split(",")
        result["temp"]      = int(out[0].strip())
        result["load"]      = int(out[1].strip())
        result["power_w"]   = int(float(out[2].strip()))
        result["fan_pct"]   = int(out[3].strip())
        result["clock_mhz"] = int(out[4].strip())
    except Exception:
        pass
    return result


# ─── NVMe / Disk ──────────────────────────────────────────────────────────────

def get_nvme_temperature():
    """Read NVMe SSD temperature."""
    try:
        temps = psutil.sensors_temperatures()
        if "nvme" in temps:
            for entry in temps["nvme"]:
                if entry.current and entry.current > 0:
                    return float(entry.current)
    except Exception:
        pass
    return None


_last_disk_io = None
_last_disk_time = 0

def get_disk_io_mbps():
    """Return disk read+write speed in MB/s."""
    global _last_disk_io, _last_disk_time
    try:
        io = psutil.disk_io_counters()
        now = time.time()
        if _last_disk_io is not None and now > _last_disk_time:
            dt = now - _last_disk_time
            read_mb  = (io.read_bytes  - _last_disk_io.read_bytes)  / (1024**2 * dt)
            write_mb = (io.write_bytes - _last_disk_io.write_bytes) / (1024**2 * dt)
            _last_disk_io   = io
            _last_disk_time = now
            return read_mb + write_mb
        _last_disk_io   = io
        _last_disk_time = now
    except Exception:
        pass
    return 0.0


# ─── Network ──────────────────────────────────────────────────────────────────

_last_net_io = None
_last_net_time = 0

def get_network_speed():
    """Return (download_kbps, upload_kbps)."""
    global _last_net_io, _last_net_time
    try:
        io  = psutil.net_io_counters()
        now = time.time()
        if _last_net_io is not None and now > _last_net_time:
            dt   = now - _last_net_time
            dl   = (io.bytes_recv - _last_net_io.bytes_recv) / (1024 * dt)
            ul   = (io.bytes_sent - _last_net_io.bytes_sent) / (1024 * dt)
            _last_net_io   = io
            _last_net_time = now
            return max(0, dl), max(0, ul)
        _last_net_io   = io
        _last_net_time = now
    except Exception:
        pass
    return 0.0, 0.0


# ─── Packet builder ───────────────────────────────────────────────────────────

def build_packet(cpu_temp, cpu_load=0, cpu_freq=0, gpu_temp=0, gpu_load=0,
                 gpu_power=0, gpu_clock=0, mem_pct=0, mem_used_mb=0,
                 disk_pct=0):
    """
    Build the 65-byte HID output report.
    Byte  0: Report ID (0x00)
    Byte  1: Header (0x40)
    Byte  2: CPU Temperature °C          ← main display value
    Byte  3: CPU Load %
    Byte 4-5: CPU Frequency MHz (16-bit BE)
    Byte 10: GPU Temperature °C
    Byte 11: GPU Load %
    Byte 12-13: GPU Clock MHz (16-bit BE)
    Byte 16-17: GPU Power W (16-bit BE)
    Byte 18: RAM %
    Byte 19-20: RAM Used MB (16-bit BE)
    Byte 22-23: Disk % (16-bit BE)
    """
    pkt = [0] * 65
    pkt[0] = 0x00
    pkt[1] = 0x40
    pkt[2] = max(0, min(255, int(round(cpu_temp))))
    pkt[3] = max(0, min(100, int(round(cpu_load))))

    freq_int = max(0, min(65535, int(cpu_freq)))
    pkt[4] = (freq_int >> 8) & 0xFF
    pkt[5] = freq_int & 0xFF

    pkt[10] = max(0, min(255, int(gpu_temp)))
    pkt[11] = max(0, min(100, int(gpu_load)))

    gpu_clk = max(0, min(65535, int(gpu_clock)))
    pkt[12] = (gpu_clk >> 8) & 0xFF
    pkt[13] = gpu_clk & 0xFF

    gpu_pwr = max(0, min(65535, int(gpu_power)))
    pkt[16] = (gpu_pwr >> 8) & 0xFF
    pkt[17] = gpu_pwr & 0xFF

    pkt[18] = max(0, min(100, int(mem_pct)))

    mem_mb = max(0, min(65535, int(mem_used_mb)))
    pkt[19] = (mem_mb >> 8) & 0xFF
    pkt[20] = mem_mb & 0xFF

    dsk = max(0, min(65535, int(disk_pct)))
    pkt[22] = (dsk >> 8) & 0xFF
    pkt[23] = dsk & 0xFF

    return pkt


# ─── Display value selector ───────────────────────────────────────────────────

def get_display_value(mode, metrics, cfg):
    """Return the integer value to place in byte 2 (main display)."""
    cpu_temp  = metrics["cpu_temp"]
    gpu       = metrics["gpu"]
    mem       = metrics["mem"]
    disk_pct  = metrics["disk_pct"]
    nvme_temp = metrics["nvme_temp"]
    dl_kbps   = metrics["dl_kbps"]
    ul_kbps   = metrics["ul_kbps"]
    cpu_load  = metrics["cpu_load"]
    cpu_freq  = metrics["cpu_freq"]
    disk_mbps = metrics["disk_mbps"]

    now = time.localtime()

    if mode == "gpu_temp":
        return gpu["temp"] if gpu["temp"] else cpu_temp
    elif mode == "cpu_load":
        return int(round(cpu_load))
    elif mode == "hottest":
        return max(cpu_temp, gpu["temp"])
    elif mode == "alternating":
        return cpu_temp if (int(time.time() / 5) % 2 == 0) else (gpu["temp"] or cpu_temp)

    elif mode == "ram_pct":
        return int(round(mem.percent))
    elif mode == "ram_used_gb":
        return int(mem.used / 1024**3)
    elif mode == "disk_pct":
        return int(round(disk_pct))
    elif mode == "nvme_temp":
        return int(round(nvme_temp)) if nvme_temp else int(round(cpu_temp))
    elif mode == "cpu_freq_ghz10":
        # e.g. 3.4GHz → shows 34
        return max(0, min(99, int(cpu_freq / 100)))

    elif mode == "gpu_load":
        return gpu["load"]
    elif mode == "gpu_power":
        return gpu["power_w"]
    elif mode == "gpu_fan":
        return gpu["fan_pct"]

    elif mode == "net_dl_kbps":
        return max(0, min(999, int(dl_kbps)))
    elif mode == "net_ul_kbps":
        return max(0, min(999, int(ul_kbps)))
    elif mode == "net_dl_mbps":
        return max(0, min(999, int(dl_kbps / 1024 * 8)))  # KB/s → Mbps
    elif mode == "disk_mbps":
        return max(0, min(999, int(disk_mbps)))

    elif mode == "clock_hour":
        return now.tm_hour
    elif mode == "clock_minute":
        return now.tm_min
    elif mode == "uptime_hours":
        return int((time.time() - psutil.boot_time()) / 3600)

    elif mode == "alert":
        # Show CPU temp normally; flash alert_value when temp ≥ threshold
        threshold = int(cfg.get("alert_temp", "80"))
        alert_val = int(cfg.get("alert_value", "99"))
        if cpu_temp >= threshold:
            # Alternate between cpu_temp and alert_value every 0.5s
            return alert_val if (int(time.time() * 2) % 2 == 0) else int(round(cpu_temp))
        return int(round(cpu_temp))

    else:  # cpu_temp (default)
        return int(round(cpu_temp))


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    logger.info("Cooler Display Daemon started (USB %04X:%04X)", VENDOR_ID, PRODUCT_ID)
    dev = None
    last_gpu_check  = 0
    cached_gpu      = {"temp": 0, "load": 0, "power_w": 0, "fan_pct": 0, "clock_mhz": 0}
    config_mtime    = 0
    cfg             = read_config()
    display_mode    = cfg.get("mode", "cpu_temp")

    while running:
        try:
            # Reload config on file change
            try:
                mtime = os.path.getmtime(CONFIG_PATH)
                if mtime != config_mtime:
                    cfg          = read_config()
                    display_mode = cfg.get("mode", "cpu_temp")
                    config_mtime = mtime
                    logger.info("Config reloaded: mode=%s", display_mode)
            except FileNotFoundError:
                pass

            if dev is None:
                try:
                    dev = hid.device()
                    dev.open(VENDOR_ID, PRODUCT_ID)
                    dev.set_nonblocking(1)
                    logger.info("Connected to HID device %04X:%04X", VENDOR_ID, PRODUCT_ID)
                except Exception as e:
                    logger.warning("Device not found (%s). Retrying in 2s...", e)
                    dev = None
                    time.sleep(2)
                    continue

            # ── Gather all metrics ──
            cpu_temp = get_cpu_temperature()
            if cpu_temp is None:
                logger.warning("Cannot read CPU temperature, retrying...")
                time.sleep(1)
                continue

            cpu_load     = psutil.cpu_percent(interval=None)
            cpu_freq_inf = psutil.cpu_freq()
            cpu_freq     = cpu_freq_inf.current if cpu_freq_inf else 0
            mem          = psutil.virtual_memory()
            disk         = psutil.disk_usage("/")
            nvme_temp    = get_nvme_temperature()
            dl_kbps, ul_kbps = get_network_speed()
            disk_mbps    = get_disk_io_mbps()

            # GPU: poll every 5s
            now = time.time()
            if now - last_gpu_check >= 5.0:
                cached_gpu     = get_gpu_metrics()
                last_gpu_check = now

            metrics = {
                "cpu_temp":  cpu_temp,
                "cpu_load":  cpu_load,
                "cpu_freq":  cpu_freq,
                "gpu":       cached_gpu,
                "mem":       mem,
                "disk_pct":  disk.percent,
                "nvme_temp": nvme_temp,
                "dl_kbps":   dl_kbps,
                "ul_kbps":   ul_kbps,
                "disk_mbps": disk_mbps,
            }

            display_val = get_display_value(display_mode, metrics, cfg)

            packet = build_packet(
                cpu_temp   = display_val,
                cpu_load   = int(cpu_load),
                cpu_freq   = cpu_freq,
                gpu_temp   = cached_gpu["temp"],
                gpu_load   = cached_gpu["load"],
                gpu_power  = cached_gpu["power_w"],
                gpu_clock  = cached_gpu["clock_mhz"],
                mem_pct    = int(mem.percent),
                mem_used_mb= int(mem.used / 1024**2),
                disk_pct   = int(disk.percent),
            )

            written = dev.write(packet)
            if written < 0:
                logger.error("HID write failed (%d), reconnecting...", written)
                try:
                    dev.close()
                except Exception:
                    pass
                dev = None
                time.sleep(1)
                continue

            logger.debug("mode=%-16s display=%3d  cpu=%.1f°C load=%d%% gpu=%d°C ram=%d%% net↓%.0f kb/s",
                         display_mode, display_val, cpu_temp, int(cpu_load),
                         cached_gpu["temp"], int(mem.percent), dl_kbps)

        except Exception as e:
            logger.error("Daemon error: %s", e)
            if dev:
                try:
                    dev.close()
                except Exception:
                    pass
                dev = None
            time.sleep(2)

        time.sleep(UPDATE_INTERVAL)

    if dev:
        try:
            dev.close()
        except Exception:
            pass
    logger.info("Cooler Display Daemon stopped.")


if __name__ == "__main__":
    main()
