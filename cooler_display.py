#!/usr/bin/env python3
"""
Redragon CC-1014 CPU Cooler Digital Temperature Display Daemon
USB HID VID: 0x5131, PID: 0x2007

Reversed from original Redragon PcInfoMonitorPro.exe (V1.0.0.04):
HID Output Report: 65 bytes
  [0]: 0x00 (Report ID)
  [1]: 0x40 (Header / Payload size 64)
  [2]: CPU Temperature in °C (integer)
  [3]: CPU Usage / Load % (integer)
  [4..5]: CPU Frequency (MHz, 16-bit BE)
  [6..7]: CPU Fan RPM (16-bit BE)
  [8..9]: CPU Power (16-bit BE)
  [10]: GPU Temperature in °C
  [11]: GPU Usage / Load %
  [12..64]: Remaining metrics / 0x00 padding
"""

import sys
import time
import signal
import logging
import subprocess
import psutil
import hid

VENDOR_ID = 0x5131
PRODUCT_ID = 0x2007
UPDATE_INTERVAL = 1.0  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("cooler_display")

running = True

def signal_handler(signum, frame):
    global running
    logger.info("Shutdown signal received (%s), exiting...", signum)
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def get_cpu_temperature():
    """Read CPU package/control temperature."""
    try:
        temps = psutil.sensors_temperatures()
        # 1. AMD Ryzen k10temp (Tctl preferred, then Tccd1)
        if "k10temp" in temps:
            for entry in temps["k10temp"]:
                if entry.label == "Tctl" and entry.current is not None:
                    return float(entry.current)
            for entry in temps["k10temp"]:
                if entry.current is not None:
                    return float(entry.current)

        # 2. Intel coretemp (Package id 0 preferred, then Core 0)
        if "coretemp" in temps:
            for entry in temps["coretemp"]:
                if "Package" in entry.label and entry.current is not None:
                    return float(entry.current)
            for entry in temps["coretemp"]:
                if entry.current is not None:
                    return float(entry.current)

        # 3. Any sensor key containing cpu, k10, core, zen
        for name, entries in temps.items():
            if any(k in name.lower() for k in ["cpu", "k10", "core", "zen"]):
                for entry in entries:
                    if entry.current is not None:
                        return float(entry.current)

        # 4. Fallback to any sensor temperature
        for name, entries in temps.items():
            for entry in entries:
                if entry.current is not None and entry.current > 0:
                    return float(entry.current)
    except Exception as e:
        logger.debug("psutil sensors error: %s", e)

    # 5. Direct hwmon sysfs fallback
    try:
        import glob
        for name_file in glob.glob("/sys/class/hwmon/hwmon*/name"):
            with open(name_file, "r") as f:
                name = f.read().strip()
            if name in ("k10temp", "coretemp"):
                dir_path = name_file.rsplit("/", 1)[0]
                for input_file in glob.glob(f"{dir_path}/temp*_input"):
                    with open(input_file, "r") as f:
                        val = float(f.read().strip()) / 1000.0
                        if val > 0:
                            return val
    except Exception as e:
        logger.debug("sysfs hwmon error: %s", e)

    return None

def get_gpu_temperature():
    """Read NVIDIA GPU temperature via nvidia-smi if available."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL,
            timeout=0.5
        )
        return int(out.decode().strip().split("\n")[0])
    except Exception:
        return 0

def build_packet(cpu_temp, cpu_load=0, cpu_freq=0, gpu_temp=0, gpu_load=0):
    """
    Construct the 65-byte HID output report matching PcInfoMonitorPro.exe:
    Byte 0: Report ID (0x00)
    Byte 1: Header/size (0x40 = 64)
    Byte 2: CPU Temperature (°C)
    Byte 3: CPU Load (%)
    Byte 4-5: CPU Frequency (MHz, 16-bit BE)
    Byte 10: GPU Temperature (°C)
    Byte 11: GPU Load (%)
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
    logger.info("Starting Redragon CC-1014 Cooler Display Daemon (VID: 0x%04X, PID: 0x%04X)", VENDOR_ID, PRODUCT_ID)
    dev = None

    last_gpu_check = 0
    cached_gpu_temp = 0

    while running:
        try:
            if dev is None:
                try:
                    dev = hid.device()
                    dev.open(VENDOR_ID, PRODUCT_ID)
                    dev.set_nonblocking(1)
                    logger.info("Connected to Redragon CC-1014 HID device (0x%04x:0x%04x)", VENDOR_ID, PRODUCT_ID)
                except Exception as e:
                    logger.warning("Device 0x%04x:0x%04x not found or cannot open (%s). Retrying in 2s...", VENDOR_ID, PRODUCT_ID, e)
                    dev = None
                    time.sleep(2)
                    continue

            cpu_temp = get_cpu_temperature()
            if cpu_temp is None:
                logger.warning("Could not read CPU temperature, retrying...")
                time.sleep(1)
                continue

            cpu_load = psutil.cpu_percent(interval=None)
            cpu_freq_info = psutil.cpu_freq()
            cpu_freq = cpu_freq_info.current if cpu_freq_info else 0

            # Poll GPU temp periodically
            now = time.time()
            if now - last_gpu_check >= 5.0:
                cached_gpu_temp = get_gpu_temperature()
                last_gpu_check = now

            packet = build_packet(
                cpu_temp=cpu_temp,
                cpu_load=cpu_load,
                cpu_freq=cpu_freq,
                gpu_temp=cached_gpu_temp,
                gpu_load=0
            )

            written = dev.write(packet)
            if written < 0:
                logger.error("HID write returned error %d, reconnecting...", written)
                try:
                    dev.close()
                except Exception:
                    pass
                dev = None
                time.sleep(1)
                continue

            logger.info("Sent update: CPU Temp=%d°C (raw=%.1f°C), Load=%d%%, Freq=%dMHz, GPU Temp=%d°C",
                        packet[2], cpu_temp, packet[3], cpu_freq, cached_gpu_temp)

        except Exception as e:
            logger.error("Error during daemon loop: %s", e)
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
    logger.info("Cooler Display Daemon stopped cleanly.")

if __name__ == "__main__":
    main()
