import sqlite3
import os

DB_PATH = 'db.sqlite3'

def fix_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(stores)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'map_location' in columns:
            print("Found map_location column. Dropping it...")
            # SQLite 3.35+ supports DROP COLUMN
            cursor.execute("ALTER TABLE stores DROP COLUMN map_location")
            conn.commit()
            print("Successfully dropped map_location column.")
        else:
            print("map_location column does not exist.")
            
    except sqlite3.OperationalError as e:
        print(f"Error executing SQL: {e}")
        print("Note: ALTER TABLE DROP COLUMN requires SQLite 3.35.0+")
        # If DROP COLUMN is not supported, we have to recreate the table (omitted for safety unless needed)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_db()
