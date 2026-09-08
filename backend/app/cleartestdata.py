"""
Clears all investigation data (cases, evidence, analysis, propagation,
audit, reports, case_assignments) while leaving `users` and `sessions`
untouched, so your login/accounts survive.

Run from the `backend` directory (same place you'd run the app), e.g.:
    python clear_test_data.py

Make a backup first if you haven't already:
    cp truthtrace.db truthtrace.db.backup
"""
from db import conn

TABLES_IN_DELETE_ORDER = [
    'analysis',
    'propagation',
    'audit',
    'reports',
    'case_assignments',
    'evidence',
    'cases',
]

# Only these use INTEGER PRIMARY KEY AUTOINCREMENT, so only these need
# their sqlite_sequence entry reset to make new IDs start from 1 again.
AUTOINCREMENT_TABLES = ['analysis', 'propagation', 'audit', 'reports']


def main():
    c = conn()
    try:
        counts_before = {}
        for t in TABLES_IN_DELETE_ORDER:
            counts_before[t] = c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]

        c.execute('BEGIN')
        for t in TABLES_IN_DELETE_ORDER:
            c.execute(f'DELETE FROM {t}')
        if AUTOINCREMENT_TABLES:
            placeholders = ','.join('?' for _ in AUTOINCREMENT_TABLES)
            c.execute(f'DELETE FROM sqlite_sequence WHERE name IN ({placeholders})', AUTOINCREMENT_TABLES)
        c.commit()
        c.execute('VACUUM')

        print('Cleared:')
        for t in TABLES_IN_DELETE_ORDER:
            print(f'  {t}: {counts_before[t]} row(s) removed')
        print('\nusers and sessions were NOT touched.')
    except Exception as e:
        c.rollback()
        print('Something went wrong, rolled back. No data was deleted.')
        print(f'Error: {e}')
        raise
    finally:
        c.close()


if __name__ == '__main__':
    confirm = input('This will permanently delete ALL cases/evidence/analysis data. Type "yes" to continue: ')
    if confirm.strip().lower() == 'yes':
        main()
    else:
        print('Cancelled. No data was deleted.')