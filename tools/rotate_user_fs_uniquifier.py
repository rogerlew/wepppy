"""Rotate one user's Flask-Security identity token after suspected theft."""

from __future__ import annotations

import argparse
import uuid

from wepppy.weppcloud.app import User, app, db


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("email", help="Exact WEPPcloud account email")
    parser.add_argument("--apply", action="store_true", help="Commit the rotation")
    args = parser.parse_args()

    with app.app_context():
        user = User.query.filter_by(email=args.email).one_or_none()
        if user is None:
            parser.error("account not found")
        print(f"account_id={user.id} action={'rotate' if args.apply else 'preview'}")
        if not args.apply:
            return 0
        user.fs_uniquifier = uuid.uuid4().hex
        db.session.commit()
        print("rotation=committed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
