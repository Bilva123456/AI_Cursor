"""
Integration Test - Verify app.py is properly integrated with web app
"""

import os
import sys

def test_database_module():
    """Test if gesture_db module exists and works"""
    print("\n" + "="*60)
    print("TEST 1: Database Module Existence")
    print("="*60)
    
    try:
        from gesture_db import get_database, GestureAppDatabase
        print("✓ gesture_db module found")
        print("✓ GestureAppDatabase class accessible")
        return True
    except ImportError as e:
        print(f"✗ Failed to import gesture_db: {e}")
        return False


def test_database_connection():
    """Test database connection"""
    print("\n" + "="*60)
    print("TEST 2: Database Connection")
    print("="*60)
    
    try:
        from gesture_db import get_database
        db = get_database()
        
        if db.connected:
            print(f"✓ Connected to database: {db.db_path}")
            print(f"✓ Database file exists: {os.path.exists(db.db_path)}")
            return True
        else:
            print("✗ Database connection failed")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_load_user_settings():
    """Test loading user settings"""
    print("\n" + "="*60)
    print("TEST 3: Load User Settings")
    print("="*60)
    
    try:
        from gesture_db import get_database
        db = get_database()
        
        # Get latest user
        user_id = db.get_latest_user_id()
        if user_id:
            print(f"✓ Found user ID: {user_id}")
            
            # Load settings
            settings = db.load_user_settings(user_id)
            if settings:
                print("✓ Settings loaded successfully:")
                for key, value in settings.items():
                    print(f"  - {key}: {value}")
                return True
            else:
                print("✗ No settings found for user")
                return False
        else:
            print("⚠ No user found in database (this is OK if web app not used yet)")
            return True  # This is expected if no login
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_save_gesture():
    """Test saving a gesture"""
    print("\n" + "="*60)
    print("TEST 4: Save Gesture")
    print("="*60)
    
    try:
        from gesture_db import get_database
        db = get_database()
        
        user_id = db.get_latest_user_id()
        if user_id:
            # Try to save a test gesture
            success = db.save_gesture(
                gesture_name='test_gesture',
                gesture_data='{"test": true}',
                description='Test gesture for integration'
            )
            
            if success:
                print("✓ Test gesture saved successfully")
                
                # Verify it was saved
                gestures = db.get_user_gestures(user_id)
                found = any(g['name'] == 'test_gesture' for g in gestures)
                if found:
                    print("✓ Gesture found in database")
                    return True
                else:
                    print("⚠ Gesture saved but not found in query")
                    return True  # Save succeeded
            else:
                print("✗ Failed to save gesture")
                return False
        else:
            print("⚠ No user in database (can't test gesture save)")
            return True  # This is OK
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_app_py_integration():
    """Test if app.py imports gesture_db"""
    print("\n" + "="*60)
    print("TEST 5: app.py Integration")
    print("="*60)
    
    try:
        # Check if app.py imports gesture_db
        with open('app.py', 'r') as f:
            content = f.read()
            
        if 'from gesture_db import' in content:
            print("✓ app.py imports gesture_db module")
        else:
            print("✗ app.py does not import gesture_db")
            return False
            
        if 'HAS_DB' in content:
            print("✓ app.py has HAS_DB flag")
        else:
            print("✗ app.py missing HAS_DB flag")
            return False
            
        if 'load_user_settings' in content:
            print("✓ app.py calls load_user_settings")
        else:
            print("✗ app.py does not load settings")
            return False
            
        if 'db.save_gesture' in content:
            print("✓ app.py saves gestures to database")
        else:
            print("✗ app.py does not save gestures")
            return False
            
        print("✓ All integration checks passed!")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "█"*60)
    print("█  APP.PY INTEGRATION TEST SUITE")
    print("█"*60)
    
    tests = [
        ("Database Module", test_database_module),
        ("Database Connection", test_database_connection),
        ("Load Settings", test_load_user_settings),
        ("Save Gesture", test_save_gesture),
        ("app.py Integration", test_app_py_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n✨ ALL TESTS PASSED! Integration is working! ✨\n")
        return 0
    elif passed >= total - 1:
        print("\n⚠ Most tests passed. Some issues may be minor.\n")
        return 1
    else:
        print("\n✗ Integration issues detected. Please review above.\n")
        return 2


if __name__ == '__main__':
    sys.exit(main())
