#!/usr/bin/env python3
# pull_logs.py — Pull logs from multiple Linux hosts via ssh/scp (Python wrapper around ssh). No bash scripts.
# Requirements: ssh keys set up; journalctl on remotes (preferred) or /var/log/syslog/messages.
import argparse, subprocess, shlex
from pathlib import Path
from datetime import datetime

def run(cmd, **kw):
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kw)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('hosts_file', help='File with one host per line, e.g. admin@host1 or root@10.0.0.5')
    ap.add_argument('--since', help='Start time string')
    ap.add_argument('--hours', type=int, help='Last N hours')
    ap.add_argument('--out', default='./out', help='Output directory')
    args = ap.parse_args()

    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    session_dir = out_dir / f'syslog_multi_{ts}'
    session_dir.mkdir(parents=True, exist_ok=True)

    for line in Path(args.hosts_file).read_text(encoding='utf-8').splitlines():
        target = line.strip()
        if not target or target.startswith('#'): continue
        host_dir = session_dir / ''.join(c if c.isalnum() or c in '._-' else '_' for c in target)
        host_dir.mkdir(parents=True, exist_ok=True)

        # detect journalctl remotely
        ok = run(f"ssh -o BatchMode=yes -o ConnectTimeout=8 {shlex.quote(target)} 'command -v journalctl >/dev/null'" )
        if ok.returncode == 0:
            if args.since:
                run(f"ssh {shlex.quote(target)} " + shlex.quote(f"sudo journalctl -o short-iso -S '{args.since}'") + f" > '{host_dir/'journal_since.log'}'" )
                run(f"ssh {shlex.quote(target)} " + shlex.quote(f"sudo journalctl -o json -S '{args.since}'") + f" > '{host_dir/'journal_since.json'}'" )
            elif args.hours:
                run(f"ssh {shlex.quote(target)} " + shlex.quote(f"sudo journalctl -o short-iso --since '{args.hours} hours ago'") + f" > '{host_dir/'journal_since.log'}'" )
                run(f"ssh {shlex.quote(target)} " + shlex.quote(f"sudo journalctl -o json --since '{args.hours} hours ago'") + f" > '{host_dir/'journal_since.json'}'" )
            else:
                run(f"ssh {shlex.quote(target)} 'sudo journalctl -o short-iso -b 0' > '{host_dir/'journal_boot.log'}'" )
                run(f"ssh {shlex.quote(target)} 'sudo journalctl -o json -b 0' > '{host_dir/'journal_boot.json'}'" )
        else:
            # fallback copy
            run(f"scp -o BatchMode=yes -o ConnectTimeout=8 {shlex.quote(target)}:/var/log/syslog* '{host_dir}/'" )
            run(f"scp -o BatchMode=yes -o ConnectTimeout=8 {shlex.quote(target)}:/var/log/messages* '{host_dir}/'" )

    print(str(session_dir))

if __name__ == '__main__':
    main()
