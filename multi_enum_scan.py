import subprocess
import argparse
import os
import json
from datetime import datetime

results = {
    "target": "",
    "timestamp": datetime.utcnow().isoformat(),
    "nmap": [],
    "nikto": "",
    "gobuster": [],
    "whatweb": "",
    "whois": ""
}

# ----------------- NMAP -----------------
def run_nmap(target):
    print(f"[+] Running nmap on {target}")
    try:
        result = subprocess.run(
            ["nmap", "-sV", "-T4", target],
            capture_output=True, text=True, timeout=60
        )
        results["nmap"] = result.stdout.splitlines()
    except Exception as e:
        results["nmap"] = [f"Error: {e}"]

# ----------------- NIKTO -----------------
def run_nikto(target):
    print(f"[+] Running nikto on {target}")
    try:
        result = subprocess.run(
            ["nikto", "-h", target],
            capture_output=True, text=True, timeout=90
        )
        results["nikto"] = result.stdout
    except Exception as e:
        results["nikto"] = f"Error: {e}"

# ----------------- GOBUSTER -----------------
def run_gobuster(target, wordlist="wordlists/common.txt"):
    print(f"[+] Running gobuster on {target}")
    url = f"http://{target}" if not target.startswith("http") else target
    try:
        result = subprocess.run(
            ["gobuster", "dir", "-u", url, "-w", wordlist, "-q"],
            capture_output=True, text=True, timeout=90
        )
        results["gobuster"] = result.stdout.splitlines()
    except Exception as e:
        results["gobuster"] = [f"Error: {e}"]

# ----------------- WHATWEB -----------------
def run_whatweb(target):
    print(f"[+] Running whatweb on {target}")
    try:
        result = subprocess.run(
            ["whatweb", target],
            capture_output=True, text=True, timeout=30
        )
        results["whatweb"] = result.stdout.strip()
    except Exception as e:
        results["whatweb"] = f"Error: {e}"

# ----------------- WHOIS -----------------
def run_whois(target):
    print(f"[+] Running whois on {target}")
    try:
        result = subprocess.run(
            ["whois", target],
            capture_output=True, text=True, timeout=30
        )
        results["whois"] = result.stdout.strip()
    except Exception as e:
        results["whois"] = f"Error: {e}"

# ----------------- SAVE TO FILE -----------------
def save_results(output_file):
    os.makedirs("output", exist_ok=True)
    path = os.path.join("output", output_file)
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[✓] Results saved to {path}")

# ----------------- MAIN -----------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Tool Recon Scanner")
    parser.add_argument("target", help="Target IP or domain")
    parser.add_argument("--gobuster-wordlist", default="wordlists/common.txt", help="Gobuster wordlist path")
    parser.add_argument("--output", default="scan_results.json", help="Output JSON file")
    args = parser.parse_args()

    target = args.target
    results["target"] = target

    # Run selected tools
    run_nmap(target)
    run_whatweb(target)
    run_nikto(target)
    run_gobuster(target, args.gobuster_wordlist)
    run_whois(target)

    save_results(args.output)
