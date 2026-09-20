import os

import bcrypt
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Return a connection to the SpeakWise MySQL database.

    Reads credentials from environment variables set in .env.
    """

    db = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "samarth597"),
        database=os.getenv("DB_NAME", "speakwise"),
        charset="utf8mb4",
    )

    return db


def setup_tables():
    """Create the required tables (users, sessions, takes) if they do not exist."""

    db = get_connection()
    cursor = db.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4
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
            ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4
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
            ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4
        """)

        db.commit()
    finally:
        cursor.close()
        db.close()


def seed_admin():
    """Seed the pre-defined admin account if it does not already exist."""

    admin_name = (os.getenv("ADMIN_NAME") or "").strip()
    admin_email = (os.getenv("ADMIN_EMAIL") or "").strip()
    admin_password = (os.getenv("ADMIN_PASSWORD") or "").strip()

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
        # If the admin already exists (errno 1062: Duplicate entry), ignore safely
        if getattr(error, "errno", None) == 1062:
            return
        raise error
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_db_stats():
    """Return summary counts of users, sessions, and takes in MySQL."""
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
    """Set up tables and seed admin — call once at app startup."""
    setup_tables()
    seed_admin()


if __name__ == "__main__":

    try:
        db = get_connection()
        if db.is_connected():
            print("================================")
            print("Connected to SpeakWise MySQL database!")
            print("================================")
        db.close()

        setup_tables()
        print("Tables (users, sessions, takes) verified successfully!")

        seed_admin()
        print("Admin account verified!")

        stats = get_db_stats()
        if stats:
            print(f"Database Stats: {stats['users']} users, {stats['sessions']} sessions, {stats['takes']} takes.")

    except mysql.connector.Error as error:
        print("Database connection failed!")
        print("Error:", error)