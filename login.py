"""SpeakWise AI — Authentication & Session Management Module.

Provides user registration, login, session history, and account deletion
backed by the MySQL database (users, sessions, takes) with full step-by-step
'Back' navigation at every stage.
"""

import json
import re
import time

import bcrypt
import mysql.connector

from speakwise_database import get_connection, initialize_database


# ============================================================
# PASSWORD UTILITIES
# ============================================================

def hash_password(password):
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password, password_hash):
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"), password_hash.encode("utf-8")
    )


# ============================================================
# VALIDATION HELPERS
# ============================================================

def _validate_name(name):
    """Validate user name: 2-100 chars."""
    if not name or len(name.strip()) < 2:
        return "Name must be at least 2 characters."
    if len(name) > 100:
        return "Name must be at most 100 characters."
    return None


def _validate_email(email):
    """Validate email format."""
    if not email:
        return "Email cannot be empty."
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return "Please enter a valid email address."
    return None


def _validate_password(password):
    """Validate password: minimum 6 characters."""
    if not password or len(password) < 6:
        return "Password must be at least 6 characters."
    return None


# ============================================================
# USER REGISTRATION WITH STEP-BY-STEP BACK SUPPORT
# ============================================================

def register():
    """Register a new user account in MySQL with step-by-step back navigation.

    Prompts for Name, Email, Password, and Confirmation.
    Type 'b' or 'back' at any step to return to the previous step.

    Returns:
        True if registration was successful, False if cancelled.
    """

    print("\n" + "=" * 46)
    print("           CREATE NEW ACCOUNT")
    print("=" * 46)
    print("  (Type 'b' or 'back' at any step to go back)\n")

    step = 1
    name = ""
    email = ""
    password = ""

    while True:
        if step == 1:
            # --- Step 1: Full Name ---
            val = input("  Enter full name  : ").strip()
            if val.lower() in ("b", "back"):
                print("\n  Registration cancelled. Returning to main menu...\n")
                return False

            error = _validate_name(val)
            if error:
                print(f"  [-] {error}\n")
                continue

            name = val
            step = 2

        elif step == 2:
            # --- Step 2: Email ---
            val = input("  Enter email      : ").strip()
            if val.lower() in ("b", "back"):
                print("  <- Going back to Name...\n")
                step = 1
                continue

            error = _validate_email(val)
            if error:
                print(f"  [-] {error}\n")
                continue

            # Pre-check if email already exists in MySQL
            db = None
            cursor = None
            try:
                db = get_connection()
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    "SELECT user_id FROM users WHERE LOWER(TRIM(email)) = %s",
                    (val.lower(),),
                )
                if cursor.fetchone():
                    print("\n  [-] Email is already registered in MySQL. Please log in instead or use another email.\n")
                    continue
            except mysql.connector.Error as err:
                print(f"\n  [-] Database check error: {err}\n")
            finally:
                if cursor:
                    cursor.close()
                if db:
                    db.close()

            email = val.lower()
            step = 3

        elif step == 3:
            # --- Step 3: Password ---
            val = input("  Enter password   : ").strip()
            if val.lower() in ("b", "back"):
                print("  <- Going back to Email...\n")
                step = 2
                continue

            error = _validate_password(val)
            if error:
                print(f"  [-] {error}\n")
                continue

            password = val
            step = 4

        elif step == 4:
            # --- Step 4: Confirm Password ---
            confirm = input("  Confirm password : ").strip()
            if confirm.lower() in ("b", "back"):
                print("  <- Going back to Password...\n")
                step = 3
                continue

            if password != confirm:
                print("  [-] Passwords do not match. Try again or type 'b' to go back.\n")
                continue

            # --- Store in MySQL database ---
            db = None
            cursor = None
            try:
                db = get_connection()
                cursor = db.cursor(dictionary=True)

                pw_hash = hash_password(password)

                cursor.execute(
                    "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, pw_hash),
                )

                db.commit()

                print("\n  [+] Account created and permanently saved to MySQL database!")
                print(f"  Welcome, {name}! You can now log in.\n")
                return True

            except mysql.connector.Error as error:
                if getattr(error, "errno", None) == 1062:
                    print("\n  [-] Email is already registered in MySQL. Please log in instead.\n")
                else:
                    print(f"\n  [-] Registration failed in MySQL: {error}\n")
                return False
            finally:
                if cursor:
                    cursor.close()
                if db:
                    db.close()


# ============================================================
# USER LOGIN WITH STEP-BY-STEP BACK SUPPORT
# ============================================================

def login():
    """Prompt the user to log in with Email (or Name) and password from MySQL.

    Supports typing 'b' or 'back' at any step to return to the previous step
    or cancel back to the welcome menu.

    Returns:
        dict {user_id, name, email} on success, or None on cancel/failure.
    """

    print("\n" + "=" * 46)
    print("                 LOGIN")
    print("=" * 46)
    print("  (Type 'b' or 'back' at any prompt to go back)\n")

    step = 1
    login_input = ""
    password = ""

    while True:
        if step == 1:
            # --- Step 1: Email or Name ---
            raw_input = input("  Email or Name : ").strip()
            if raw_input.lower() in ("b", "back"):
                print("\n  Returning to main menu...\n")
                return None

            if not raw_input:
                print("  [-] Email/Name cannot be empty.\n")
                continue

            login_input = raw_input
            step = 2

        elif step == 2:
            # --- Step 2: Password ---
            raw_pw = input("  Password      : ").strip()
            if raw_pw.lower() in ("b", "back"):
                print("  <- Going back to Email/Name...\n")
                step = 1
                continue

            if not raw_pw:
                print("  [-] Password cannot be empty.\n")
                continue

            password = raw_pw

            # Authenticate against MySQL
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
                    """,
                    (login_input, login_input),
                )
                user = cursor.fetchone()

                if not user:
                    print(f"\n  [-] No user found matching '{login_input}' in MySQL.")
                    print("  Please check the email/name or type 'b' to go back.\n")
                    step = 1
                    continue

                if verify_password(password, user["password"]):
                    print(f"\n  [+] Login successful! Welcome back, {user['name']}!\n")
                    return {
                        "user_id": user["user_id"],
                        "name": user["name"],
                        "email": user["email"],
                    }

                print("\n  [-] Incorrect password. Please try again or type 'b' to go back.\n")
                # Stay at step 2 to allow re-entering password or typing 'b' to change username

            except mysql.connector.Error as error:
                print(f"\n  [-] MySQL error during login: {error}\n")
                return None
            finally:
                if cursor:
                    cursor.close()
                if db:
                    db.close()


# ============================================================
# SESSION & TAKE STORAGE
# ============================================================

def save_session(user_id, category, topic_name, speaking_time, audio_path, video_path, transcription, report):
    """Save a completed speech session and its take details to MySQL.

    Inserts into:
      1. `sessions` (user_id, category, topic_name, speaking_time)
      2. `takes` (session_id, audio_path, video_path, transcription, report)

    Args:
        user_id: The ID of the logged-in user.
        category: Speech category (e.g., 'Practice', 'AI Topic', etc.)
        topic_name: The speech topic title.
        speaking_time: Duration of speaking in seconds.
        audio_path: File path of the recorded audio (.wav).
        video_path: File path of the recorded video (.avi).
        transcription: Full transcribed text string.
        report: Detailed report string or JSON summary.
    """

    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor()

        # 1. Insert into sessions table
        cursor.execute(
            """
            INSERT INTO sessions (user_id, category, topic_name, speaking_time) 
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, category or "General Practice", topic_name or "Untitled Topic", int(speaking_time or 60)),
        )

        session_id = cursor.lastrowid

        # Format report as string if it is a dict
        report_str = json.dumps(report, indent=2) if isinstance(report, dict) else str(report or "")

        # 2. Insert into takes table
        cursor.execute(
            """
            INSERT INTO takes (session_id, audio_path, video_path, transcription, report) 
            VALUES (%s, %s, %s, %s, %s)
            """,
            (session_id, audio_path or "", video_path or "", transcription or "", report_str),
        )

        db.commit()
        print(f"  [+] Session #{session_id} and take committed to MySQL.")

    except mysql.connector.Error as error:
        print(f"  [!] Could not save session to MySQL: {error}")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def view_my_sessions(user):
    """Display the logged-in user's past speech sessions and takes from MySQL."""

    print("\n" + "=" * 60)
    print("             MY SESSION HISTORY (From MySQL)")
    print("=" * 60)

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
            (user["user_id"],),
        )
        rows = cursor.fetchall()

        if not rows:
            print("\n  No sessions found in MySQL. Start a speech practice to begin!\n")
            input("  Press ENTER to return to menu...")
            return

        for i, row in enumerate(rows, 1):
            date_str = row["created_at"].strftime("%Y-%m-%d %H:%M") if row.get("created_at") else "N/A"
            category = row.get("category") or "General"
            topic = row.get("topic_name") or "Untitled"
            speaking_time = row.get("speaking_time") or 60

            print(f"\n  Session #{i} (ID: {row['session_id']}) | {date_str}")
            print(f"  Category      : {category}")
            print(f"  Topic         : {topic}")
            print(f"  Speaking Time : {speaking_time} seconds")

            trans = (row.get("transcription") or "").strip()
            if trans:
                preview = trans[:100] + ("..." if len(trans) > 100 else "")
                print(f"  Transcript    : \"{preview}\"")

            report_raw = row.get("report")
            if report_raw:
                try:
                    rep_data = json.loads(report_raw) if isinstance(report_raw, str) and report_raw.startswith("{") else None
                    if rep_data and "overall" in rep_data:
                        print(f"  Overall Score : {rep_data.get('overall')}/10")
                    flaws = rep_data.get("what_went_wrong", []) if rep_data else []
                    if flaws and not (len(flaws) == 1 and flaws[0].startswith("No major")):
                        print("  What Went Wrong:")
                        for flaw in flaws[:2]:
                            print(f"    - {flaw}")
                except Exception:
                    pass

            print("  " + "-" * 50)

        print()
        input("  Press ENTER to return to menu...")

    except mysql.connector.Error as error:
        print(f"\n  [-] Could not load sessions from MySQL: {error}\n")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ============================================================
# ACCOUNT DELETION WITH STEP-BY-STEP BACK SUPPORT
# ============================================================

def delete_account(user):
    """Permanently delete the user's account and all associated data from MySQL.

    Prompts for password verification and explicit user re-confirmation.
    Type 'b' or 'back' at any prompt to cancel and go back.

    Returns:
        bool: True if account was deleted, False if cancelled or failed.
    """

    print("\n" + "=" * 50)
    print("           PERMANENT ACCOUNT DELETION")
    print("=" * 50)
    print("\n  WARNING: This will permanently delete your account,")
    print("  all past speech sessions, takes, and evaluations from MySQL.")
    print("  This action CANNOT be undone.\n")
    print("  (Type 'b' or 'back' at any prompt to cancel)\n")

    # Step 1: Initial confirmation
    confirm_step1 = input("  Are you sure you want to delete your account? (yes/no): ").strip().lower()
    if confirm_step1 in ("b", "back", "no", "n"):
        print("\n  Account deletion cancelled. Returning to menu...\n")
        return False

    if confirm_step1 not in ("yes", "y"):
        print("\n  [-] Invalid response. Account deletion cancelled.\n")
        return False

    # Step 2: Password verification
    password = input("  Enter your account password to verify: ").strip()
    if password.lower() in ("b", "back"):
        print("\n  Account deletion cancelled. Returning to menu...\n")
        return False

    if not password:
        print("\n  [-] Password cannot be empty. Deletion cancelled.\n")
        return False

    db = None
    cursor = None
    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT user_id, password FROM users WHERE user_id = %s",
            (user["user_id"],),
        )
        user_row = cursor.fetchone()

        if not user_row or not verify_password(password, user_row["password"]):
            print("\n  [-] Incorrect password. Account deletion cancelled.\n")
            return False

        # Step 3: Explicit re-confirmation
        print("\n  Final Confirmation:")
        confirm_step3 = input("  Type 'DELETE' to confirm permanent deletion: ").strip()
        if confirm_step3.lower() in ("b", "back"):
            print("\n  Account deletion cancelled. Returning to menu...\n")
            return False

        if confirm_step3 != "DELETE":
            print("\n  [-] Confirmation mismatch ('DELETE' was not entered). Deletion cancelled.\n")
            return False

        # Step 4: Execute deletion in MySQL (Cascades to sessions and takes)
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user["user_id"],))
        db.commit()

        print(f"\n  [+] Account for '{user['name']}' ({user['email']}) has been permanently deleted from MySQL.\n")
        return True

    except mysql.connector.Error as error:
        print(f"\n  [-] MySQL error during account deletion: {error}\n")
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ============================================================
# AUTHENTICATION & USER FLOW
# ============================================================

def authenticate():
    """Main authentication gate.

    Initializes MySQL database tables, then presents login/register options.

    Returns:
        dict with user info on success, or None to exit.
    """

    try:
        initialize_database()
    except Exception as e:
        print(f"\n  [-] Database initialization failed: {e}")
        print("  Please verify your MySQL service and settings in .env\n")
        return None

    while True:
        print("\n" + "=" * 46)
        print("           SPEAKWISE AI — WELCOME")
        print("=" * 46)
        print()
        print("  Do you have an account?")
        print()
        print("  1. Yes — Log in")
        print("  2. No  — Create a new account")
        print("  3. Exit")
        print()

        choice = input("  Select option (1-3): ").strip()

        if choice == "1":
            user = login()
            if user:
                return user

        elif choice == "2":
            if register():
                print("  Please log in with your new account.\n")
                time.sleep(1)
                user = login()
                if user:
                    return user

        elif choice in ("3", "exit", "e", "q", "quit"):
            print("\n  Goodbye!\n")
            return None

        else:
            print("  [-] Invalid option. Please try again.")


def user_menu(user):
    """Post-login menu for the authenticated user.

    Returns:
        str — 'speech' to start practice, 'logout' to log out, 'deleted' if deleted.
    """

    while True:
        print("\n" + "=" * 46)
        print(f"  Welcome, {user['name']}!")
        print("=" * 46)
        print()
        print("  1. Start Speech Practice")
        print("  2. View My Past Sessions")
        print("  3. Logout")
        print("  4. Delete Account Permanently")
        print()

        choice = input("  Select option (1-4): ").strip()

        if choice == "1":
            return "speech"
        elif choice == "2":
            view_my_sessions(user)
        elif choice == "3":
            return "logout"
        elif choice == "4":
            if delete_account(user):
                return "deleted"
        else:
            print("  [-] Invalid option. Please try again.")
