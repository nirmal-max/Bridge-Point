"""
Bridge Point - Payment V2 Migration
Adds Platform Custody Payment columns to jobs table and is_admin to users table.
Run once: python migrate_payment_v2.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "bridgepoint.db"


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    new_job_columns = [
        ("platform_commission_paise", "INTEGER NOT NULL DEFAULT 0"),
        ("worker_payout_paise", "INTEGER NOT NULL DEFAULT 0"),
        ("payment_status", "TEXT DEFAULT 'pending'"),
        ("payment_sent_at", "TIMESTAMP"),
        ("payout_released_at", "TIMESTAMP"),
    ]

    for col_name, col_type in new_job_columns:
        try:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
            print(f"  + Added jobs.{col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  . jobs.{col_name} already exists")
            else:
                raise

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
        print("  + Added users.is_admin")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  . users.is_admin already exists")
        else:
            raise

    print("\n  Backfilling platform custody fields...")
    cursor.execute("SELECT id, budget_paise FROM jobs WHERE platform_commission_paise = 0 AND budget_paise > 0")
    rows = cursor.fetchall()
    for job_id, budget_paise in rows:
        commission = round(budget_paise * 0.03)
        payout = budget_paise - commission
        cursor.execute(
            "UPDATE jobs SET platform_commission_paise = ?, worker_payout_paise = ? WHERE id = ?",
            (commission, payout, job_id),
        )
    print(f"  + Backfilled {len(rows)} jobs")

    print("\n  Migrating old payment statuses...")
    cursor.execute("UPDATE jobs SET status = 'payment_completed', payment_status = 'payout_released' WHERE status = 'paid'")
    print(f"  + Migrated {cursor.rowcount} 'paid' -> 'payment_completed'")

    cursor.execute("UPDATE jobs SET status = 'payment_completed', payment_status = 'payout_released' WHERE status = 'payment_received'")
    print(f"  + Migrated {cursor.rowcount} 'payment_received' -> 'payment_completed'")

    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_jobs_payment_status ON jobs(payment_status)")
        print("  + Created index ix_jobs_payment_status")
    except Exception:
        pass

    cursor.execute("UPDATE users SET is_admin = 1 WHERE id = 1")
    print("  + Set user #1 as admin")

    conn.commit()
    conn.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()
