"""Database migration script — adds missing columns and tables."""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "data", "bridgepoint.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check existing columns in jobs table
c.execute("PRAGMA table_info(jobs)")
cols = [row[1] for row in c.fetchall()]
print("Current jobs columns:", cols)

# Add missing columns
if "accepted_at" not in cols:
    c.execute("ALTER TABLE jobs ADD COLUMN accepted_at DATETIME")
    print("Added: accepted_at")
else:
    print("accepted_at already exists")

if "allotted_labor_id" not in cols:
    c.execute("ALTER TABLE jobs ADD COLUMN allotted_labor_id INTEGER REFERENCES users(id)")
    print("Added: allotted_labor_id")
else:
    print("allotted_labor_id already exists")

# Check if messages table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
if not c.fetchone():
    c.execute("""CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL REFERENCES jobs(id),
        sender_id INTEGER NOT NULL REFERENCES users(id),
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("CREATE INDEX ix_messages_job_created ON messages(job_id, created_at)")
    c.execute("CREATE INDEX ix_messages_sender_id ON messages(sender_id)")
    print("Created: messages table with indexes")
else:
    print("messages table already exists")

conn.commit()
conn.close()
print("Migration complete!")
