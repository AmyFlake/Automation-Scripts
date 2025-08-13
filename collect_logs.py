#!/usr/bin/env python3
# collect_logs.py — Linux syslog/journal collector (Python). No bash.
# - Uses journalctl when available (text + JSON)
# - Falls back to /var/log/{syslog,messages}
# - Packages results into a timestamped tar.gz
import subprocess, os, tarfile, time, json
from datetime import datetime
from pathlib import Path
import argparse

def sh_to_file(cmd, out_path):
    with open(out_path, 'w', encoding='utf-8') as f:
        subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.DEVNULL, text=True, check=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', help='Start time e.g. "2025-08-12 00:00:00"')
    ap.add_argument('--hours', type=int, help='Collect last N hours')
    ap.add_argument('--out', default='./out', help='Output directory')
    args = ap.parse_args()

    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    bundle = out_dir / f'syslog_local_{ts}'
    bundle.mkdir(parents=True, exist_ok=True)

    # journalctl detection
    has_journal = subprocess.call('command -v journalctl >/dev/null 2>&1', shell=True) == 0

    if has_journal:
        if args.since:
            sh_to_file(f"sudo journalctl -o short-iso -S '{args.since}'", bundle / 'journal_since.log')
            sh_to_file(f"sudo journalctl -o json -S '{args.since}'", bundle / 'journal_since.json')
        elif args.hours:
            sh_to_file(f"sudo journalctl -o short-iso --since '{args.hours} hours ago'", bundle / 'journal_since.log')
            sh_to_file(f"sudo journalctl -o json --since '{args.hours} hours ago'", bundle / 'journal_since.json')
        else:
            sh_to_file("sudo journalctl -o short-iso -b 0", bundle / 'journal_boot.log')
            sh_to_file("sudo journalctl -o json -b 0", bundle / 'journal_boot.json')
    else:
        for f in ['/var/log/syslog','/var/log/messages']:
            if Path(f).exists():
                subprocess.run(f"sudo cp -a '{f}' '{bundle}/'", shell=True)

    # compress
    tar_path = out_dir / f"{bundle.name}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(bundle, arcname=bundle.name)
    print(str(tar_path))

if __name__ == '__main__':
    main()
