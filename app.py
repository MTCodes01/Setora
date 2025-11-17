from flask import Flask, render_template, request, jsonify, session, make_response
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import sqlite3
from collections import defaultdict
import os
import hashlib
import secrets
from functools import wraps

app = Flask(__name__)
app.secret_key = 'setora_secret_key'
# CORS(app, supports_credentials=True, origins=['http://localhost:6000', 'http://127.0.0.1:6000'])

# @app.after_request
# def after_request(response):
#     origin = request.headers.get('Origin')
#     if origin in ['http://localhost:6000', 'http://127.0.0.1:6000']:
#         response.headers.add('Access-Control-Allow-Origin', origin)
#         response.headers.add('Access-Control-Allow-Credentials', 'true')
#         response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
#         response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
#     return response

# Database initialization
def init_db():
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    
    # Users table with authentication
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        height REAL,
        weight REAL,
        goal TEXT,
        unit_preference TEXT DEFAULT 'kg',
        theme_preference TEXT DEFAULT 'light',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Exercises library
    c.execute('''CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        equipment TEXT
    )''')
    
    # Workouts
    c.execute('''CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Workout exercises
    c.execute('''CREATE TABLE IF NOT EXISTS workout_exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_id INTEGER NOT NULL,
        exercise_id INTEGER NOT NULL,
        sets INTEGER,
        reps INTEGER,
        weight REAL,
        duration REAL,
        notes TEXT,
        FOREIGN KEY (workout_id) REFERENCES workouts(id),
        FOREIGN KEY (exercise_id) REFERENCES exercises(id)
    )''')
    
    # Weight logs
    c.execute('''CREATE TABLE IF NOT EXISTS weight_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        weight REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Templates
    c.execute('''CREATE TABLE IF NOT EXISTS workout_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        exercises TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    conn.commit()
    conn.close()

def seed_exercises():
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    
    # Check if exercises exist
    c.execute('SELECT COUNT(*) FROM exercises')
    if c.fetchone()[0] == 0:
        exercises = [
            ('Bench Press', 'Chest', 'Barbell'),
            ('Incline Dumbbell Press', 'Chest', 'Dumbbell'),
            ('Push-ups', 'Chest', 'Bodyweight'),
            ('Barbell Curl', 'Biceps', 'Barbell'),
            ('Dumbbell Curl', 'Biceps', 'Dumbbell'),
            ('Hammer Curl', 'Biceps', 'Dumbbell'),
            ('Tricep Dips', 'Triceps', 'Bodyweight'),
            ('Tricep Pushdown', 'Triceps', 'Cable'),
            ('Overhead Extension', 'Triceps', 'Dumbbell'),
            ('Squat', 'Legs', 'Barbell'),
            ('Leg Press', 'Legs', 'Machine'),
            ('Lunges', 'Legs', 'Dumbbell'),
            ('Deadlift', 'Back', 'Barbell'),
            ('Pull-ups', 'Back', 'Bodyweight'),
            ('Lat Pulldown', 'Back', 'Cable'),
            ('Shoulder Press', 'Shoulders', 'Dumbbell'),
            ('Lateral Raise', 'Shoulders', 'Dumbbell'),
            ('Front Raise', 'Shoulders', 'Dumbbell'),
            ('Running', 'Cardio', 'None'),
            ('Cycling', 'Cardio', 'Machine'),
            ('Jump Rope', 'Cardio', 'Equipment'),
            ('Plank', 'Core', 'Bodyweight'),
            ('Crunches', 'Core', 'Bodyweight'),
            ('Russian Twist', 'Core', 'Bodyweight')
        ]
        c.executemany('INSERT INTO exercises (name, category, equipment) VALUES (?, ?, ?)', exercises)
        conn.commit()
    
    conn.close()

# Initialize database on startup
init_db()
seed_exercises()

# Authentication helpers
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token():
    return secrets.token_urlsafe(32)

def create_session(user_id):
    token = generate_token()
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    c.execute('INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)',
             (user_id, token, expires_at))
    conn.commit()
    conn.close()
    
    return token

def get_user_from_token(token):
    if not token:
        return None
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    c.execute('''SELECT u.* FROM users u
                 JOIN sessions s ON u.id = s.user_id
                 WHERE s.token = ? AND s.expires_at > ?''',
             (token, datetime.now().isoformat()))
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0], 'email': user[1], 'name': user[3], 'age': user[4],
            'gender': user[5], 'height': user[6], 'weight': user[7],
            'goal': user[8], 'unit_preference': user[9], 'theme_preference': user[10]
        }
    return None

def check_valid_token(token):
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    c.execute('SELECT * FROM sessions WHERE token = ? AND expires_at > ?',
             (token, datetime.now().isoformat()))
    session = c.fetchone()
    conn.close()
    return session is not None

def get_token_from_request():
    # Try Authorization header first
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    # Fall back to cookie
    return request.cookies.get('session_token')

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow CORS preflight requests through
        if request.method == 'OPTIONS':
            return jsonify({'ok': True}), 200

        token = get_token_from_request()
        # Use check_valid_token for a quick validity check
        if not token or not check_valid_token(token):
            return jsonify({'authenticated': False}), 401

        # Fetch the full user object
        user = get_user_from_token(token)
        if not user:
            return jsonify({'authenticated': False}), 401

        request.user = user
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

# Authentication routes
@app.route('/api/auth/signup', methods=['POST', 'OPTIONS'])
def signup():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
        
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        
        if not email or not password or not name:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        password_hash = hash_password(password)
        
        conn = sqlite3.connect('setora.db')
        c = conn.cursor()
        
        try:
            c.execute('''INSERT INTO users (email, password_hash, name, theme_preference)
                         VALUES (?, ?, ?, ?)''',
                      (email, password_hash, name, 'light'))
            user_id = c.lastrowid
            conn.commit()
            conn.close()
            
            token = create_session(user_id)
            
            response = make_response(jsonify({'success': True, 'user': {'id': user_id, 'name': name, 'email': email}}))
            response.set_cookie('session_token', token, max_age=30*24*60*60, httponly=True, samesite='Lax', secure=False)
            return response
            
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'success': False, 'error': 'Email already exists'}), 400
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
        
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        print(f"Login attempt for: {email}")  # Debug log
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Missing credentials'}), 400
        
        password_hash = hash_password(password)
        
        conn = sqlite3.connect('setora.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ? AND password_hash = ?',
                 (email, password_hash))
        user = c.fetchone()
        conn.close()
        
        if user:
            print(f"Login successful for user: {user[0]}")  # Debug log
            token = create_session(user[0])
            response = make_response(jsonify({
                'success': True,
                'user': {
                    'id': user[0],
                    'email': user[1],
                    'name': user[3],
                    'theme_preference': user[10]
                }
            }))
            response.set_cookie('session_token', token, max_age=30*24*60*60, httponly=True, samesite='Lax', secure=False)
            return response
        
        print("Login failed: Invalid credentials")  # Debug log
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST', 'OPTIONS'])
def logout():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
        
    token = get_token_from_request()
    
    if token:
        conn = sqlite3.connect('setora.db')
        c = conn.cursor()
        c.execute('DELETE FROM sessions WHERE token = ?', (token,))
        conn.commit()
        conn.close()
    
    return jsonify({'success': True})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    token = get_token_from_request()
    user = get_user_from_token(token)
    
    if user:
        return jsonify({'authenticated': True, 'user': user})
    return jsonify({'authenticated': False}), 401

# User routes
@app.route('/api/user', methods=['GET'])
@require_auth
def get_user():
    return jsonify(request.user)

@app.route('/api/user', methods=['PUT'])
@require_auth
def update_user():
    data = request.json
    user_id = request.user['id']
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    c.execute('''UPDATE users SET name=?, age=?, gender=?, height=?, weight=?, goal=?, unit_preference=?, theme_preference=?
                 WHERE id=?''',
              (data.get('name'), data.get('age'), data.get('gender'), data.get('height'),
               data.get('weight'), data.get('goal'), data.get('unit_preference'), 
               data.get('theme_preference'), user_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# custom exercise routes
@app.route('/api/exercises/custom', methods=['POST'])
@require_auth
def add_custom_exercise():
    """Create a custom exercise for the current user"""
    data = request.json
    user_id = request.user['id']
    
    # Validation
    if not data.get('name') or not data.get('category'):
        return jsonify({'success': False, 'error': 'Name and category are required'}), 400
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO user_exercises (user_id, name, category, equipment, image_url)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, data['name'], data['category'], 
                   data.get('equipment', ''), data.get('image_url', '')))
        exercise_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'exercise': {
                'id': exercise_id,
                'name': data['name'],
                'category': data['category'],
                'equipment': data.get('equipment', ''),
                'image_url': data.get('image_url', ''),
                'is_custom': True
            }
        })
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'error': 'You already have an exercise with this name'}), 400

@app.route('/api/exercises/custom/<int:exercise_id>', methods=['DELETE'])
@require_auth
def delete_custom_exercise(exercise_id):
    """Delete a custom exercise"""
    user_id = request.user['id']
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    
    # Verify ownership
    c.execute('SELECT id FROM user_exercises WHERE id = ? AND user_id = ?', 
              (exercise_id, user_id))
    
    if not c.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'Exercise not found'}), 404
    
    c.execute('DELETE FROM user_exercises WHERE id = ?', (exercise_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/exercises/all', methods=['GET'])
@require_auth
def get_all_exercises():
    """Get built-in exercises + user's custom exercises"""
    user_id = request.user['id']
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    
    # Built-in exercises
    c.execute('SELECT id, name, category, equipment FROM exercises ORDER BY category, name')
    builtin = [{'id': row[0], 'name': row[1], 'category': row[2], 
                'equipment': row[3], 'is_custom': False} 
               for row in c.fetchall()]
    
    # User's custom exercises
    c.execute('''SELECT id, name, category, equipment, image_url 
                 FROM user_exercises 
                 WHERE user_id = ? 
                 ORDER BY category, name''', (user_id,))
    custom = [{'id': f'custom_{row[0]}', 'name': row[1], 'category': row[2], 
               'equipment': row[3], 'image_url': row[4], 'is_custom': True} 
              for row in c.fetchall()]
    
    conn.close()
    
    return jsonify(builtin + custom)

# Exercise routes
@app.route('/api/exercises', methods=['GET'])
@require_auth
def get_exercises():
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    c.execute('SELECT * FROM exercises ORDER BY category, name')
    exercises = [{'id': row[0], 'name': row[1], 'category': row[2], 'equipment': row[3]}
                 for row in c.fetchall()]
    conn.close()
    return jsonify(exercises)

@app.route('/api/exercises', methods=['POST'])
@require_auth
def add_exercise():
    data = request.json
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO exercises (name, category, equipment) VALUES (?, ?, ?)',
                 (data['name'], data['category'], data['equipment']))
        conn.commit()
        exercise_id = c.lastrowid
        conn.close()
        return jsonify({'success': True, 'id': exercise_id})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'error': 'Exercise already exists'}), 400

# Workout routes
@app.route('/api/workouts', methods=['POST'])
@require_auth
def add_workout():
    """Add workout with merge support and rest day handling"""
    data = request.json
    user_id = request.user['id']
    workout_date = data['date']
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    
    # Check if workout already exists for this date
    c.execute('SELECT id FROM workouts WHERE user_id = ? AND date = ?', 
              (user_id, workout_date))
    existing = c.fetchone()
    
    if data.get('is_rest_day'):
        # Handle rest day
        if existing:
            # Update existing workout to rest day
            c.execute('UPDATE workouts SET is_rest_day = 1, notes = ? WHERE id = ?',
                     (data.get('notes', ''), existing[0]))
            workout_id = existing[0]
        else:
            # Create new rest day workout
            c.execute('INSERT INTO workouts (user_id, date, notes, is_rest_day) VALUES (?, ?, ?, 1)',
                     (user_id, workout_date, data.get('notes', '')))
            workout_id = c.lastrowid
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'workout_id': workout_id, 'merged': bool(existing)})
    
    # Regular workout
    if existing:
        # MERGE MODE: Add exercises to existing workout
        workout_id = existing[0]
        c.execute('UPDATE workouts SET merged_at = ?, is_rest_day = 0 WHERE id = ?',
                 (datetime.now().isoformat(), workout_id))
    else:
        # CREATE MODE: New workout
        c.execute('INSERT INTO workouts (user_id, date, notes, is_rest_day) VALUES (?, ?, ?, 0)',
                 (user_id, workout_date, data.get('notes', '')))
        workout_id = c.lastrowid
    
    # Get current max order index for this workout
    c.execute('SELECT COALESCE(MAX(order_index), 0) FROM workout_exercises WHERE workout_id = ?', 
              (workout_id,))
    current_max_order = c.fetchone()[0]
    
    # Add exercises
    for idx, ex in enumerate(data['exercises']):
        # Determine if custom exercise
        exercise_id = ex['exercise_id']
        is_custom = 0
        
        if isinstance(exercise_id, str) and exercise_id.startswith('custom_'):
            is_custom = 1
            exercise_id = int(exercise_id.replace('custom_', ''))
        
        # Insert workout exercise
        c.execute('''INSERT INTO workout_exercises 
                   (workout_id, exercise_id, notes, is_custom, order_index)
                   VALUES (?, ?, ?, ?, ?)''',
                 (workout_id, exercise_id, ex.get('notes', ''), 
                  is_custom, current_max_order + idx + 1))
        
        workout_exercise_id = c.lastrowid
        
        # Add sets
        for set_data in ex.get('sets', []):
            c.execute('''INSERT INTO workout_sets 
                       (workout_exercise_id, set_number, reps, weight, duration, notes)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                     (workout_exercise_id, set_data['set_number'],
                      set_data.get('reps'), set_data.get('weight'),
                      set_data.get('duration'), set_data.get('notes', '')))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'workout_id': workout_id, 'merged': bool(existing)})

@app.route('/api/workouts/<date>', methods=['GET'])
@require_auth
def get_workout_by_date(date):
    """Get workout for a specific date"""
    user_id = request.user['id']
    
    conn = sqlite3.connect('setora.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT * FROM workouts WHERE user_id = ? AND date = ?', 
              (user_id, date))
    workout = c.fetchone()
    
    if not workout:
        conn.close()
        return jsonify({'exists': False})
    
    workout_dict = dict(workout)
    
    # Get exercises and sets
    c.execute('''SELECT we.*, e.name, e.category, e.equipment
                 FROM workout_exercises we
                 JOIN exercises e ON we.exercise_id = e.id
                 WHERE we.workout_id = ? AND we.is_custom = 0
                 ORDER BY we.order_index''', (workout_dict['id'],))
    
    exercises = []
    for ex_row in c.fetchall():
        ex = dict(ex_row)
        
        # Get sets for this exercise
        c.execute('''SELECT * FROM workout_sets 
                    WHERE workout_exercise_id = ? 
                    ORDER BY set_number''', (ex['id'],))
        ex['sets'] = [dict(s) for s in c.fetchall()]
        exercises.append(ex)
    
    # Get custom exercises
    c.execute('''SELECT we.*, ue.name, ue.category, ue.equipment, ue.image_url
                 FROM workout_exercises we
                 JOIN user_exercises ue ON we.exercise_id = ue.id
                 WHERE we.workout_id = ? AND we.is_custom = 1
                 ORDER BY we.order_index''', (workout_dict['id'],))
    
    for ex_row in c.fetchall():
        ex = dict(ex_row)
        ex['is_custom'] = True
        
        c.execute('''SELECT * FROM workout_sets 
                    WHERE workout_exercise_id = ? 
                    ORDER BY set_number''', (ex['id'],))
        ex['sets'] = [dict(s) for s in c.fetchall()]
        exercises.append(ex)
    
    workout_dict['exercises'] = exercises
    workout_dict['exists'] = True
    
    conn.close()
    return jsonify(workout_dict)

@app.route('/api/workouts/rest', methods=['POST'])
@require_auth
def toggle_rest_day():
    """Mark or unmark a day as rest day"""
    data = request.json
    user_id = request.user['id']
    workout_date = data['date']
    is_rest = data.get('is_rest_day', True)
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    
    c.execute('SELECT id FROM workouts WHERE user_id = ? AND date = ?', 
              (user_id, workout_date))
    existing = c.fetchone()
    
    if existing:
        c.execute('UPDATE workouts SET is_rest_day = ? WHERE id = ?',
                 (1 if is_rest else 0, existing[0]))
        workout_id = existing[0]
    else:
        c.execute('INSERT INTO workouts (user_id, date, is_rest_day) VALUES (?, ?, ?)',
                 (user_id, workout_date, 1 if is_rest else 0))
        workout_id = c.lastrowid
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'workout_id': workout_id})

@app.route('/api/workouts', methods=['GET'])
@require_auth
def get_workouts():
    """Get workouts with rest day support and new sets structure"""
    user_id = request.user['id']
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = sqlite3.connect('setora.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = 'SELECT * FROM workouts WHERE user_id=?'
    params = [user_id]
    
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    
    query += ' ORDER BY date DESC'
    
    c.execute(query, params)
    workouts = []
    
    for row in c.fetchall():
        workout = dict(row)
        
        if workout['is_rest_day']:
            workout['day_type'] = 'Rest Day'
            workout['exercises'] = []
        else:
            # Get built-in exercises
            c.execute('''SELECT we.*, e.name, e.category 
                        FROM workout_exercises we
                        JOIN exercises e ON we.exercise_id = e.id
                        WHERE we.workout_id = ? AND we.is_custom = 0
                        ORDER BY we.order_index''', (workout['id'],))
            
            exercises = []
            categories = set()
            
            for ex_row in c.fetchall():
                ex = dict(ex_row)
                
                # Get sets
                c.execute('''SELECT * FROM workout_sets 
                            WHERE workout_exercise_id = ? 
                            ORDER BY set_number''', (ex['id'],))
                ex['sets'] = [dict(s) for s in c.fetchall()]
                
                exercises.append(ex)
                categories.add(ex['category'])
            
            # Get custom exercises
            c.execute('''SELECT we.*, ue.name, ue.category 
                        FROM workout_exercises we
                        JOIN user_exercises ue ON we.exercise_id = ue.id
                        WHERE we.workout_id = ? AND we.is_custom = 1
                        ORDER BY we.order_index''', (workout['id'],))
            
            for ex_row in c.fetchall():
                ex = dict(ex_row)
                ex['is_custom'] = True
                
                c.execute('''SELECT * FROM workout_sets 
                            WHERE workout_exercise_id = ? 
                            ORDER BY set_number''', (ex['id'],))
                ex['sets'] = [dict(s) for s in c.fetchall()]
                
                exercises.append(ex)
                categories.add(ex['category'])
            
            workout['exercises'] = exercises
            
            if len(categories) == 1:
                workout['day_type'] = f"{list(categories)[0]} Day"
            elif len(categories) > 1:
                workout['day_type'] = " + ".join(sorted(categories)) + " Day"
            else:
                workout['day_type'] = "Workout Day"
        
        workouts.append(workout)
    
    conn.close()
    return jsonify(workouts)

# Weight routes
@app.route('/api/weight', methods=['POST'])
@require_auth
def add_weight():
    data = request.json
    user_id = request.user['id']
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    c.execute('INSERT INTO weight_logs (user_id, date, weight) VALUES (?, ?, ?)',
             (user_id, data['date'], data['weight']))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/weight', methods=['GET'])
@require_auth
def get_weight_logs():
    user_id = request.user['id']
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    c.execute('SELECT * FROM weight_logs WHERE user_id=? ORDER BY date DESC',
             (user_id,))
    logs = [{'id': row[0], 'date': row[2], 'weight': row[3]}
            for row in c.fetchall()]
    conn.close()
    
    return jsonify(logs)

# Progress routes
@app.route('/api/progress', methods=['GET'])
@require_auth
def get_progress():
    """Get progress stats with rest day awareness"""
    user_id = request.user['id']
    
    conn = sqlite3.connect('setora.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Volume stats (exclude rest days)
    c.execute('''SELECT w.date, e.category, 
                 SUM(ws.weight * ws.reps) as volume,
                 COUNT(DISTINCT we.id) as exercise_count
                 FROM workouts w
                 JOIN workout_exercises we ON w.id = we.workout_id
                 LEFT JOIN exercises e ON we.exercise_id = e.id AND we.is_custom = 0
                 LEFT JOIN user_exercises ue ON we.exercise_id = ue.id AND we.is_custom = 1
                 LEFT JOIN workout_sets ws ON we.id = ws.workout_exercise_id
                 WHERE w.user_id = ? AND w.is_rest_day = 0
                 GROUP BY w.date, COALESCE(e.category, ue.category)
                 ORDER BY w.date''', (user_id,))
    
    workout_stats = [dict(row) for row in c.fetchall()]
    
    # Category frequency (exclude rest days)
    c.execute('''SELECT COALESCE(e.category, ue.category) as category, 
                 COUNT(DISTINCT w.date) as frequency
                 FROM workouts w
                 JOIN workout_exercises we ON w.id = we.workout_id
                 LEFT JOIN exercises e ON we.exercise_id = e.id AND we.is_custom = 0
                 LEFT JOIN user_exercises ue ON we.exercise_id = ue.id AND we.is_custom = 1
                 WHERE w.user_id = ? AND w.is_rest_day = 0
                 GROUP BY COALESCE(e.category, ue.category)''', (user_id,))
    
    category_freq = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        'workout_stats': workout_stats,
        'category_frequency': category_freq
    })

# Template routes
@app.route('/api/templates', methods=['GET'])
@require_auth
def get_templates():
    user_id = request.user['id']
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    c.execute('SELECT * FROM workout_templates WHERE user_id=?', (user_id,))
    templates = [{'id': row[0], 'name': row[2], 'exercises': json.loads(row[3])}
                 for row in c.fetchall()]
    conn.close()
    return jsonify(templates)

@app.route('/api/templates', methods=['POST'])
@require_auth
def add_template():
    data = request.json
    user_id = request.user['id']
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    c.execute('INSERT INTO workout_templates (user_id, name, exercises) VALUES (?, ?, ?)',
             (user_id, data['name'], json.dumps(data['exercises'])))
    conn.commit()
    template_id = c.lastrowid
    conn.close()
    
    return jsonify({'success': True, 'id': template_id})

if __name__ == '__main__':
    app.run(debug=True, port=5000)