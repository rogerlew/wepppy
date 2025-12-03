#!/usr/bin/env python3
"""
Scan .<run_slug> access logs and compile run/user info to JSONL.

This script scans the access log files (.<run_slug>) in /wc1/runs/ directories
and outputs a JSONL file with run and user access information.

Usage:
    python scan_access_logs.py [--wc1-dir /wc1] [--output access_data.jsonl]

Output format (one JSON object per line):
    {"runid": "ab/some-run", "config": "disturbed", "users": [{"email": "user@example.com", "first_access": "2025-01-01T12:00:00"}]}
"""

import os
import sys
import json
import argparse
from glob import glob
from datetime import datetime
from os.path import join as _join
from os.path import exists as _exists
from os.path import basename, dirname
from collections import defaultdict


def parse_log_file(log_path):
    """
    Parse a .<run_slug> log file and extract user accesses.
    
    Returns list of (email, ip, datetime) tuples
    """
    accesses = []
    try:
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        email = parts[0].strip()
                        ip = parts[1].strip()
                        date_str = parts[2].strip()
                        
                        # Parse datetime
                        try:
                            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
                        except ValueError:
                            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        
                        accesses.append((email, ip, dt))
                except Exception as e:
                    print(f"  Warning: Could not parse line in {log_path}: {line[:50]}... ({e})", file=sys.stderr)
    except Exception as e:
        print(f"  Error reading {log_path}: {e}", file=sys.stderr)
    
    return accesses


def scan_run_logs(wc1_dir):
    """
    Scan all run directories for access logs.
    
    Yields dicts with run info and user accesses.
    """
    # Find all .<run_slug> files
    pattern = _join(wc1_dir, 'runs', '*', '.*')
    log_files = glob(pattern)
    
    print(f"Found {len(log_files)} log files to process...", file=sys.stderr)
    
    for log_path in sorted(log_files):
        # Skip vim swap files
        if log_path.endswith('.swp') or log_path.endswith('.swo'):
            continue
            
        log_name = basename(log_path)
        if not log_name.startswith('.'):
            continue
            
        run_slug = log_name[1:]  # Remove leading dot
        parent_dir = dirname(log_path)
        prefix = basename(parent_dir)  # e.g., 'ab', 'ad'
        runid = f"{prefix}/{run_slug}"
        
        # Check if the actual run directory exists
        run_dir = _join(parent_dir, run_slug)
        if not _exists(run_dir):
            continue
        
        # Try to get config from ron.nodb
        config = None
        ron_path = _join(run_dir, 'ron.nodb')
        if _exists(ron_path):
            try:
                # Import here to allow running without full wepppy install
                sys.path.insert(0, '/workdir/wepppy')
                from wepppy.nodb import Ron
                ron = Ron.getInstance(run_dir)
                config = ron.config_stem
            except Exception:
                pass
        
        # Parse the log file
        accesses = parse_log_file(log_path)
        
        # Group by email and find first access (only OAuth users with @)
        email_first_access = {}
        for email, ip, dt in accesses:
            # Skip anonymous users
            if email == '<anonymous>' or not email or '@' not in email:
                continue
            
            email_lower = email.lower()
            if email_lower not in email_first_access or dt < email_first_access[email_lower]:
                email_first_access[email_lower] = dt
        
        # Build user list sorted by first access
        users = [
            {"email": email, "first_access": dt.isoformat()}
            for email, dt in sorted(email_first_access.items(), key=lambda x: x[1])
        ]
        
        # Find earliest access for run creation date
        earliest_access = None
        if accesses:
            earliest_access = min(dt for _, _, dt in accesses).isoformat()
        
        yield {
            "runid": runid,
            "run_dir": run_dir,
            "config": config,
            "earliest_access": earliest_access,
            "users": users
        }


def main():
    parser = argparse.ArgumentParser(
        description='Scan access logs and output run/user info as JSONL'
    )
    parser.add_argument(
        '--wc1-dir',
        default='/wc1',
        help='Path to wc1 directory (default: /wc1)'
    )
    parser.add_argument(
        '--output', '-o',
        default='access_data.jsonl',
        help='Output JSONL file (default: access_data.jsonl)'
    )
    
    args = parser.parse_args()
    
    print(f"Scanning {args.wc1_dir}/runs for access logs...", file=sys.stderr)
    
    run_count = 0
    user_run_count = 0
    unique_users = set()
    
    with open(args.output, 'w') as f:
        for run_data in scan_run_logs(args.wc1_dir):
            f.write(json.dumps(run_data) + '\n')
            run_count += 1
            
            for user in run_data['users']:
                user_run_count += 1
                unique_users.add(user['email'])
    
    print(f"\nWrote {args.output}", file=sys.stderr)
    print(f"  Runs: {run_count}", file=sys.stderr)
    print(f"  Unique OAuth users: {len(unique_users)}", file=sys.stderr)
    print(f"  User-run associations: {user_run_count}", file=sys.stderr)


if __name__ == '__main__':
    main()
