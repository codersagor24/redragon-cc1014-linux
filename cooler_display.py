#!/usr/bin/env python3
"""
Redragon CC-1014 / USB HID Cooler Display Daemon
Reads CPU & GPU telemetry and updates the digital display in real time.
USB HID VID: 0x5131, PID: 0x2007
"""

import sys
import time
import signal
import logging
import subprocess
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


def read_config():
    """Read DISPLAY_MODE from /etc/cooler-display.conf."""
    mode = "cpu_temp"
    try:
        with open(CONFIG_PATH) as f:
            for line in f:
                if line.startswith("DISPLAY_MODE="):
                    mode = line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning("Could not read config: %s", e)
    return mode


def get_cpu_temperature():
    """Read CPU package temperature from hardware sensors."""
    try:
        temps = psutil.sensors_temperatures()
        # AMD Ryzen
        if "k10temp" in temps:
            for entry in temps["k10temp"]:
                if entry.label == "Tctl" and entry.current is not None:
                    return float(entry.current)
            for entry in temps["k10temp"]:
                if entry.current is not None:
                    return float(entry.current)
        # Intel
        if "coretemp" in temps:
            for entry in temps["coretemp"]:
                if "Package" in entry.label and entry.current is not None:
                    return float(entry.current)
            for entry in temps["coretemp"]:
                if entry.current is not None:
                    return float(entry.current)
        # Generic fallback
        for name, entries in temps.items():
            for entry in entries:
                if entry.current is not None and entry.current > 0:
                    return float(entry.current)
    except Exception as e:
        logger.debug("psutil sensors error: %s", e)

    # sysfs hwmon fallback
    try:
        import glob
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


def get_gpu_temperature():
    """Read NVIDIA GPU temperature via nvidia-smi."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=0.5
        )
        return int(out.decode().strip().split("\n")[0])
    except Exception:
        return 0


def build_packet(cpu_temp, cpu_load=0, cpu_freq=0, gpu_temp=0, gpu_load=0):
    """
    Build the 65-byte HID output report for the display controller.
    Byte 0: Report ID (0x00)
    Byte 1: Header (0x40)
    Byte 2: CPU Temperature °C
    Byte 3: CPU Load %
    Byte 4-5: CPU Frequency MHz (16-bit big-endian)
    Byte 10: GPU Temperature °C
    Byte 11: GPU Load %
    """
    pkt = [0] * 65
    pkt[0] = 0x00
    pkt[1] = 0x40
    pkt[2] = max(0, min(255, int(round(cpu_temp))))
    pkt[3] = max(0, min(100, int(round(cpu_load))))
    freq_int = max(0, min(65535, int(cpu_freq)))
    pkt[4] = (freq_int >> 8) & 0xFF
    pkt[5] = freq_int & 0xFF
    if gpu_temp > 0:
        pkt[10] = max(0, min(255, int(gpu_temp)))
    if gpu_load > 0:
        pkt[11] = max(0, min(100, int(gpu_load)))
    return pkt


def main():
    logger.info("Cooler Display Daemon started (USB %04X:%04X)", VENDOR_ID, PRODUCT_ID)
    dev = None
    last_gpu_check = 0
    cached_gpu_temp = 0
    config_mtime = 0
    display_mode = read_config()
    alternating_toggle_time = 0

    while running:
        try:
            # Reload config if file changed
            try:
                import os
                mtime = os.path.getmtime(CONFIG_PATH)
                if mtime != config_mtime:
                    display_mode = read_config()
                    config_mtime = mtime
                    logger.info("Config reloaded: display_mode=%s", display_mode)
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

            cpu_temp = get_cpu_temperature()
            if cpu_temp is None:
                logger.warning("Cannot read CPU temperature, retrying...")
                time.sleep(1)
                continue

            cpu_load     = psutil.cpu_percent(interval=None)
            cpu_freq_inf = psutil.cpu_freq()
            cpu_freq     = cpu_freq_inf.current if cpu_freq_inf else 0

            # GPU: poll every 5 seconds
            now = time.time()
            if now - last_gpu_check >= 5.0:
                cached_gpu_temp = get_gpu_temperature()
                last_gpu_check = now

            # Determine what temperature to display on the cooler
            if display_mode == "gpu_temp":
                display_temp = cached_gpu_temp if cached_gpu_temp else cpu_temp
            elif display_mode == "cpu_load":
                display_temp = cpu_load
            elif display_mode == "hottest":
                display_temp = max(cpu_temp, cached_gpu_temp)
            elif display_mode == "alternating":
                show_cpu = (int(now / 5) % 2 == 0)
                display_temp = cpu_temp if show_cpu else (cached_gpu_temp or cpu_temp)
            else:  # cpu_temp (default)
                display_temp = cpu_temp

            packet = build_packet(
                cpu_temp=display_temp,
                cpu_load=cpu_load,
                cpu_freq=cpu_freq,
                gpu_temp=cached_gpu_temp,
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

            logger.debug("Sent: mode=%s display=%d°C CPU=%.1f°C load=%d%% freq=%dMHz GPU=%d°C",
                         display_mode, packet[2], cpu_temp, int(cpu_load), int(cpu_freq), cached_gpu_temp)

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
