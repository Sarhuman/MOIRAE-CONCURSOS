"""Read-only account diagnosis; never emits credentials or confirmation links."""
import argparse
import json
import sqlite3
import time
from pathlib import Path
from .accounts import POLICY_VERSION


def inspect(database, email):
    target = Path(database).resolve(strict=True)
    with sqlite3.connect(target.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        row = db.execute('SELECT id FROM users WHERE email=?', (email.strip().lower(),)).fetchone()
        result = {'database': str(target), 'account_exists': bool(row)}
        if row:
            uid = row['id']
            profile = db.execute('SELECT email_verified,policy_version,accepted_at,adult_pilot FROM user_profiles WHERE user_id=?', (uid,)).fetchone()
            result['profile'] = dict(profile) if profile else None
            result['current_terms'] = bool(profile and profile['policy_version'] == POLICY_VERSION and profile['adult_pilot'])
            result['orders'] = [dict(r) for r in db.execute('SELECT status,plan_id FROM billing_orders WHERE user_id=?', (uid,))]
            result['grants'] = [dict(r) for r in db.execute('SELECT plan_id,status,starts_at,ends_at FROM access_grants WHERE user_id=?', (uid,))]
            result['valid_verification_tokens'] = db.execute("SELECT count(*) FROM account_tokens WHERE user_id=? AND purpose='verify' AND expires_at>?", (uid, int(time.time()))).fetchone()[0]
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--email', default='henrique@example.test')
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.database, args.email), indent=2, ensure_ascii=False))
    except (OSError, sqlite3.Error):
        parser.exit(1, 'Banco inacessível ou incompatível; nenhum dado foi alterado.\n')


if __name__ == '__main__':
    main()
