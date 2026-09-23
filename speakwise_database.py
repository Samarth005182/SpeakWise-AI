"""SpeakWise AI — Centralized MySQL Database Layer & Real-Time CRUD Operations.

Handles automatic database/table creation and dynamic real-time operations
for users, sessions, and speech practice takes.
"""

import json
import os
import bcrypt
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def ensure_database_exists():
    """Connect to MySQL server and ensure the database exists with utf8mb4 charset."""
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "samarth597")
    db_name = os.getenv("DB_NAME", "speakwise")

    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            charset="utf8mb4",
            autocommit=True,
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    except Exception as e:
        print(f"[DB Auto-Create Warning] {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_connection():
    """Return a real-time connection to the SpeakWise MySQL database with autocommit enabled."""
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "samarth597")
    db_name = os.getenv("DB_NAME", "speakwise")

    try:
        db = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db_name,
            charset="utf8mb4",
            autocommit=True,
        )
        return db
    except mysql.connector.Error as err:
        # If database doesn't exist, create it and reconnect
        if getattr(err, "errno", None) == 1049:
            ensure_database_exists()
            db = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=db_name,
                charset="utf8mb4",
                autocommit=True,
            )
            return db
        raise err


def setup_tables():
    """Create the required tables (users, sessions, takes) if they do not exist."""
    ensure_database_exists()
    db = get_connection()
    cursor = db.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL,
                category VARCHAR(100) NOT NULL,
                topic_name VARCHAR(255) NOT NULL,
                speaking_time INT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS takes (
                take_id INT PRIMARY KEY AUTO_INCREMENT,
                session_id INT NOT NULL,
                audio_path VARCHAR(500),
                video_path VARCHAR(500),
                transcription TEXT,
                report TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id)
                    REFERENCES sessions(session_id)
                    ON DELETE CASCADE
            ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci
        """)

        db.commit()
    finally:
        cursor.close()
        db.close()


def seed_admin():
    """Seed the pre-defined admin account if it does not already exist."""
    admin_name = (os.getenv("ADMIN_NAME") or "Samarth").strip()
    admin_email = (os.getenv("ADMIN_EMAIL") or "admin123@gmail.com").strip()
    admin_password = (os.getenv("ADMIN_PASSWORD") or "admin123").strip()

    if not all([admin_name, admin_email, admin_password]):
        return

    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor(buffered=True)

        cursor.execute(
            "SELECT user_id FROM users WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))",
            (admin_email,),
        )
        if cursor.fetchone():
            return

        password_hash = bcrypt.hashpw(
            admin_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (admin_name, admin_email.lower(), password_hash),
        )
        db.commit()
    except mysql.connector.Error as error:
        if getattr(error, "errno", None) == 1062:
            return
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ============================================================
# REAL-TIME DYNAMIC USER CRUD OPERATIONS
# ============================================================

def register_user(name, email, password):
    """Dynamically register a new user in MySQL in real-time.

    Args:
        name: Full name of the user
        email: Email address (unique)
        password: Raw password (will be hashed with bcrypt)

    Returns:
        tuple: (success: bool, result_or_error: dict|str)
    """
    clean_name = (name or "").strip()
    clean_email = (email or "").strip().lower()
    clean_password = (password or "").strip()

    if not clean_name or len(clean_name) < 2:
        return False, "Name must be at least 2 characters."
    if not clean_email or "@" not in clean_email or "." not in clean_email:
        return False, "Please enter a valid email address."
    if not clean_password or len(clean_password) < 6:
        return False, "Password must be at least 6 characters."

    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)

        # Check for existing email in real-time
        cursor.execute(
            "SELECT user_id FROM users WHERE LOWER(TRIM(email)) = %s",
            (clean_email,),
        )
        if cursor.fetchone():
            return False, "Email is already registered. Please log in instead."

        pw_hash = bcrypt.hashpw(
            clean_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (clean_name, clean_email, pw_hash),
        )
        db.commit()
        new_id = cursor.lastrowid

        user_data = {
            "user_id": new_id,
            "name": clean_name,
            "email": clean_email,
        }
        return True, user_data

    except mysql.connector.Error as err:
        if getattr(err, "errno", None) == 1062:
            return False, "Email is already registered. Please log in instead."
        return False, f"Database error: {err}"
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def authenticate_user(identifier, password):
    """Dynamically verify credentials against MySQL in real-time.

    Args:
        identifier: Email address or Name
        password: Raw password string

    Returns:
        tuple: (success: bool, user_dict_or_error_msg: dict|str)
    """
    clean_id = (identifier or "").strip()
    clean_pw = (password or "").strip()

    if not clean_id or not clean_pw:
        return False, "Identifier and password cannot be empty."

    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT user_id, name, email, password 
            FROM users 
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s)) 
               OR LOWER(TRIM(name)) = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (clean_id, clean_id),
        )
        user = cursor.fetchone()

        if not user:
            return False, f"No account found matching '{clean_id}'."

        if bcrypt.checkpw(clean_pw.encode("utf-8"), user["password"].encode("utf-8")):
            return True, {
                "user_id": user["user_id"],
                "name": user["name"],
                "email": user["email"],
            }
        else:
            return False, "Incorrect password. Please try again."

    except mysql.connector.Error as err:
        return False, f"Database error: {err}"
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_all_users():
    """Retrieve all users from the MySQL database with their session counts in real-time.

    Returns:
        list of dicts: [{"user_id", "name", "email", "session_count"}]
    """
    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                u.user_id, 
                u.name, 
                u.email,
                COUNT(s.session_id) AS session_count
            FROM users u
            LEFT JOIN sessions s ON u.user_id = s.user_id
            GROUP BY u.user_id, u.name, u.email
            ORDER BY u.user_id ASC
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"[DB get_all_users error] {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_user_by_id(user_id):
    """Retrieve user details by user_id in real-time."""
    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, name, email FROM users WHERE user_id = %s",
            (user_id,),
        )
        return cursor.fetchone()
    except Exception:
        return None
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def delete_user(user_id):
    """Permanently delete user and all cascade data (sessions, takes) from MySQL in real-time."""
    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        db.commit()
        return True, "User account deleted successfully."
    except Exception as e:
        return False, str(e)
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ============================================================
# REAL-TIME SESSIONS & TAKES CRUD
# ============================================================

def save_speech_session(user_id, category, topic_name, speaking_time, audio_path, video_path, transcription, report):
    """Save a completed speech session and take directly to MySQL in real-time.

    Inserts into:
      1. `sessions`
      2. `takes`
    """
    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO sessions (user_id, category, topic_name, speaking_time) 
            VALUES (%s, %s, %s, %s)
            """,
            (
                user_id,
                category or "General Practice",
                topic_name or "Untitled Topic",
                int(speaking_time or 60),
            ),
        )
        session_id = cursor.lastrowid

        report_str = (
            json.dumps(report, indent=2)
            if isinstance(report, dict)
            else str(report or "")
        )

        cursor.execute(
            """
            INSERT INTO takes (session_id, audio_path, video_path, transcription, report) 
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                session_id,
                audio_path or "",
                video_path or "",
                transcription or "",
                report_str,
            ),
        )
        db.commit()
        return session_id
    except mysql.connector.Error as err:
        print(f"[DB Save Error] {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_user_sessions(user_id):
    """Retrieve all sessions and takes for a user ordered by date descending in real-time."""
    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT 
                s.session_id,
                s.category,
                s.topic_name,
                s.speaking_time,
                s.created_at,
                t.take_id,
                t.audio_path,
                t.video_path,
                t.transcription,
                t.report
            FROM sessions s
            LEFT JOIN takes t ON s.session_id = t.session_id
            WHERE s.user_id = %s
            ORDER BY s.created_at DESC
            """,
            (user_id,),
        )
        return cursor.fetchall()
    except Exception as e:
        print(f"[DB get_user_sessions error] {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_db_stats():
    """Return summary counts of users, sessions, and takes in MySQL in real-time."""
    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total_users FROM users")
        users_count = cursor.fetchone()["total_users"]
        cursor.execute("SELECT COUNT(*) AS total_sessions FROM sessions")
        sessions_count = cursor.fetchone()["total_sessions"]
        cursor.execute("SELECT COUNT(*) AS total_takes FROM takes")
        takes_count = cursor.fetchone()["total_takes"]
        cursor.close()
        db.close()
        return {"users": users_count, "sessions": sessions_count, "takes": takes_count}
    except Exception:
        return None


def initialize_database():
    """Set up database, tables, and seed admin — call once at app startup."""
    setup_tables()
    seed_admin()


if __name__ == "__main__":
    print("=" * 60)
    print("      SPEAKWISE AI — MYSQL DATABASE MANAGER")
    print("=" * 60)

    try:
        initialize_database()
        print(" [+] Database and Tables (users, sessions, takes) verified.")

        stats = get_db_stats()
        if stats:
            print(f" [+] Total Registered Users : {stats['users']}")
            print(f" [+] Total Sessions Recorded : {stats['sessions']}")
            print(f" [+] Total Takes Stored      : {stats['takes']}")

        users = get_all_users()
        print("\n" + "-" * 60)
        print(f"{'ID':<6} | {'Name':<20} | {'Email':<28} | {'Sessions':<8}")
        print("-" * 60)
        for u in users:
            print(f"{u['user_id']:<6} | {u['name']:<20} | {u['email']:<28} | {u['session_count']:<8}")
        print("-" * 60 + "\n")

    except Exception as error:
        print(f" [-] Database error: {error}")