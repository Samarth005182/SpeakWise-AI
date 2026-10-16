import json
import os
import bcrypt
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def ensure_database_exists():
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
    except Exception:
        pass
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_connection(db_name=None):
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "samarth597")
    target_db = os.getenv("DB_NAME", "speakwise") if db_name is None else db_name

    try:
        kwargs = {
            "host": host,
            "user": user,
            "password": password,
            "charset": "utf8mb4",
            "autocommit": True,
        }
        if target_db:
            kwargs["database"] = target_db

        db = mysql.connector.connect(**kwargs)
        return db
    except mysql.connector.Error as err:
        if getattr(err, "errno", None) == 1049 and target_db:
            ensure_database_exists()
            db = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=target_db,
                charset="utf8mb4",
                autocommit=True,
            )
            return db
        raise err


def setup_tables():
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
    admin_name = "Admin"
    admin_email = "admin@speakwise.ai"
    admin_password = "admin"

    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor(buffered=True)

        cursor.execute(
            "SELECT user_id FROM users WHERE LOWER(TRIM(email)) = %s OR LOWER(TRIM(name)) = 'admin'",
            (admin_email.lower(),),
        )
        row = cursor.fetchone()
        password_hash = bcrypt.hashpw(
            admin_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        if row:
            cursor.execute(
                "UPDATE users SET password = %s, name = %s WHERE user_id = %s",
                (password_hash, admin_name, row[0]),
            )
        else:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (admin_name, admin_email.lower(), password_hash),
            )
        db.commit()
    except Exception:
        pass
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()



def register_user(name, email, password):
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
    clean_id = (identifier or "").strip()
    clean_pw = (password or "").strip()

    if not clean_id or not clean_pw:
        return False, "Identifier and password cannot be empty."

    # Hidden admin login support: username "admin" and password "admin"
    if clean_id.lower() in ("admin", "admin@speakwise.ai") and clean_pw == "admin":
        seed_admin()
        admin_id = 1
        db = None
        cursor = None
        try:
            db = get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                "SELECT user_id, name, email FROM users WHERE LOWER(TRIM(email)) = 'admin@speakwise.ai' OR LOWER(TRIM(name)) = 'admin' LIMIT 1"
            )
            admin_user = cursor.fetchone()
            if admin_user:
                admin_id = admin_user["user_id"]
        except Exception:
            pass
        finally:
            if cursor:
                cursor.close()
            if db:
                db.close()

        return True, {
            "user_id": admin_id,
            "name": "Admin",
            "email": "admin@speakwise.ai",
            "role": "Administrator",
            "is_admin": True,
        }

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
            is_admin = (
                user["email"].lower() == "admin@speakwise.ai"
                or user["name"].lower() == "admin"
            )
            return True, {
                "user_id": user["user_id"],
                "name": user["name"],
                "email": user["email"],
                "role": "Administrator" if is_admin else "Student",
                "is_admin": is_admin,
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
    except Exception:
        return []
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_user_by_id(user_id):
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



def save_speech_session(user_id, category, topic_name, speaking_time, audio_path, video_path, transcription, report):
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
    except mysql.connector.Error:
        return None
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_user_sessions(user_id):
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
    except Exception:
        return []
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_db_stats():
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


def get_all_databases():
    """Retrieve list of all databases available on the MySQL server."""
    db = None
    cursor = None
    try:
        db = get_connection(db_name="")
        cursor = db.cursor()
        cursor.execute("SHOW DATABASES")
        dbs = [row[0] for row in cursor.fetchall()]
        if "speakwise" in dbs:
            dbs.remove("speakwise")
            dbs.insert(0, "speakwise")
        return dbs
    except Exception:
        return ["speakwise"]
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_database_tables(db_name="speakwise"):
    """Retrieve all table names inside a database."""
    db = None
    cursor = None
    try:
        db = get_connection(db_name=db_name)
        cursor = db.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        preferred = ["users", "sessions", "takes"]
        sorted_tables = []
        for p in preferred:
            if p in tables:
                sorted_tables.append(p)
        for t in tables:
            if t not in sorted_tables:
                sorted_tables.append(t)
        return sorted_tables
    except Exception:
        return ["users", "sessions", "takes"]
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_table_schema(table_name, db_name="speakwise"):
    """Retrieve table column schema definition (fields, types, keys)."""
    db = None
    cursor = None
    try:
        db = get_connection(db_name=db_name)
        cursor = db.cursor(dictionary=True)
        cursor.execute(f"DESCRIBE `{table_name}`")
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_table_data(table_name, db_name="speakwise", limit=300, search_query=None):
    """Retrieve column list and rows for a table with optional search filter."""
    db = None
    cursor = None
    try:
        db = get_connection(db_name=db_name)
        cursor = db.cursor(dictionary=True)

        cursor.execute(f"DESCRIBE `{table_name}`")
        columns = [row["Field"] for row in cursor.fetchall()]

        order_by = ""
        for col in ["user_id", "session_id", "take_id", "id", "created_at"]:
            if col in columns:
                order_by = f"ORDER BY `{col}` DESC"
                break

        query = f"SELECT * FROM `{table_name}` {order_by} LIMIT {int(limit)}"
        cursor.execute(query)
        rows = cursor.fetchall()

        if search_query and search_query.strip():
            sq = search_query.strip().lower()
            filtered = []
            for r in rows:
                match = False
                for val in r.values():
                    if val is not None and sq in str(val).lower():
                        match = True
                        break
                if match:
                    filtered.append(r)
            rows = filtered

        return columns, rows
    except Exception:
        return [], []
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def get_table_row_count(table_name, db_name="speakwise"):
    """Get total row count of a table."""
    db = None
    cursor = None
    try:
        db = get_connection(db_name=db_name)
        cursor = db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def delete_table_record(table_name, primary_key_col, primary_key_val, db_name="speakwise"):
    """Delete a record by primary key."""
    db = None
    cursor = None
    try:
        db = get_connection(db_name=db_name)
        cursor = db.cursor()
        cursor.execute(
            f"DELETE FROM `{table_name}` WHERE `{primary_key_col}` = %s",
            (primary_key_val,),
        )
        db.commit()
        return True, "Record deleted successfully."
    except Exception as e:
        return False, str(e)
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def initialize_database():
    setup_tables()
    seed_admin()


if __name__ == "__main__":
    try:
        initialize_database()
    except Exception:
        pass