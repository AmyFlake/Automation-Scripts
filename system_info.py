#!/usr/bin/env python3
# system_info.py — Linux system information (Python only). No bash.
import os, time, json, socket, platform, subprocess
from datetime import datetime

def sh(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""

def read(p):
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""

def cpu_usage_sample():
    def read_stat():
        with open("/proc/stat","r") as f:
            parts = f.readline().split()
            v = list(map(int, parts[1:11]))
            user,nice,system,idle,iowait,irq,softirq,steal,guest,guest_nice = v
            idle_t = idle + iowait
            nonidle = user + nice + system + irq + softirq + steal
            total = idle_t + nonidle
            return idle_t, total
    idle1,total1 = read_stat(); time.sleep(0.5)
    idle2,total2 = read_stat()
    totald=total2-total1; idled=idle2-idle1
    return round((totald-idled)*100.0/totald,2) if totald>0 else None

def main():
    data = {}
    data["timestamp"] = datetime.utcnow().isoformat() + "Z"
    data["hostname"] = socket.gethostname()
    data["uptime_pretty"] = sh("uptime -p") or None
    data["manufacturer"] = read("/sys/class/dmi/id/chassis_vendor") or None
    data["product_name"] = read("/sys/class/dmi/id/product_name") or None
    data["version"] = read("/sys/class/dmi/id/product_version") or None
    data["serial_number"] = read("/sys/class/dmi/id/product_serial") or None
    virt = sh("systemd-detect-virt") or ""
    data["machine_type"] = f"VM ({virt})" if virt and virt!="none" else "Physical"
    os_name = sh("hostnamectl | awk -F': ' '/Operating System/ {print $2}'") or None
    data["operating_system"] = os_name
    data["kernel"] = platform.release()
    data["architecture"] = platform.machine()
    cpu_name = sh("awk -F': ' '/^model name/ {print $2; exit}' /proc/cpuinfo") or None
    data["processor_name"] = cpu_name
    users = sh("who | awk '{print $1}' | sort -u")
    data["active_users"] = users.splitlines() if users else []
    data["main_ip"] = sh("hostname -I") or None
    # memory/swap
    mem = sh("free -m | awk '/Mem:/ {print $2, $3}'").split()
    if len(mem)==2:
        total, used = map(float, mem); data['memory_used_pct']=round(used*100.0/total,2) if total else None
    swap = sh("free -m | awk '/Swap:/ {print $2, $3}'").split()
    if len(swap)==2:
        total, used = map(float, swap); data['swap_used_pct']=round(used*100.0/total,2) if total else None
    data['cpu_used_pct'] = cpu_usage_sample()
    df = sh("df -Ph | awk 'NR==1 || ($5+0) > 80 {print $0}'")
    data['disk_usage_gt80'] = df.splitlines()

    # pretty
    def line(k,v): print(f"{k:24s}{v}")
    print("-"*31 + " System Information " + "-"*31)
    line("Hostname:", data['hostname'])
    line("Uptime:", data.get('uptime_pretty') or 'N/A')
    line("Manufacturer:", data.get('manufacturer') or 'N/A')
    line("Product Name:", data.get('product_name') or 'N/A')
    line("Version:", data.get('version') or 'N/A')
    line("Serial Number:", data.get('serial_number') or 'N/A')
    line("Machine Type:", data['machine_type'])
    line("Operating System:", data.get('operating_system') or 'N/A')
    line("Kernel:", data['kernel'])
    line("Architecture:", data['architecture'])
    line("Processor Name:", data.get('processor_name') or 'N/A')
    line("Active Users:", ', '.join(data['active_users']) or 'none')
    line("System Main IP:", data.get('main_ip') or 'N/A')
    print("-"*31 + " CPU/Memory Usage " + "-"*31)
    line("Memory Usage:", f"{data.get('memory_used_pct','N/A')}%" )
    line("Swap Usage:", f"{data.get('swap_used_pct','N/A')}%" )
    cpuv=data.get('cpu_used_pct'); line("CPU Usage:", f"{cpuv}%" if cpuv is not None else 'N/A')
    print("-"*29 + " Disk Usage > 80% " + "-"*29)
    for row in data['disk_usage_gt80']: print(row)
    print("\n--JSON--"); import json; print(json.dumps(data, indent=2))

if __name__ == '__main__':
    main()
