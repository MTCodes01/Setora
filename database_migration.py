import sqlite3
from datetime import datetime

def migrate_database():
    """
    Migration script to upgrade database schema for new workout system
    Run this ONCE before deploying new version
    """
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    
    print("Starting database migration...")
    
    # 1. Create user_exercises table for custom exercises
    print("Creating user_exercises table...")
    c.execute('''CREATE TABLE IF NOT EXISTS user_exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        equipment TEXT,
        image_url TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, name)
    )''')
    
    # 2. Create workout_sets table for detailed set tracking
    print("Creating workout_sets table...")
    c.execute('''CREATE TABLE IF NOT EXISTS workout_sets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_exercise_id INTEGER NOT NULL,
        set_number INTEGER NOT NULL,
        reps INTEGER,
        weight REAL,
        duration REAL,
        notes TEXT,
        FOREIGN KEY (workout_exercise_id) REFERENCES workout_exercises(id) ON DELETE CASCADE
    )''')
    
    # 3. Add new columns to workouts table
    print("Adding columns to workouts table...")
    try:
        c.execute('ALTER TABLE workouts ADD COLUMN is_rest_day INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        print("  - is_rest_day column already exists")
    
    try:
        c.execute('ALTER TABLE workouts ADD COLUMN merged_at TEXT')
    except sqlite3.OperationalError:
        print("  - merged_at column already exists")
    
    # 4. Add new columns to workout_exercises table
    print("Adding columns to workout_exercises table...")
    try:
        c.execute('ALTER TABLE workout_exercises ADD COLUMN is_custom INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        print("  - is_custom column already exists")
    
    try:
        c.execute('ALTER TABLE workout_exercises ADD COLUMN order_index INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        print("  - order_index column already exists")
    
    # 5. Migrate existing workout data to new sets structure
    print("Migrating existing workout data...")
    c.execute('''SELECT id, sets, reps, weight, duration 
                 FROM workout_exercises 
                 WHERE sets IS NOT NULL OR reps IS NOT NULL OR weight IS NOT NULL''')
    
    old_exercises = c.fetchall()
    migrated_count = 0
    
    for ex_id, sets, reps, weight, duration in old_exercises:
        # Check if already migrated
        c.execute('SELECT COUNT(*) FROM workout_sets WHERE workout_exercise_id = ?', (ex_id,))
        if c.fetchone()[0] > 0:
            continue
        
        # Create sets based on old data
        num_sets = sets if sets else 1
        for set_num in range(1, num_sets + 1):
            c.execute('''INSERT INTO workout_sets 
                        (workout_exercise_id, set_number, reps, weight, duration)
                        VALUES (?, ?, ?, ?, ?)''',
                     (ex_id, set_num, reps, weight, duration))
            migrated_count += 1
    
    print(f"  - Migrated {migrated_count} sets from old format")
    
    # 6. Create indexes for better performance
    print("Creating indexes...")
    try:
        c.execute('CREATE INDEX IF NOT EXISTS idx_user_exercises_user ON user_exercises(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_workout_sets_exercise ON workout_sets(workout_exercise_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(user_id, date)')
    except sqlite3.OperationalError as e:
        print(f"  - Index creation note: {e}")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration completed successfully!")
    print("\nNext steps:")
    print("1. Backup your database before proceeding")
    print("2. Deploy the new Flask application code")
    print("3. Test the new features")

if __name__ == '__main__':
    migrate_database()