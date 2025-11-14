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
    data = request.json
    user_id = request.user['id']
    
    conn = sqlite3.connect('setora.db')
    c = conn.cursor()
    
    c.execute('INSERT INTO workouts (user_id, date, notes) VALUES (?, ?, ?)',
             (user_id, data['date'], data.get('notes', '')))
    workout_id = c.lastrowid
    
    for ex in data['exercises']:
        c.execute('''INSERT INTO workout_exercises 
                   (workout_id, exercise_id, sets, reps, weight, duration, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (workout_id, ex['exercise_id'], ex.get('sets'), ex.get('reps'),
                  ex.get('weight'), ex.get('duration'), ex.get('notes', '')))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'workout_id': workout_id})

@app.route('/api/workouts', methods=['GET'])
@require_auth
def get_workouts():
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
        
        c.execute('''SELECT we.*, e.name, e.category 
                    FROM workout_exercises we
                    JOIN exercises e ON we.exercise_id = e.id
                    WHERE we.workout_id = ?''', (workout['id'],))
        
        exercises = []
        categories = set()
        
        for ex_row in c.fetchall():
            ex = dict(ex_row)
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
    user_id = request.user['id']
    
    conn = sqlite3.connect('setora.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''SELECT w.date, e.category, 
                 SUM(we.sets * we.reps * we.weight) as volume,
                 COUNT(we.id) as exercise_count
                 FROM workouts w
                 JOIN workout_exercises we ON w.id = we.workout_id
                 JOIN exercises e ON we.exercise_id = e.id
                 WHERE w.user_id = ?
                 GROUP BY w.date, e.category
                 ORDER BY w.date''', (user_id,))
    
    workout_stats = [dict(row) for row in c.fetchall()]
    
    c.execute('''SELECT e.category, COUNT(DISTINCT w.date) as frequency
                 FROM workouts w
                 JOIN workout_exercises we ON w.id = we.workout_id
                 JOIN exercises e ON we.exercise_id = e.id
                 WHERE w.user_id = ?
                 GROUP BY e.category''', (user_id,))
    
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
    app.run(host="0.0.0.0", debug=True, port=5000)
