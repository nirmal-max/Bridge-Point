"""
Bridge Point — Cashfree Migration (Dual-Sided 4% + 4%)
Updates all existing jobs to reflect the 4%+4% commission model.
Run once: python migrate_cashfree_dual.py
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

    # ─── Update commission rates (4% + 4% model) ───────────
    print("Updating commission rates to 4%+4% model...")
    cursor.execute("SELECT id, budget_paise FROM jobs WHERE budget_paise > 0")
    rows = cursor.fetchall()

    for job_id, budget_paise in rows:
        employer_commission = round(budget_paise * 0.04)
        labor_commission = round(budget_paise * 0.04)
        employer_total = budget_paise + employer_commission
        worker_payout = budget_paise - labor_commission
        platform_earning = employer_commission + labor_commission

        cursor.execute(
            """UPDATE jobs SET
                employer_commission_paise = ?,
                employer_total_paise = ?,
                labor_commission_paise = ?,
                labor_receives_paise = ?,
                platform_earning_paise = ?,
                platform_commission_paise = ?,
                worker_payout_paise = ?
            WHERE id = ?""",
            (employer_commission, employer_total, labor_commission,
             worker_payout, platform_earning, platform_earning,
             worker_payout, job_id),
        )

    migrated = len(rows)
    print(f"  + Updated {migrated} jobs to 4%+4% commission model")

    try:
        cursor.execute("""
            UPDATE payments
            SET amount_total_paise = (SELECT employer_total_paise FROM jobs WHERE jobs.id = payments.job_id),
                platform_commission_paise = (SELECT platform_commission_paise FROM jobs WHERE jobs.id = payments.job_id),
                worker_payout_paise = (SELECT worker_payout_paise FROM jobs WHERE jobs.id = payments.job_id)
            WHERE payment_status IN ('pending', 'paid')
        """)
        updated_payments = cursor.rowcount
        if updated_payments > 0:
            print(f"  + Synced {updated_payments} pending/paid payment records to new math")
    except sqlite3.OperationalError:
        print("  . No 'payments' table found to sync (expected if DB is fresh)")

    conn.commit()
    conn.close()
    print("\nDual-sided 4%+4% commission migration complete!")


if __name__ == "__main__":
    migrate()
