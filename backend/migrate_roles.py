import sqlite3
import json

db_path = r'C:\Users\NIRMAL KUMAR\.gemini\antigravity\scratch\bridge-point\backend\data\bridgepoint.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # 1. Check if column 'role' exists (to see if we need to rename)
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'role' in columns and 'roles' not in columns:
        print("Renaming 'role' to 'roles'...")
        cursor.execute("ALTER TABLE users RENAME COLUMN role TO roles")
    
    # 2. Convert string roles to JSON arrays
    cursor.execute("SELECT id, roles FROM users")
    users = cursor.fetchall()
    
    for user_id, roles_val in users:
        # If it's already a JSON array (starts with [), skip
        if roles_val and not roles_val.startswith('['):
            new_roles = json.dumps([roles_val])
            cursor.execute("UPDATE users SET roles = ? WHERE id = ?", (new_roles, user_id))
            print(f"Updated user {user_id}: {roles_val} -> {new_roles}")
    
    conn.commit()
    print("Migration completed successfully.")
except Exception as e:
    conn.rollback()
    print(f"Migration failed: {e}")
finally:
    conn.close()
