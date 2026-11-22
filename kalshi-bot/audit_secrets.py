#!/usr/bin/env python3
"""Scan files (and optionally git history) for key material.  python audit_secrets.py [paths] [--git]

Flags: PEM private-key blocks; the API key id and any line of the PEM file named by the
environment (KALSHI_API_KEY_ID / KALSHI_PRIVATE_KEY_PATH); extra literals via --literal.
Prints file:line and the KIND of match, never the secret itself. Exit 1 if anything is found.
"""
import argparse
import os
import re
import subprocess
import sys

PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


def env_secrets():
    out = {}
    kid = os.getenv("KALSHI_API_KEY_ID")
    if kid and len(kid) >= 8:
        out["api-key-id"] = kid
    path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    if path and os.path.exists(path):
        for i, line in enumerate(open(path).read().splitlines()):
            line = line.strip()
            if len(line) >= 30 and not line.startswith("-----"):
                out[f"pem-line-{i}"] = line
    return out


def scan_text(text, where, secrets):
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if PEM.search(line):
            hits.append((where, n, "PEM private key block"))
        for kind, s in secrets.items():
            if s in line:
                hits.append((where, n, kind))
    return hits


def scan_paths(paths, secrets):
    hits = []
    for root in paths:
        files = [root] if os.path.isfile(root) else [os.path.join(d, f) for d, ds, fs in os.walk(root)
                                                    if not (set(d.split(os.sep)) & SKIP_DIRS) for f in fs]
        for f in files:
            try:
                with open(f, "r", errors="ignore") as fh:
                    hits += scan_text(fh.read(), f, secrets)
            except OSError:
                pass
    return hits


def scan_git(repo, secrets):
    try:
        log = subprocess.run(["git", "-C", repo, "log", "-p", "--all"], capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return [("git", 0, "could not read history")]
    return scan_text(log, "git-history", secrets)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--git", action="store_true")
    ap.add_argument("--literal", action="append", default=[])
    a = ap.parse_args(argv)
    secrets = env_secrets()
    secrets.update({f"literal-{i}": s for i, s in enumerate(a.literal)})
    hits = scan_paths(a.paths, secrets) + (scan_git(a.paths[0], secrets) if a.git else [])
    for w, n, kind in hits:
        print(f"FOUND {kind}: {w}:{n}")
    print(f"scanned {len(a.paths)} path(s){' + git history' if a.git else ''} for {len(secrets)} env secret(s) + PEM blocks: "
          f"{'NOTHING FOUND' if not hits else str(len(hits)) + ' HIT(S)'}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
