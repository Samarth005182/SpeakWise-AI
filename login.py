"""SpeakWise AI — Authentication & Admin Module.

Provides user registration, login, session history viewing,
and an admin dashboard for user management.
"""

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

def _validate_username(username):
    """Validate username: 3-50 chars, alphanumeric + underscores."""
    if not username or len(username) < 3:
        return "Username must be at least 3 characters."
    if len(username) > 50:
        return "Username must be at most 50 characters."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return "Username can only contain letters, numbers, and underscores."
    return None


def _validate_email(email):
    """Basic email format validation."""
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
# USER REGISTRATION
# ============================================================

def register():
    """Register a new user account.

    Prompts for username, email, password and confirmation.
    Validates all input and stores the new user in the database.

    Returns:
        True if registration was successful, False otherwise.
    """

    print("\n" + "=" * 46)
    print("           CREATE NEW ACCOUNT")
    print("=" * 46 + "\n")

    # --- Username ---
    username = input("  Enter username : ").strip()
    error = _validate_username(username)
    if error:
        print(f"\n  ✗ {error}")
        return False

    # --- Email ---
    email = input("  Enter email    : ").strip()
    error = _validate_email(email)
    if error:
        print(f"\n  ✗ {error}")
        return False

    # --- Password ---
    password = input("  Enter password : ").strip()
    error = _validate_password(password)
    if error:
        print(f"\n  ✗ {error}")
        return False

    confirm = input("  Confirm password: ").strip()
    if password != confirm:
        print("\n  ✗ Passwords do not match.")
        return False

    # --- Store in database ---
    try:
        db = get_connection()
        cursor = db.cursor()

        # Check for duplicate username or email
        cursor.execute(
            "SELECT username, email FROM users WHERE username = %s OR email = %s",
            (username, email),
        )
        existing = cursor.fetchone()
        if existing:
            if existing[0].lower() == username.lower():
                print("\n  ✗ Username is already taken. Please choose a different username.")
            else:
                print("\n  ✗ Email is already registered. Please log in instead.")
            cursor.close()
            db.close()
            return False

        pw_hash = hash_password(password)

        cursor.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) "
            "VALUES (%s, %s, %s, %s)",
            (username, email, pw_hash, False),
        )

        db.commit()
        cursor.close()
        db.close()

        print("\n  ✓ Account created successfully!")
        print(f"  Welcome, {username}! You can now log in.\n")
        return True

    except mysql.connector.Error as error:
        print(f"\n  ✗ Registration failed: {error}")
        return False


# ============================================================
# USER LOGIN
# ============================================================

def login():
    """Prompt the user to log in with username/email and password.

    Allows up to 3 attempts before returning None.

    Returns:
        dict with user info {id, username, email, is_admin} on success,
        or None on failure.
    """

    print("\n" + "=" * 46)
    print("                 LOGIN")
    print("=" * 46 + "\n")

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):

        login_input = input("  Username or Email : ").strip()
        password = input("  Password          : ").strip()

        if not login_input or not password:
            print("  ✗ Username/Email and password cannot be empty.\n")
            continue

        try:
            db = get_connection()
            cursor = db.cursor(dictionary=True)

            cursor.execute(
                "SELECT id, username, email, password_hash, is_admin "
                "FROM users WHERE username = %s OR email = %s",
                (login_input, login_input),
            )
            user = cursor.fetchone()

            cursor.close()
            db.close()

            if user and verify_password(password, user["password_hash"]):
                print(f"\n  ✓ Login successful! Welcome back, {user['username']}!\n")
                return {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "is_admin": bool(user["is_admin"]),
                }

            print(f"  ✗ Invalid username/email or password. "
                  f"({max_attempts - attempt} attempts remaining)\n")

        except mysql.connector.Error as error:
            print(f"  ✗ Login error: {error}\n")

    print("  ✗ Too many failed attempts.\n")
    return None


# ============================================================
# SESSION HISTORY
# ============================================================

def save_session(user_id, topic, scores):
    """Save a speech session's scores to the database.

    Args:
        user_id: The logged-in user's ID.
        topic: The speech topic.
        scores: Dict with score keys matching the sessions table columns.
    """

    try:
        db = get_connection()
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO sessions "
            "(user_id, topic, overall_score, fluency_score, pace_score, "
            "pause_score, eye_contact_score, head_stability_score, "
            "relevance_score, total_words, total_fillers) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                user_id,
                topic,
                scores.get("overall"),
                scores.get("fluency"),
                scores.get("pace"),
                scores.get("pauses"),
                scores.get("eye_contact"),
                scores.get("head_stability"),
                scores.get("relevance"),
                scores.get("total_words"),
                scores.get("total_fillers"),
            ),
        )

        db.commit()
        cursor.close()
        db.close()

    except mysql.connector.Error as error:
        print(f"  ⚠ Could not save session: {error}")


def view_my_sessions(user):
    """Display the logged-in user's past speech sessions."""

    print("\n" + "=" * 60)
    print("             MY SESSION HISTORY")
    print("=" * 60)

    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT topic, overall_score, fluency_score, pace_score, "
            "pause_score, eye_contact_score, head_stability_score, "
            "relevance_score, total_words, total_fillers, session_date "
            "FROM sessions WHERE user_id = %s ORDER BY session_date DESC",
            (user["id"],),
        )
        rows = cursor.fetchall()

        cursor.close()
        db.close()

        if not rows:
            print("\n  No sessions found. Start a speech practice to begin!\n")
            return

        for i, row in enumerate(rows, 1):
            date_str = row["session_date"].strftime("%Y-%m-%d %H:%M")
            overall = row["overall_score"]
            overall_display = f"{overall}/10" if overall is not None else "N/A"

            print(f"\n  Session #{i}  |  {date_str}")
            print(f"  Topic: {row['topic'] or 'Unknown'}")
            print(f"  Overall Score: {overall_display}")
            print(f"  ├─ Fluency:       {_fmt_score(row['fluency_score'])}")
            print(f"  ├─ Pace:          {_fmt_score(row['pace_score'])}")
            print(f"  ├─ Pauses:        {_fmt_score(row['pause_score'])}")
            print(f"  ├─ Eye Contact:   {_fmt_score(row['eye_contact_score'])}")
            print(f"  ├─ Head Stability:{_fmt_score(row['head_stability_score'])}")
            print(f"  └─ Relevance:     {_fmt_score(row['relevance_score'])}")
            print(f"  Words: {row['total_words'] or 0}  |  "
                  f"Fillers: {row['total_fillers'] or 0}")
            print("  " + "-" * 44)

        print()

    except mysql.connector.Error as error:
        print(f"\n  ✗ Could not load sessions: {error}\n")


def _fmt_score(value):
    """Format a score value for display."""
    return f"{value}/10" if value is not None else "N/A"


# ============================================================
# ADMIN DASHBOARD
# ============================================================

def admin_dashboard(user):
    """Admin dashboard for user and session management.

    Only accessible by users with is_admin=True.
    """

    if not user.get("is_admin"):
        print("\n  ✗ Access denied. Admin privileges required.\n")
        return

    while True:
        print("\n" + "=" * 50)
        print("              ADMIN DASHBOARD")
        print("=" * 50)
        print()
        print("  1. View All Users")
        print("  2. View User Session History")
        print("  3. Promote User to Admin")
        print("  4. Demote Admin to User")
        print("  5. Delete User")
        print("  6. System Stats")
        print("  7. Back to Main Menu")
        print()

        choice = input("  Select option (1-7): ").strip()

        if choice == "1":
            _admin_view_users()
        elif choice == "2":
            _admin_view_sessions()
        elif choice == "3":
            _admin_promote_user()
        elif choice == "4":
            _admin_demote_user(user)
        elif choice == "5":
            _admin_delete_user(user)
        elif choice == "6":
            _admin_system_stats()
        elif choice == "7":
            break
        else:
            print("  ✗ Invalid option. Please try again.")


def _admin_view_users():
    """Display all registered users in a formatted table."""

    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, username, email, is_admin, created_at FROM users "
            "ORDER BY id"
        )
        users = cursor.fetchall()

        cursor.close()
        db.close()

        print("\n  " + "-" * 72)
        print(f"  {'ID':<5} {'Username':<15} {'Email':<25} "
              f"{'Admin':<7} {'Created':<16}")
        print("  " + "-" * 72)

        for u in users:
            admin_flag = "Yes" if u["is_admin"] else "No"
            created = u["created_at"].strftime("%Y-%m-%d %H:%M")
            print(f"  {u['id']:<5} {u['username']:<15} {u['email']:<25} "
                  f"{admin_flag:<7} {created:<16}")

        print("  " + "-" * 72)
        print(f"  Total: {len(users)} users\n")

    except mysql.connector.Error as error:
        print(f"\n  ✗ Error: {error}\n")


def _admin_view_sessions():
    """View session history for a specific user (by username or email)."""

    user_input = input("\n  Enter username or email to view sessions: ").strip()
    if not user_input:
        return

    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, username FROM users WHERE username = %s OR email = %s",
            (user_input, user_input),
        )
        target = cursor.fetchone()

        if not target:
            print(f"  ✗ User '{user_input}' not found.")
            cursor.close()
            db.close()
            return

        cursor.execute(
            "SELECT topic, overall_score, fluency_score, pace_score, "
            "pause_score, eye_contact_score, head_stability_score, "
            "relevance_score, total_words, total_fillers, session_date "
            "FROM sessions WHERE user_id = %s ORDER BY session_date DESC",
            (target["id"],),
        )
        rows = cursor.fetchall()

        cursor.close()
        db.close()

        if not rows:
            print(f"  No sessions found for '{target['username']}'.\n")
            return

        print(f"\n  Sessions for {target['username']}:")
        print("  " + "-" * 50)

        for i, row in enumerate(rows, 1):
            date_str = row["session_date"].strftime("%Y-%m-%d %H:%M")
            overall = row["overall_score"]
            overall_display = f"{overall}/10" if overall is not None else "N/A"

            print(f"  #{i} | {date_str} | Topic: {row['topic'] or 'Unknown'}")
            print(f"      Overall: {overall_display} | "
                  f"Words: {row['total_words'] or 0} | "
                  f"Fillers: {row['total_fillers'] or 0}")

        print("  " + "-" * 50 + "\n")

    except mysql.connector.Error as error:
        print(f"\n  ✗ Error: {error}\n")


def _admin_promote_user():
    """Promote a regular user to admin."""

    user_input = input("\n  Enter username or email to promote: ").strip()
    if not user_input:
        return

    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, username, is_admin FROM users WHERE username = %s OR email = %s",
            (user_input, user_input),
        )
        target = cursor.fetchone()

        if not target:
            print(f"  ✗ User '{user_input}' not found.")
        elif target["is_admin"]:
            print(f"  ✗ '{target['username']}' is already an admin.")
        else:
            cursor.execute(
                "UPDATE users SET is_admin = TRUE WHERE id = %s",
                (target["id"],),
            )
            db.commit()
            print(f"  ✓ '{target['username']}' has been promoted to admin.")

        cursor.close()
        db.close()

    except mysql.connector.Error as error:
        print(f"\n  ✗ Error: {error}\n")


def _admin_demote_user(current_user):
    """Demote an admin to regular user. Cannot demote yourself."""

    user_input = input("\n  Enter admin username or email to demote: ").strip()
    if not user_input:
        return

    if user_input.lower() in (current_user["username"].lower(), current_user["email"].lower()):
        print("  ✗ You cannot demote yourself.")
        return

    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, username, is_admin FROM users WHERE username = %s OR email = %s",
            (user_input, user_input),
        )
        target = cursor.fetchone()

        if not target:
            print(f"  ✗ User '{user_input}' not found.")
        elif not target["is_admin"]:
            print(f"  ✗ '{target['username']}' is not an admin.")
        else:
            cursor.execute(
                "UPDATE users SET is_admin = FALSE WHERE id = %s",
                (target["id"],),
            )
            db.commit()
            print(f"  ✓ '{target['username']}' has been demoted to regular user.")

        cursor.close()
        db.close()

    except mysql.connector.Error as error:
        print(f"\n  ✗ Error: {error}\n")


def _admin_delete_user(current_user):
    """Delete a user and their sessions. Cannot delete yourself."""

    user_input = input("\n  Enter username or email to delete: ").strip()
    if not user_input:
        return

    if user_input.lower() in (current_user["username"].lower(), current_user["email"].lower()):
        print("  ✗ You cannot delete your own account.")
        return

    try:
        db = get_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, username FROM users WHERE username = %s OR email = %s",
            (user_input, user_input),
        )
        target = cursor.fetchone()

        if not target:
            print(f"  ✗ User '{user_input}' not found.")
            cursor.close()
            db.close()
            return

        confirm = input(
            f"  ⚠ Delete user '{target['username']}' and all their data? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("  Cancelled.")
            cursor.close()
            db.close()
            return

        cursor.execute("DELETE FROM users WHERE id = %s", (target["id"],))
        db.commit()
        print(f"  ✓ User '{target['username']}' has been deleted.")

        cursor.close()
        db.close()

    except mysql.connector.Error as error:
        print(f"\n  ✗ Error: {error}\n")
        db.close()

    except mysql.connector.Error as error:
        print(f"\n  ✗ Error: {error}\n")


def _admin_system_stats():
    """Display overall system statistics."""

    try:
        db = get_connection()
        cursor = db.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = TRUE")
        total_admins = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(overall_score) FROM sessions")
        avg_score = cursor.fetchone()[0]

        cursor.execute(
            "SELECT u.username, COUNT(s.id) as session_count "
            "FROM users u LEFT JOIN sessions s ON u.id = s.user_id "
            "GROUP BY u.id ORDER BY session_count DESC LIMIT 5"
        )
        top_users = cursor.fetchall()

        cursor.close()
        db.close()

        print("\n  " + "=" * 40)
        print("          SYSTEM STATISTICS")
        print("  " + "=" * 40)
        print(f"  Total Users:     {total_users}")
        print(f"  Admin Users:     {total_admins}")
        print(f"  Total Sessions:  {total_sessions}")
        print(f"  Avg Score:       "
              f"{avg_score:.1f}/10" if avg_score else "  Avg Score:       N/A")

        if top_users:
            print("\n  Most Active Users:")
            for username, count in top_users:
                print(f"    {username}: {count} sessions")

        print("  " + "=" * 40 + "\n")

    except mysql.connector.Error as error:
        print(f"\n  ✗ Error: {error}\n")


# ============================================================
# AUTHENTICATION FLOW (called from main.py)
# ============================================================

def authenticate():
    """Main authentication flow.

    Initializes the database, then asks the user whether they
    have an account. Routes to login or register accordingly.

    Returns:
        dict with user info on success, or None to exit.
    """

    # Ensure database tables and admin account exist
    try:
        initialize_database()
    except Exception as e:
        print(f"\n  ✗ Database initialization failed: {e}")
        print("  Please check your database connection settings in .env\n")
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

        elif choice == "3":
            print("\n  Goodbye!\n")
            return None

        else:
            print("  ✗ Invalid option. Please try again.")


def user_menu(user):
    """Post-login menu for the authenticated user.

    Returns:
        str — "speech" to start a practice session,
               "sessions" to view history,
               "admin" to open admin dashboard,
               "logout" to log out.
    """

    while True:
        print("\n" + "=" * 46)
        print(f"  Welcome, {user['username']}!")
        print("=" * 46)
        print()
        print("  1. Start Speech Practice")
        print("  2. View My Past Sessions")

        if user.get("is_admin"):
            print("  3. Admin Dashboard")
            print("  4. Logout")
            max_option = 4
        else:
            print("  3. Logout")
            max_option = 3

        print()

        choice = input(f"  Select option (1-{max_option}): ").strip()

        if choice == "1":
            return "speech"
        elif choice == "2":
            view_my_sessions(user)
        elif choice == "3":
            if user.get("is_admin"):
                admin_dashboard(user)
            else:
                return "logout"
        elif choice == "4" and user.get("is_admin"):
            return "logout"
        else:
            print("  ✗ Invalid option. Please try again.")
