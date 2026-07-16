"""
Script to create test users in the database
Run this once to populate test data
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app_web import app, db, User, UserSettings, GestureRecord
from datetime import datetime

def create_test_users():
    """Create test users for testing"""
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Check if test user already exists
        test_user = User.query.filter_by(username='testuser').first()
        if test_user:
            print("✓ Test user already exists!")
            print(f"  Username: testuser")
            print(f"  Password: password123")
            print(f"  Email: test@example.com")
            return
        
        # Create test user
        user = User(
            username='testuser',
            email='test@example.com',
            full_name='Test User',
            created_at=datetime.utcnow()
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()
        
        # Create user settings
        settings = UserSettings(
            user_id=user.id,
            default_effect='rainbow',
            enable_shape_detection=True,
            enable_gesture_recording=True,
            gesture_sensitivity=1.0,
            theme='light'
        )
        db.session.add(settings)
        
        # Create sample gesture records
        gesture1 = GestureRecord(
            user_id=user.id,
            gesture_name='Circle',
            gesture_data='{"type": "circle", "radius": 50}',
            description='Draw a circle with your hand'
        )
        
        gesture2 = GestureRecord(
            user_id=user.id,
            gesture_name='Wave',
            gesture_data='{"type": "wave", "direction": "left_to_right"}',
            description='Wave your hand from left to right'
        )
        
        db.session.add(gesture1)
        db.session.add(gesture2)
        
        db.session.commit()
        
        print("=" * 50)
        print("✅ TEST USER CREATED SUCCESSFULLY!")
        print("=" * 50)
        print()
        print("📝 LOGIN CREDENTIALS:")
        print(f"   Username: testuser")
        print(f"   Password: password123")
        print(f"   Email: test@example.com")
        print()
        print("📊 TEST DATA:")
        print(f"   Default Effect: rainbow")
        print(f"   Shape Detection: Enabled")
        print(f"   Gesture Recording: Enabled")
        print(f"   Saved Gestures: 2 (Circle, Wave)")
        print()
        print("🚀 READY TO TEST!")
        print("=" * 50)

if __name__ == '__main__':
    create_test_users()
