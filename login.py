import json
import os
from pathlib import Path

from speakwise_database import (
    authenticate_user,
    delete_user,
    get_user_by_id,
    get_user_sessions,
    initialize_database,
    register_user,
    save_speech_session,
)


_REMEMBERED_SESSION_FILE = Path(__file__).resolve().parent / ".speakwise_session.json"


def remember_user(user):
    """Persist the account ID locally; never store the user's password."""
    try:
        user_id = int(user["user_id"])
        temp_path = _REMEMBERED_SESSION_FILE.with_suffix(".tmp")
        temp_path.write_text(json.dumps({"user_id": user_id}), encoding="utf-8")
        os.replace(temp_path, _REMEMBERED_SESSION_FILE)
    except (KeyError, TypeError, ValueError, OSError):
        pass


def load_remembered_user():
    """Restore the remembered account if it still exists in the database."""
    try:
        data = json.loads(_REMEMBERED_SESSION_FILE.read_text(encoding="utf-8"))
        user_id = int(data["user_id"])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None

    user = get_user_by_id(user_id)
    if user:
        return user
    return None


def clear_remembered_user():
    try:
        _REMEMBERED_SESSION_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def hash_password(password):
    import bcrypt

    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password, password_hash):
    import bcrypt

    return bcrypt.checkpw(
        password.encode("utf-8"), password_hash.encode("utf-8")
    )



def register():
    step = 1
    name = ""
    email = ""
    password = ""

    while True:
        if step == 1:
            val = input().strip()
            if val.lower() in ("b", "back"):
                return None

            if not val or len(val) < 2:
                continue

            name = val
            step = 2

        elif step == 2:
            val = input().strip().lower()
            if val.lower() in ("b", "back"):
                step = 1
                continue

            if not val or "@" not in val or "." not in val:
                continue

            email = val
            step = 3

        elif step == 3:
            val = input().strip()
            if val.lower() in ("b", "back"):
                step = 2
                continue

            if not val or len(val) < 6:
                continue

            password = val
            step = 4

        elif step == 4:
            confirm = input().strip()
            if confirm.lower() in ("b", "back"):
                step = 3
                continue

            if password != confirm:
                continue

            success, result = register_user(name, email, password)
            if success:
                return result
            else:
                return None



def login():
    step = 1
    login_input = ""
    password = ""

    while True:
        if step == 1:
            raw_input = input().strip()
            if raw_input.lower() in ("b", "back"):
                return None

            if not raw_input:
                continue

            login_input = raw_input
            step = 2

        elif step == 2:
            raw_pw = input().strip()
            if raw_pw.lower() in ("b", "back"):
                step = 1
                continue

            if not raw_pw:
                continue

            password = raw_pw

            success, result = authenticate_user(login_input, password)
            if success:
                return result
            else:
                step = 1



def save_session(user_id, category, topic_name, speaking_time, audio_path, video_path, transcription, report):
    return save_speech_session(
        user_id=user_id,
        category=category,
        topic_name=topic_name,
        speaking_time=speaking_time,
        audio_path=audio_path,
        video_path=video_path,
        transcription=transcription,
        report=report,
    )


def view_my_sessions(user):
    rows = get_user_sessions(user["user_id"])
    if not rows:
        print("No saved practice sessions.")
        return

    for i, row in enumerate(rows, 1):
        created_at = row.get("created_at")
        if hasattr(created_at, "strftime"):
            created_at = created_at.strftime("%Y-%m-%d %H:%M")
        print(f"{i}. {created_at or 'Date unavailable'} — {row.get('topic_name') or 'Untitled topic'}")
        print(f"   Category: {row.get('category') or 'General'} | Target: {row.get('speaking_time', 0)} seconds")
        transcription = (row.get("transcription") or "").strip()
        print(f"   Transcript: {transcription[:240] + ('…' if len(transcription) > 240 else '') if transcription else 'Unavailable'}")


def delete_account(user):
    confirm_step1 = input().strip().lower()
    if confirm_step1 in ("b", "back", "no", "n"):
        return False

    if confirm_step1 not in ("yes", "y"):
        return False

    password = input().strip()
    if password.lower() in ("b", "back"):
        return False

    success, _ = authenticate_user(user["email"], password)
    if not success:
        return False

    confirm_step3 = input().strip()
    if confirm_step3 != "DELETE":
        return False

    success, msg = delete_user(user["user_id"])
    return bool(success)



def authenticate():
    try:
        initialize_database()
    except Exception as error:
        print(f"Could not initialize the database: {error}")
        return None

    remembered_user = load_remembered_user()
    if remembered_user:
        print(f"Welcome back, {remembered_user['name']}.")
        return remembered_user

    while True:
        choice = input().strip()

        if choice == "1":
            user = login()
            if user:
                remember_user(user)
                return user

        elif choice == "2":
            user = register()
            if user:
                remember_user(user)
                return user

        elif choice in ("3", "exit", "e", "q", "quit"):
            return None


def user_menu(user):
    while True:
        choice = input().strip()

        if choice == "1":
            return "speech"
        elif choice == "2":
            view_my_sessions(user)
        elif choice == "3":
            return "logout"
        elif choice == "4":
            if delete_account(user):
                return "deleted"
