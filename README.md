# Setora - Workout Tracker

## About Setora

Setora is a self-hostable personal gym workout tracker with automatic categorization and progress visualization. Track your workouts, monitor body weight, and visualize your fitness journey with beautiful charts and insights.

## Features

### Core Features
- **Workout Logging**: Quick 30-second workout entry with exercise name, sets, reps, and weights
- **Auto Categorization**: Automatically tags workouts (e.g., "Biceps Day", "Cardio Day", "Biceps + Cardio Day")
- **Calendar View**: Visual calendar showing all workout days with color coding
- **Progress Tracking**: Monitor body weight trends and workout volume over time
- **Exercise Library**: Pre-loaded with 24+ exercises across all major muscle groups
- **Dashboard**: Quick stats showing total workouts, weekly activity, and current streak

### Advanced Features
- **Custom Exercises**: Add your own exercises with categories
- **Workout Templates**: Save and reuse common workout routines
- **Progress Charts**: 
  - Body weight trend line chart
  - Workout volume bar chart
  - Category frequency doughnut chart
- **User Profile**: Track personal metrics (height, weight, goals, unit preferences)
- **Workout History**: Detailed view of past workouts with notes

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Setup

1. **Clone or download the project files**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Run the Flask backend**:
```bash
python app.py
```

The backend will start on `http://localhost:5000`

## 📁 Project Structure

```
setora/
├── app.py              # Flask backend with API endpoints
├── templates/
│   └── index.html      # Frontend HTML/CSS/JS
├── requirements.txt    # Python dependencies
├── setora.db           # SQLite database (auto-created)
├── .gitignore          # Ignores extra files from git
├── LICENSE             # GNU GPL v3 License
├── Dockerfile          # Docker File
└── README.md           # This file
```

## 🗄️ Database Schema

The app uses SQLite with the following tables:

- **users**: User profile information
- **sessions**: Stores the session tokens
- **exercises**: Exercise library with categories
- **workouts**: Workout sessions
- **workout_exercises**: Exercises performed in each workout
- **weight_logs**: Body weight tracking
- **workout_templates**: Saved workout routines

## 🎮 Usage Guide

### Adding a Workout

1. Click **"Add Workout"** in the navigation
2. Select the date (defaults to today)
3. Click **"+ Add Exercise"**
4. Choose an exercise from the dropdown
5. Enter sets, reps, and weight
6. Add notes (optional)
7. Click **"Save Workout"**

### Viewing Progress

1. Navigate to **"Progress"** tab
2. View three charts:
   - **Weight Trend**: Track body weight over time
   - **Workout Volume**: See total volume lifted per session
   - **Category Frequency**: Understand which muscle groups you train most

### Calendar View

- Color-coded days show workout activity
- Click any day to see workout details
- Navigate between months with arrow buttons

### Profile Management

1. Go to **"Profile"** tab
2. Update personal information
3. Log body weight regularly for accurate progress tracking
4. Set fitness goals

## 🎨 Customization

### Adding Custom Exercises

```python
# In the backend, you can add exercises via API:
POST /api/exercises
{
    "name": "Bulgarian Split Squat",
    "category": "Legs",
    "equipment": "Dumbbell"
}
```

### Available Categories

- Chest
- Biceps
- Triceps
- Legs
- Back
- Shoulders
- Cardio
- Core

## 🔧 API Endpoints

### User Management
- `GET /api/user` - Get user profile
- `PUT /api/user` - Update user profile

### Exercises
- `GET /api/exercises` - Get all exercises
- `POST /api/exercises` - Add new exercise

### Workouts
- `GET /api/workouts` - Get all workouts
- `POST /api/workouts` - Log new workout

### Progress
- `GET /api/progress` - Get workout statistics
- `GET /api/weight` - Get weight logs
- `POST /api/weight` - Log body weight

### Templates
- `GET /api/templates` - Get saved templates
- `POST /api/templates` - Save workout template

## 🚢 Deployment Options

### Local Development
Already configured! Just run `python app.py`

### Production Deployment

**Backend (Render/Railway/Heroku)**:
1. Push code to GitHub
2. Connect repository to hosting platform
3. Set Python buildpack
4. Deploy

**Frontend (Can be served by Flask)**:
The current setup serves the frontend via Flask templates, so deploying the backend automatically deploys the frontend.

**Database**:
- Development: SQLite (included)
- Production: Consider PostgreSQL for better concurrency

## 🔒 Security Notes

- This is a development version with a simple secret key
- For production, use environment variables for sensitive data
- Add user authentication (Flask-Login or JWT)
- Use proper password hashing (bcrypt)

## 🎯 Future Enhancements

- [x] Multi-user authentication
- [ ] Better UI/UX
- [ ] Workout reminders & notifications
- [ ] Progressive overload tracking
- [ ] Exercise form videos/GIFs
- [ ] Mobile app (React Native)
- [ ] Social features (share workouts)
- [ ] Fitness device integration (Fitbit, Apple Health)
- [ ] AI-powered workout suggestions
- [ ] Personal records (PRs) tracking
- [ ] Export data to CSV/PDF

## 🐛 Troubleshooting

**Port already in use**:
```bash
# Change port in app.py:
app.run(debug=True, port=5001)  # Use different port
```

**Database locked**:
```bash
# Delete and recreate database:
rm setora.db
python app.py
```

**CORS errors**:
- Ensure Flask-CORS is installed
- Check that frontend is accessing correct API URL

## 📝 License

This project is open source and available for personal and educational use.

## 🤝 Contributing

Feel free to fork, improve, and submit pull requests!

## 💪 Built With

- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Charts**: Chart.js
- **Database**: SQLite
- **Styling**: Custom CSS with modern design principles

---

**Start tracking your fitness journey with Setora today! 💪**
