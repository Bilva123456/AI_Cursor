"""
Database Integration for Gesture App
Connects to web app's SQLite database to load user settings and save gestures
"""

import os
import sys
import sqlite3
from datetime import datetime

class GestureAppDatabase:
    """Handles integration with web app database"""
    
    def __init__(self, db_path=None):
        """Initialize database connection"""
        if db_path is None:
            # Default path: web_app/gesture_control.db
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'web_app', 'gesture_control.db')
        
        self.db_path = db_path
        self.user_id = None
        self.connected = False
        
        try:
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor = self.connection.cursor()
            self.connected = True
            print(f"✓ Database connected: {db_path}")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            self.connected = False
    
    def get_latest_user_id(self):
        """Get the ID of the most recently logged-in user"""
        try:
            if not self.connected:
                return None
            
            query = "SELECT id FROM users ORDER BY last_login DESC LIMIT 1"
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            
            if result:
                self.user_id = result[0]
                print(f"✓ Loaded user ID: {self.user_id}")
                return self.user_id
            
            return None
        except Exception as e:
            print(f"✗ Error getting user ID: {e}")
            return None
    
    def load_user_settings(self, user_id=None):
        """Load user settings from database"""
        try:
            if not self.connected:
                return None
            
            if user_id is None:
                user_id = self.get_latest_user_id()
            
            if user_id is None:
                print("✗ No user ID available")
                return None
            
            query = """
                SELECT 
                    default_effect, 
                    enable_shape_detection, 
                    enable_gesture_recording, 
                    gesture_sensitivity, 
                    theme
                FROM user_settings 
                WHERE user_id = ?
            """
            
            self.cursor.execute(query, (user_id,))
            result = self.cursor.fetchone()
            
            if result:
                settings = {
                    'effect': result[0] or 'normal',
                    'shape_detection': bool(result[1]),
                    'gesture_recording': bool(result[2]),
                    'sensitivity': result[3] or 1.0,
                    'theme': result[4] or 'light'
                }
                print(f"✓ Loaded user settings: {settings}")
                return settings
            
            print("✗ No settings found for user")
            return None
        except Exception as e:
            print(f"✗ Error loading settings: {e}")
            return None
    
    def save_gesture(self, gesture_name, gesture_data, description=''):
        """Save a recorded gesture to database"""
        try:
            if not self.connected or self.user_id is None:
                print("✗ Cannot save gesture: not connected or no user")
                return False
            
            query = """
                INSERT INTO gesture_records 
                (user_id, gesture_name, gesture_data, created_at, description)
                VALUES (?, ?, ?, ?, ?)
            """
            
            self.cursor.execute(query, (
                self.user_id,
                gesture_name,
                gesture_data,
                datetime.utcnow().isoformat(),
                description
            ))
            
            self.connection.commit()
            print(f"✓ Gesture saved: {gesture_name}")
            return True
        except Exception as e:
            print(f"✗ Error saving gesture: {e}")
            return False
    
    def get_user_gestures(self, user_id=None):
        """Get all gestures for a user"""
        try:
            if not self.connected:
                return []
            
            if user_id is None:
                user_id = self.get_latest_user_id()
            
            if user_id is None:
                return []
            
            query = """
                SELECT id, gesture_name, description, created_at
                FROM gesture_records
                WHERE user_id = ?
                ORDER BY created_at DESC
            """
            
            self.cursor.execute(query, (user_id,))
            results = self.cursor.fetchall()
            
            gestures = []
            for result in results:
                gestures.append({
                    'id': result[0],
                    'name': result[1],
                    'description': result[2],
                    'created_at': result[3]
                })
            
            print(f"✓ Loaded {len(gestures)} gestures")
            return gestures
        except Exception as e:
            print(f"✗ Error loading gestures: {e}")
            return []
    
    def update_user_last_login(self, user_id=None):
        """Update user's last login timestamp"""
        try:
            if not self.connected:
                return False
            
            if user_id is None:
                user_id = self.user_id
            
            if user_id is None:
                return False
            
            query = "UPDATE users SET last_login = ? WHERE id = ?"
            self.cursor.execute(query, (datetime.utcnow().isoformat(), user_id))
            self.connection.commit()
            
            print(f"✓ Updated last login for user {user_id}")
            return True
        except Exception as e:
            print(f"✗ Error updating last login: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        try:
            if self.connected:
                self.connection.close()
                self.connected = False
                print("✓ Database connection closed")
        except Exception as e:
            print(f"✗ Error closing database: {e}")


# Singleton instance
_db_instance = None

def get_database():
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = GestureAppDatabase()
    return _db_instance


# Example usage
if __name__ == '__main__':
    db = get_database()
    
    # Load latest user
    user_id = db.get_latest_user_id()
    if user_id:
        # Load their settings
        settings = db.load_user_settings(user_id)
        
        # Get their gestures
        gestures = db.get_user_gestures(user_id)
        
        # Update last login
        db.update_user_last_login(user_id)
    
    db.close()
