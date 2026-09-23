"""SpeakWise AI — Authentication & Session Management Module.

Provides user registration, login, session history, and account deletion
backed dynamically and in real-time by MySQL database tables (users, sessions, takes)
with full step-by-step 'Back' navigation at every stage.
"""

import time

from speakwise_database import (
    authenticate_user,
    delete_user,
    get_connection,
    get_user_sessions,
    initialize_database,
    register_user,
    save_speech_session,
)


def hash_password(password):
    """Hash a plaintext password using bcrypt."""
    import bcrypt

    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password, password_hash):
    """Verify a plaintext password against a bcrypt hash."""
    import bcrypt

    return bcrypt.checkpw(
        password.encode("utf-8"), password_hash.encode("utf-8")
    )


# ============================================================
# USER REGISTRATION WITH STEP-BY-STEP BACK SUPPORT
# ============================================================

def register():
    """Register a new user account dynamically into MySQL in real-time.

    Prompts for Name, Email, Password, and Confirmation.
    Type 'b' or 'back' at any step to return to the previous step.

    Returns:
        dict with user data on success, or None if cancelled/failed.
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
            val = input("  Enter full name  : ").strip()
            if val.lower() in ("b", "back"):
                print("\n  Registration cancelled. Returning to main menu...\n")
                return None

            if not val or len(val) < 2:
                print("  [-] Name must be at least 2 characters.\n")
                continue

            name = val
            step = 2

        elif step == 2:
            val = input("  Enter email      : ").strip().lower()
            if val.lower() in ("b", "back"):
                print("  <- Going back to Name...\n")
                step = 1
                continue

            if not val or "@" not in val or "." not in val:
                print("  [-] Please enter a valid email address.\n")
                continue

            email = val
            step = 3

        elif step == 3:
            val = input("  Enter password   : ").strip()
            if val.lower() in ("b", "back"):
                print("  <- Going back to Email...\n")
                step = 2
                continue

            if not val or len(val) < 6:
                print("  [-] Password must be at least 6 characters.\n")
                continue

            password = val
            step = 4

        elif step == 4:
            confirm = input("  Confirm password : ").strip()
            if confirm.lower() in ("b", "back"):
                print("  <- Going back to Password...\n")
                step = 3
                continue

            if password != confirm:
                print("  [-] Passwords do not match. Try again or type 'b' to go back.\n")
                continue

            # Real-time dynamic insertion into MySQL
            success, result = register_user(name, email, password)
            if success:
                print("\n  [+] Account dynamically created and committed in real-time to MySQL!")
                print(f"  Welcome, {name} (ID: #{result['user_id']})!\n")
                return result
            else:
                print(f"\n  [-] {result}\n")
                return None


# ============================================================
# USER LOGIN WITH STEP-BY-STEP BACK SUPPORT
# ============================================================

def login():
    """Prompt the user to log in with Email (or Name) and password from MySQL in real-time.

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
            raw_pw = input("  Password      : ").strip()
            if raw_pw.lower() in ("b", "back"):
                print("  <- Going back to Email/Name...\n")
                step = 1
                continue

            if not raw_pw:
                print("  [-] Password cannot be empty.\n")
                continue

            password = raw_pw

            # Authenticate dynamically against MySQL
            success, result = authenticate_user(login_input, password)
            if success:
                print(f"\n  [+] Login successful! Welcome back, {result['name']}!\n")
                return result
            else:
                print(f"\n  [-] {result}\n")
                step = 1


# ============================================================
# SESSION & TAKE STORAGE
# ============================================================

def save_session(user_id, category, topic_name, speaking_time, audio_path, video_path, transcription, report):
    """Save a completed speech session and take to MySQL in real-time."""
    session_id = save_speech_session(
        user_id=user_id,
        category=category,
        topic_name=topic_name,
        speaking_time=speaking_time,
        audio_path=audio_path,
        video_path=video_path,
        transcription=transcription,
        report=report,
    )
    if session_id:
        print(f"  [+] Session #{session_id} and take committed to MySQL in real-time.")
    return session_id


def view_my_sessions(user):
    """Display the logged-in user's past speech sessions and takes dynamically from MySQL."""

    print("\n" + "=" * 60)
    print(f"       SESSION HISTORY FOR {user['name'].upper()} (From MySQL)")
    print("=" * 60)

    rows = get_user_sessions(user["user_id"])
    if not rows:
        print("\n  No sessions found in MySQL. Start a speech practice to begin!\n")
        input("  Press ENTER to return to menu...")
        return

    import json

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


# ============================================================
# ACCOUNT DELETION WITH STEP-BY-STEP BACK SUPPORT
# ============================================================

def delete_account(user):
    """Permanently delete user account dynamically from MySQL in real-time."""

    print("\n" + "=" * 50)
    print("           PERMANENT ACCOUNT DELETION")
    print("=" * 50)
    print("\n  WARNING: This will permanently delete your account,")
    print("  all past speech sessions, takes, and evaluations from MySQL.")
    print("  This action CANNOT be undone.\n")
    print("  (Type 'b' or 'back' at any prompt to cancel)\n")

    confirm_step1 = input("  Are you sure you want to delete your account? (yes/no): ").strip().lower()
    if confirm_step1 in ("b", "back", "no", "n"):
        print("\n  Account deletion cancelled. Returning to menu...\n")
        return False

    if confirm_step1 not in ("yes", "y"):
        print("\n  [-] Invalid response. Account deletion cancelled.\n")
        return False

    password = input("  Enter your account password to verify: ").strip()
    if password.lower() in ("b", "back"):
        print("\n  Account deletion cancelled. Returning to menu...\n")
        return False

    success, _ = authenticate_user(user["email"], password)
    if not success:
        print("\n  [-] Incorrect password. Account deletion cancelled.\n")
        return False

    print("\n  Final Confirmation:")
    confirm_step3 = input("  Type 'DELETE' to confirm permanent deletion: ").strip()
    if confirm_step3 != "DELETE":
        print("\n  [-] Confirmation mismatch ('DELETE' was not entered). Deletion cancelled.\n")
        return False

    success, msg = delete_user(user["user_id"])
    if success:
        print(f"\n  [+] Account for '{user['name']}' ({user['email']}) deleted dynamically from MySQL.\n")
        return True
    else:
        print(f"\n  [-] Deletion failed: {msg}\n")
        return False


# ============================================================
# AUTHENTICATION & USER FLOW
# ============================================================

def authenticate():
    """Main authentication gate."""
    try:
        initialize_database()
    except Exception as e:
        print(f"\n  [-] Database initialization failed: {e}")
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
            user = register()
            if user:
                return user

        elif choice in ("3", "exit", "e", "q", "quit"):
            print("\n  Goodbye!\n")
            return None

        else:
            print("  [-] Invalid option. Please try again.")


def user_menu(user):
    """Post-login menu for the authenticated user."""
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
