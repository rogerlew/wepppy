#!/usr/bin/env python3
"""
Import run/user data from JSONL into the WEPPcloud database.

This script reads the JSONL output from scan_access_logs.py and creates
User and Run records, associating users with runs they've accessed.

Usage:
    # Dry run (show what would be done)
    python import_access_data.py access_data.jsonl --dry-run
    
    # Actually import
    python import_access_data.py access_data.jsonl

JSONL input format (one JSON object per line):
    {"runid": "some-run", "config": "disturbed", "users": [{"email": "user@example.com", "first_access": "2025-01-01T12:00:00"}]}
    
Note: runid should be just the slug (e.g., "some-run"), not prefixed (e.g., "ab/some-run").
      The prefix is computed from the first two characters of the slug.
"""

import os
import sys
import json
import argparse
from datetime import datetime
import uuid

# Add wepppy to path
sys.path.insert(0, '/workdir/wepppy')


def load_jsonl(filepath):
    """Load JSONL file and yield parsed objects."""
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def import_data(jsonl_path, dry_run=False, database_url=None):
    """
    Import run/user data from JSONL into the database.
    """
    from flask import Flask
    from wepppy.weppcloud.app import db, User, Run
    
    # Create a minimal Flask app for database access
    app = Flask(__name__)
    
    # Load config
    if database_url is None:
        database_url = os.environ.get(
            'DATABASE_URL', 
            'postgresql://weppcloud:weppcloud@postgres:5432/weppcloud'
        )
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-import')
    
    db.init_app(app)
    
    with app.app_context():
        # First pass: collect all unique emails
        all_emails = set()
        run_data_list = []
        
        print("Loading JSONL data...")
        for run_data in load_jsonl(jsonl_path):
            run_data_list.append(run_data)
            for user in run_data.get('users', []):
                all_emails.add(user['email'].lower())
        
        print(f"Found {len(all_emails)} unique OAuth users")
        print(f"Found {len(run_data_list)} runs")
        
        if dry_run:
            print("\n=== DRY RUN - No changes will be made ===\n")
            
            print("Users to create:")
            for email in sorted(all_emails):
                existing = User.query.filter_by(email=email).first()
                status = "(exists)" if existing else "(new)"
                print(f"  - {email} {status}")
            
            print("\nRuns to create/update:")
            for run_data in run_data_list:
                runid = run_data['runid']
                # Strip prefix if present
                if '/' in runid:
                    runid = runid.split('/', 1)[1]
                config = run_data.get('config')
                users = run_data.get('users', [])
                
                existing = Run.query.filter_by(runid=runid).first()
                status = "(exists)" if existing else "(new)"
                
                print(f"  - {runid} (config={config}) {status}")
                if users:
                    emails = [u['email'] for u in users]
                    print(f"      owners: {', '.join(emails)}")
            
            return
        
        # Create users
        print("\nCreating/updating users...")
        email_to_user = {}
        
        for email in all_emails:
            user = User.query.filter_by(email=email).first()
            
            if user is None:
                user = User(
                    email=email,
                    fs_uniquifier=str(uuid.uuid4()),
                    active=True,
                    confirmed_at=datetime.utcnow()
                )
                db.session.add(user)
                print(f"  Created user: {email}")
            else:
                print(f"  User exists: {email}")
            
            email_to_user[email] = user
        
        db.session.commit()
        
        # Refresh user objects to get IDs
        for email in all_emails:
            email_to_user[email] = User.query.filter_by(email=email).first()
        
        # Create/update runs and ownership
        print("\nCreating/updating runs and ownership...")
        
        for run_data in run_data_list:
            runid = run_data['runid']
            
            # Strip prefix if present (e.g., "ab/some-run" -> "some-run")
            # runid should be just the slug for get_wd() to work correctly
            if '/' in runid:
                runid = runid.split('/', 1)[1]
            
            config = run_data.get('config')
            users = run_data.get('users', [])
            earliest_access = run_data.get('earliest_access')
            
            # Parse earliest access datetime
            if earliest_access:
                try:
                    date_created = datetime.fromisoformat(earliest_access)
                except ValueError:
                    date_created = datetime.utcnow()
            else:
                date_created = datetime.utcnow()
            
            # Find or create run
            run = Run.query.filter_by(runid=runid).first()
            
            if run is None:
                # Determine owner_id from first user to access
                owner_id = None
                if users:
                    first_email = users[0]['email'].lower()
                    owner_user = email_to_user.get(first_email)
                    if owner_user:
                        owner_id = owner_user.id
                
                run = Run(
                    runid=runid,
                    config=config,
                    owner_id=owner_id,
                    date_created=date_created
                )
                db.session.add(run)
                print(f"  Created run: {runid}")
            else:
                print(f"  Run exists: {runid}")
            
            db.session.commit()
            
            # Refresh to get ID
            run = Run.query.filter_by(runid=runid).first()
            
            # Add all users who accessed this run as owners
            for user_info in users:
                email = user_info['email'].lower()
                user = email_to_user.get(email)
                if user and run not in user.runs:
                    user.runs.append(run)
                    print(f"    Added {email} as owner of {runid}")
        
        db.session.commit()
        print("\nImport complete!")


def main():
    parser = argparse.ArgumentParser(
        description='Import run/user data from JSONL into database'
    )
    parser.add_argument(
        'jsonl_file',
        help='Path to JSONL file from scan_access_logs.py'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--database-url',
        help='Database URL (default: from DATABASE_URL env or postgresql://weppcloud:weppcloud@postgres:5432/weppcloud)'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.jsonl_file):
        print(f"Error: File not found: {args.jsonl_file}", file=sys.stderr)
        sys.exit(1)
    
    import_data(args.jsonl_file, dry_run=args.dry_run, database_url=args.database_url)


if __name__ == '__main__':
    main()
