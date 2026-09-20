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
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "speakwise"),
    )

    return db


def setup_tables():
    """Create the required tables if they do not already exist."""

    db = get_connection()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE = InnoDB
    """)
    db.commit()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            topic VARCHAR(255),
            overall_score FLOAT,
            fluency_score FLOAT,
            pace_score FLOAT,
            pause_score FLOAT,
            eye_contact_score FLOAT,
            head_stability_score FLOAT,
            relevance_score FLOAT,
            total_words INT,
            total_fillers INT,
            session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE = InnoDB
    """)

    db.commit()
    cursor.close()
    db.close()


def seed_admin():
    """Seed the pre-defined admin account if it does not already exist.

    Admin credentials are read from environment variables so that
    they never appear in source code.
    """

    admin_name = os.getenv("ADMIN_NAME")
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not all([admin_name, admin_email, admin_password]):
        return

    db = get_connection()
    cursor = db.cursor()

    # Check if admin already exists
    cursor.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        return

    # Hash the admin password before storing
    password_hash = bcrypt.hashpw(
        admin_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    cursor.execute(
        "INSERT INTO users (username, email, password_hash, is_admin) "
        "VALUES (%s, %s, %s, %s)",
        (admin_name, admin_email, password_hash, True),
    )

    db.commit()
    cursor.close()
    db.close()


def initialize_database():
    """Set up tables and seed admin — call once at app startup."""
    setup_tables()
    seed_admin()


if __name__ == "__main__":

    try:

        db = get_connection()

        if db.is_connected():
            print("================================")
            print("Connected to SpeakWise database!")
            print("================================")

        db.close()

        setup_tables()
        print("Tables created successfully!")

        seed_admin()
        print("Admin account seeded!")

    except mysql.connector.Error as error:

        print("Database connection failed!")
        print("Error:", error)