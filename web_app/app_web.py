"""
Flask Web Application for Gesture Control System
Provides web interface with authentication and gesture control management
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from datetime import datetime
import sqlite3

# Initialize Flask app
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gesture_control.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# ============== DATABASE MODELS ==============

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    gestures = db.relationship('GestureRecord', backref='user', lazy=True, cascade='all, delete-orphan')
    settings = db.relationship('UserSettings', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password is correct"""
        return check_password_hash(self.password, password)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class GestureRecord(db.Model):
    """Model for recorded gestures"""
    __tablename__ = 'gesture_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    gesture_name = db.Column(db.String(120), nullable=False)
    gesture_data = db.Column(db.Text, nullable=False)  # JSON format
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(500))
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'gesture_name': self.gesture_name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserSettings(db.Model):
    """Model for user preferences"""
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    default_effect = db.Column(db.String(50), default='normal')  # rainbow, particle, hologram, etc.
    enable_shape_detection = db.Column(db.Boolean, default=False)
    enable_gesture_recording = db.Column(db.Boolean, default=False)
    gesture_sensitivity = db.Column(db.Float, default=1.0)
    theme = db.Column(db.String(20), default='light')  # light or dark
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'default_effect': self.default_effect,
            'enable_shape_detection': self.enable_shape_detection,
            'enable_gesture_recording': self.enable_gesture_recording,
            'gesture_sensitivity': self.gesture_sensitivity,
            'theme': self.theme
        }


# ============== AUTHENTICATION DECORATOR ==============

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============== ROUTES ==============

@app.route('/')
def index():
    """Home page - Premium landing page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([username, email, password]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('register'))
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        user = User(username=username, email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Get the user ID
        
        # Create default settings
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            from datetime import timezone
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page"""
    user = User.query.get(session['user_id'])
    gestures = GestureRecord.query.filter_by(user_id=user.id).all()
    settings = UserSettings.query.filter_by(user_id=user.id).first()
    
    return render_template('dashboard.html',
                          user=user,
                          gestures=gestures,
                          settings=settings,
                          user_theme=settings.theme if settings else 'light')


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    user = User.query.get(session['user_id'])
    settings = UserSettings.query.filter_by(user_id=user.id).first()
    return render_template('profile.html', user=user, settings=settings, user_theme=settings.theme if settings else 'light')


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings page"""
    user = User.query.get(session['user_id'])
    user_settings = UserSettings.query.filter_by(user_id=user.id).first()
    
    if request.method == 'POST':
        user_settings.default_effect = request.form.get('default_effect', 'normal')
        user_settings.enable_shape_detection = request.form.get('enable_shape_detection') == 'on'
        user_settings.enable_gesture_recording = request.form.get('enable_gesture_recording') == 'on'
        user_settings.gesture_sensitivity = float(request.form.get('gesture_sensitivity', 1.0))
        user_settings.theme = request.form.get('theme', 'light')
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))
    
    return render_template('settings.html', user=user, settings=user_settings, user_theme=user_settings.theme if user_settings else 'light')


# ============== API ENDPOINTS ==============

@app.route('/api/gestures', methods=['GET'])
@login_required
def get_gestures():
    """Get all gestures for user"""
    user_id = session['user_id']
    gestures = GestureRecord.query.filter_by(user_id=user_id).all()
    return jsonify([g.to_dict() for g in gestures])


@app.route('/api/gestures', methods=['POST'])
@login_required
def save_gesture():
    """Save a new gesture"""
    user_id = session['user_id']
    data = request.get_json()
    
    gesture = GestureRecord(
        user_id=user_id,
        gesture_name=data.get('gesture_name', 'Unnamed'),
        gesture_data=data.get('gesture_data', ''),
        description=data.get('description', '')
    )
    db.session.add(gesture)
    db.session.commit()
    
    return jsonify({'success': True, 'gesture_id': gesture.id}), 201


@app.route('/api/gestures/<int:gesture_id>', methods=['DELETE'])
@login_required
def delete_gesture(gesture_id):
    """Delete a gesture"""
    user_id = session['user_id']
    gesture = GestureRecord.query.filter_by(id=gesture_id, user_id=user_id).first()
    
    if not gesture:
        return jsonify({'error': 'Gesture not found'}), 404
    
    db.session.delete(gesture)
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """Get user settings"""
    user_id = session['user_id']
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    return jsonify(settings.to_dict() if settings else {})


@app.route('/api/settings', methods=['PUT'])
@login_required
def update_settings():
    """Update user settings"""
    user_id = session['user_id']
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.session.add(settings)
    
    data = request.get_json()
    if 'default_effect' in data:
        settings.default_effect = data['default_effect']
    if 'enable_shape_detection' in data:
        settings.enable_shape_detection = data['enable_shape_detection']
    if 'enable_gesture_recording' in data:
        settings.enable_gesture_recording = data['enable_gesture_recording']
    if 'gesture_sensitivity' in data:
        settings.gesture_sensitivity = data['gesture_sensitivity']
    if 'theme' in data:
        settings.theme = data['theme']
    
    db.session.commit()
    return jsonify({'success': True, 'settings': settings.to_dict()})


@app.route('/api/launch-app', methods=['POST'])
@login_required
def launch_app():
    """Launch the gesture control app"""
    try:
        import subprocess
        import os
        import platform
        import sys
        
        # Get the path to app.py in parent directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        app_path = os.path.join(parent_dir, 'app.py')
        
        # Verify app.py exists
        if not os.path.exists(app_path):
            return jsonify({
                'success': False,
                'error': f'Gesture app not found at {app_path}'
            }), 404
        
        # Get venv Python executable (more reliable)
        venv_python = os.path.join(parent_dir, 'venv', 'Scripts', 'python.exe')
        if not os.path.exists(venv_python):
            venv_python = sys.executable
        
        # Launch with CREATE_NEW_CONSOLE on Windows
        try:
            subprocess.Popen(
                [venv_python, app_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=parent_dir
            )
        except Exception as e_subprocess:
            # Fallback without console flags
            subprocess.Popen([venv_python, app_path], cwd=parent_dir)
        
        print(f'[LAUNCH] Started gesture app with: {venv_python} {app_path}')
        
        return jsonify({
            'success': True,
            'message': 'Gesture app launched successfully!'
        }), 200
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f'[ERROR] Failed to launch gesture app:\n{error_msg}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============== ERROR HANDLERS ==============

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500


# ============== INITIALIZATION ==============

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Run Flask development server
    app.run(debug=True, host='127.0.0.1', port=5000)
