#!/usr/bin/env python3
"""
Password Reset Utility for AI Dropshipping ERP
Securely change admin password with bcrypt hashing
"""

import sqlite3
import getpass
import sys
import os
from werkzeug.security import generate_password_hash

# ============================================================================
# CRITICAL: Use absolute path for DB (same as app.py)
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'dropship.db')

print(f"[CHANGE_PASSWORD] ========================================")
print(f"[CHANGE_PASSWORD] Script: {__file__}")
print(f"[CHANGE_PASSWORD] Base directory: {BASE_DIR}")
print(f"[CHANGE_PASSWORD] Database path (ABSOLUTE): {DB_PATH}")
print(f"[CHANGE_PASSWORD] Database exists: {os.path.exists(DB_PATH)}")
print(f"[CHANGE_PASSWORD] ========================================")

# Verify DB path is absolute
if not os.path.isabs(DB_PATH):
    raise RuntimeError(f"CRITICAL: DB_PATH must be absolute! Got: {DB_PATH}")

def change_password():
    """Change admin password securely"""
    
    print("=" * 50)
    print("AI Dropshipping ERP - Password Reset Utility")
    print("=" * 50)
    print()
    
    # Check if database exists
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify admin user exists
        cursor.execute('SELECT id, username FROM users WHERE username = ?', ('admin',))
        user = cursor.fetchone()
        
        if not user:
            print("❌ Error: Admin user not found in database!")
            print("   Please run init_db.py first to initialize the database.")
            conn.close()
            sys.exit(1)
        
        print(f"✅ Found user: {user[1]} (ID: {user[0]})")
        print()
        
    except sqlite3.OperationalError as e:
        print(f"❌ Database error: {e}")
        print(f"   Make sure {DB_PATH} exists and is accessible.")
        sys.exit(1)
    
    # Get new password
    print("Enter new password for admin account:")
    print("(Password must be at least 8 characters)")
    print()
    
    while True:
        new_password = getpass.getpass("New password: ")
        
        if len(new_password) < 8:
            print("❌ Password too short! Must be at least 8 characters.")
            print()
            continue
        
        confirm_password = getpass.getpass("Confirm password: ")
        
        if new_password != confirm_password:
            print("❌ Passwords do not match! Please try again.")
            print()
            continue
        
        break
    
    # Hash password using bcrypt (compatible with app.py)
    print()
    print("🔐 Hashing password with bcrypt...")
    password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    
    # Update database
    try:
        cursor.execute(
            'UPDATE users SET password_hash = ? WHERE username = ?',
            (password_hash, 'admin')
        )
        conn.commit()
        
        # Verify update
        cursor.execute('SELECT id FROM users WHERE username = ? AND password_hash = ?', 
                      ('admin', password_hash))
        if cursor.fetchone():
            print("✅ Password updated successfully!")
            print()
            print("=" * 50)
            print("You can now login with:")
            print("  Username: admin")
            print("  Password: [your new password]")
            print("=" * 50)
        else:
            print("❌ Failed to verify password update!")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Failed to update password: {e}")
        conn.rollback()
        sys.exit(1)
    
    finally:
        conn.close()

if __name__ == '__main__':
    try:
        change_password()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
