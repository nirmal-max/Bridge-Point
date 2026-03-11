"""
Bridge Point — Cashfree Migration
Renames Razorpay columns to Cashfree, updates commission to 3%.
Run once: python migrate_cashfree.py
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

    # ─── 1. Rename razorpay columns in payments table ────
    print("Updating payments table columns...")
    try:
        # SQLite doesn't support RENAME COLUMN in older versions,
        # so we recreate the table if needed
        cursor.execute("PRAGMA table_info(payments)")
        columns = [col[1] for col in cursor.fetchall()]

        if "razorpay_order_id" in columns:
            # Recreate table with new column names
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL UNIQUE REFERENCES jobs(id),
                    employer_id INTEGER NOT NULL REFERENCES users(id),
                    worker_id INTEGER NOT NULL REFERENCES users(id),
                    cashfree_order_id VARCHAR(100) UNIQUE,
                    cashfree_payment_id VARCHAR(100),
                    cashfree_payout_id VARCHAR(100),
                    amount_total_paise INTEGER NOT NULL,
                    platform_commission_paise INTEGER NOT NULL,
                    worker_payout_paise INTEGER NOT NULL,
                    payment_status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified_at TIMESTAMP,
                    transferred_at TIMESTAMP
                )
            """)
            cursor.execute("""
                INSERT INTO payments_new (
                    id, job_id, employer_id, worker_id,
                    cashfree_order_id, cashfree_payment_id,
                    amount_total_paise, platform_commission_paise, worker_payout_paise,
                    payment_status, created_at, verified_at, transferred_at
                )
                SELECT
                    id, job_id, employer_id, worker_id,
                    razorpay_order_id, razorpay_payment_id,
                    amount_total_paise, platform_commission_paise, worker_payout_paise,
                    payment_status, created_at, verified_at, transferred_at
                FROM payments
            """)
            cursor.execute("DROP TABLE payments")
            cursor.execute("ALTER TABLE payments_new RENAME TO payments")
            print("  + Payments table rebuilt with Cashfree columns")
        elif "cashfree_order_id" in columns:
            print("  . Payments table already has Cashfree columns")
        else:
            # Create fresh payments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL UNIQUE REFERENCES jobs(id),
                    employer_id INTEGER NOT NULL REFERENCES users(id),
                    worker_id INTEGER NOT NULL REFERENCES users(id),
                    cashfree_order_id VARCHAR(100) UNIQUE,
                    cashfree_payment_id VARCHAR(100),
                    cashfree_payout_id VARCHAR(100),
                    amount_total_paise INTEGER NOT NULL,
                    platform_commission_paise INTEGER NOT NULL,
                    worker_payout_paise INTEGER NOT NULL,
                    payment_status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified_at TIMESTAMP,
                    transferred_at TIMESTAMP
                )
            """)
            print("  + Fresh payments table created")
    except Exception as e:
        print(f"  ! Error updating payments: {e}")

    cursor.execute("CREATE INDEX IF NOT EXISTS ix_payments_job_id ON payments(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments(cashfree_order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(payment_status)")

    # ─── 2. Update users table ───────────────────────────
    print("\nUpdating users table...")
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN bank_account_number VARCHAR(20)")
        print("  + Added users.bank_account_number")
    except sqlite3.OperationalError:
        print("  . users.bank_account_number already exists")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN bank_ifsc VARCHAR(11)")
        print("  + Added users.bank_ifsc")
    except sqlite3.OperationalError:
        print("  . users.bank_ifsc already exists")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN payout_upi_id VARCHAR(50)")
        print("  + Added users.payout_upi_id")
    except sqlite3.OperationalError:
        print("  . users.payout_upi_id already exists")

    # ─── 3. Update jobs table ────────────────────────────
    print("\nUpdating jobs table...")
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN cashfree_order_id VARCHAR(100)")
        print("  + Added jobs.cashfree_order_id")
    except sqlite3.OperationalError:
        print("  . jobs.cashfree_order_id already exists")

    # Copy razorpay_order_id to cashfree_order_id if exists
    cursor.execute("PRAGMA table_info(jobs)")
    job_columns = [col[1] for col in cursor.fetchall()]
    if "razorpay_order_id" in job_columns:
        cursor.execute("UPDATE jobs SET cashfree_order_id = razorpay_order_id WHERE razorpay_order_id IS NOT NULL")
        print("  + Migrated razorpay_order_id values to cashfree_order_id")

    # ─── 4. Update commission rates (3% model) ───────────
    print("\nUpdating commission rates to 3% model...")
    cursor.execute("SELECT id, budget_paise FROM jobs WHERE budget_paise > 0")
    rows = cursor.fetchall()
    for job_id, budget_paise in rows:
        platform_commission = round(budget_paise * 0.03)
        worker_payout = budget_paise - platform_commission
        cursor.execute(
            """UPDATE jobs SET
                employer_commission_paise = 0,
                employer_total_paise = ?,
                labor_commission_paise = 0,
                labor_receives_paise = ?,
                platform_earning_paise = ?,
                platform_commission_paise = ?,
                worker_payout_paise = ?
            WHERE id = ?""",
            (budget_paise, worker_payout, platform_commission,
             platform_commission, worker_payout, job_id),
        )
    print(f"  + Updated {len(rows)} jobs to 3% model")

    # ─── 5. Migrate legacy payment statuses ──────────────
    print("\nMigrating legacy payment statuses...")
    status_map = {
        "payment_in_process": "payment_pending",
        "verification_pending": "payment_pending",
        "verified": "payment_paid",
        "payout_released": "payout_transferred",
    }
    for old_status, new_status in status_map.items():
        cursor.execute(
            "UPDATE jobs SET status = ? WHERE status = ?",
            (new_status, old_status),
        )
        count = cursor.rowcount
        if count > 0:
            print(f"  + Migrated {count} jobs: '{old_status}' -> '{new_status}'")

    # Update payment_method from razorpay to cashfree
    cursor.execute(
        "UPDATE jobs SET payment_method = 'cashfree' WHERE payment_method = 'razorpay'"
    )
    migrated = cursor.rowcount
    if migrated > 0:
        print(f"  + Updated {migrated} jobs: payment_method 'razorpay' -> 'cashfree'")

    conn.commit()
    conn.close()
    print("\nCashfree migration complete!")


if __name__ == "__main__":
    migrate()
