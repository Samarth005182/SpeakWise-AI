import os
import sys
import hmac

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"

import json
import time
import threading
import logging
import winsound
import tkinter as tk
from dotenv import load_dotenv
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2 as cv

try:
    cv.setLogLevel(0)
except Exception:
    pass

load_dotenv()

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FONT_FAMILY = "Inter"

def load_all_project_fonts():
    global FONT_FAMILY
    loaded = []
    detected_family = None
    if os.path.exists(FONTS_DIR):
        subdirs = [d for d in os.listdir(FONTS_DIR) if os.path.isdir(os.path.join(FONTS_DIR, d))]
        if subdirs:
            detected_family = subdirs[0].replace("_", " ")

        for root_dir, _, files in os.walk(FONTS_DIR):
            for file in files:
                if file.lower().endswith((".ttf", ".otf")):
                    full_path = os.path.join(root_dir, file)
                    try:
                        if hasattr(ctk, "FontManager"):
                            ctk.FontManager.load_font(full_path)
                        loaded.append(full_path)
                    except Exception:
                        pass
    if detected_family:
        FONT_FAMILY = detected_family
    return loaded

load_all_project_fonts()


from speakwise_database import (
    get_connection,
    initialize_database,
    register_user,
    authenticate_user,
    get_all_users,
    get_user_sessions,
    delete_user,
    get_db_stats,
    save_speech_session,
    get_all_databases,
    get_database_tables,
    get_table_data,
    get_table_row_count,
)
from login import (
    hash_password,
    verify_password,
    save_session,
    remember_user,
    load_remembered_user,
    clear_remembered_user,
)
from topics import get_random_topic, get_all_categories, CATEGORIES
from ai import ai_prepare, analyze_relevance, CoachChatSession
from report import print_report, calculate_overall
import audio
import video_capture
from filler_detection import detect_fillers
from transcription import transcribe_audio_detailed
from video_analysis import analyze_video
from audio_text import detect_pauses_detailed, get_audio_duration
from recording_paths import generate_recording_paths
from transcription import count_words
from recording_session import record_session

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


COLOR_ICE = "#C9DAEA"
COLOR_CYAN = "#03F7EB"
COLOR_TEAL = "#00B295"
COLOR_ONYX = "#191516"
COLOR_RUBY = "#AB2346"

BG_DARK = "#191516"
SIDEBAR_BG = "#131011"
CARD_BG = "#221c1e"
CARD_BORDER = "#352b2e"
CARD_ACTIVE_BORDER = "#03F7EB"
CARD_HOVER = "#2b2326"
CARD_ACTIVE_BG = "#172825"

ACCENT_BLUE = "#00B295"
ACCENT_TEAL = "#00B295"
ACCENT_CYAN = "#03F7EB"
ACCENT_EMERALD = "#00B295"
ACCENT_RUBY = "#AB2346"
ACCENT_PURPLE = "#AB2346"
ACCENT_ORANGE = "#AB2346"
ACCENT_RED = "#AB2346"

TEXT_WHITE = "#FFFFFF"
TEXT_ICE = "#C9DAEA"
TEXT_MUTED = "#C9DAEA"
TEXT_SUBTLE = "#7a8a99"


PRESET_CATEGORIES = [
    {
        "id": "Technology",
        "name": "Technology",
        "icon": "💻",
        "desc": "Innovation, AI, gadgets and the digital world",
        "color": "#03F7EB",
        "backend_key": "Technology & Artificial Intelligence",
    },
    {
        "id": "Science",
        "name": "Science",
        "icon": "🧪",
        "desc": "Discoveries, research and the natural world",
        "color": "#00B295",
        "backend_key": "Scientific Wonders & Quantum Concepts",
    },
    {
        "id": "History",
        "name": "History",
        "icon": "🏛️",
        "desc": "Events, people and turning points",
        "color": "#C9DAEA",
        "backend_key": "History & Historical Mysteries",
    },
    {
        "id": "Business",
        "name": "Business",
        "icon": "📈",
        "desc": "Economy, leadership and entrepreneurship",
        "color": "#00B295",
        "backend_key": "Business, Startups & Economics",
    },
    {
        "id": "Society",
        "name": "Society",
        "icon": "👥",
        "desc": "People, culture and modern life",
        "color": "#AB2346",
        "backend_key": "Society & Modern Media",
    },
    {
        "id": "Environment",
        "name": "Environment",
        "icon": "🌿",
        "desc": "Nature, climate and sustainability",
        "color": "#00B295",
        "backend_key": "Environment & Climate Sustainability",
    },
    {
        "id": "Entertainment",
        "name": "Entertainment",
        "icon": "🎮",
        "desc": "Movies, music, games and pop culture",
        "color": "#AB2346",
        "backend_key": "Literature, Cinema & Storytelling",
    },
    {
        "id": "Random",
        "name": "Random",
        "icon": "🎲",
        "desc": "Surprise me with anything!",
        "color": "#03F7EB",
        "backend_key": None,
    },
]

DURATION_OPTIONS = [
    {"label": "30\nSeconds", "seconds": 30, "display": "30 Seconds"},
    {"label": "1\nMinute", "seconds": 60, "display": "1 Minute"},
    {"label": "2\nMinutes", "seconds": 120, "display": "2 Minutes"},
    {"label": "5\nMinutes", "seconds": 300, "display": "5 Minutes"},
    {"label": "10\nMinutes", "seconds": 600, "display": "10 Minutes"},
]





class SegmentedControl(ctk.CTkFrame):
    """Animated segmented control widget (pill selector) for filter tabs."""

    def __init__(
        self,
        master,
        values=None,
        default="7 Days",
        command=None,
        width=260,
        height=38,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=("gray90", "#27272A"),
            corner_radius=8,
            width=width,
            height=height,
            **kwargs
        )

        self.values = values or ["7 Days", "30 Days", "All Time"]
        self.command = command
        self.selected = default if default in self.values else self.values[0]
        self.buttons = {}
        self._animation_job = None

        self.grid_propagate(False)

        self.track = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=8
        )
        self.track.pack(fill="both", expand=True, padx=2, pady=2)

        self.track.grid_rowconfigure(0, weight=1)
        for index, value in enumerate(self.values):
            self.track.grid_columnconfigure(index, weight=1, uniform="segment")

        self.indicator = ctk.CTkFrame(
            self.track,
            fg_color=("white", "#3F3F46"),
            corner_radius=7
        )
        self.indicator.place(
            relx=0,
            rely=0,
            relheight=1,
            relwidth=1 / len(self.values),
            bordermode="outside"
        )

        for index, value in enumerate(self.values):
            button = ctk.CTkButton(
                self.track,
                text=value,
                fg_color="transparent",
                hover_color=("gray85", "#35353B"),
                text_color=("gray20", "#FAFAFA"),
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                corner_radius=7,
                border_width=0,
                height=height - 4,
                command=lambda v=value: self.set(v)
            )
            button.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=0,
                pady=0
            )
            self.buttons[value] = button

        self.track.bind("<Configure>", self._position_indicator)
        self.after(10, self._position_indicator)

    def _position_indicator(self, event=None):
        if not self.values:
            return
        index = self.values.index(self.selected)
        count = len(self.values)
        self.indicator.place_configure(
            relx=index / count,
            rely=0,
            relwidth=1 / count,
            relheight=1
        )
        self.indicator.lower()
        for button in self.buttons.values():
            button.lift()

    def set(self, value, notify=True):
        if value not in self.values:
            return
        if self._animation_job:
            self.after_cancel(self._animation_job)
            self._animation_job = None

        old_value = self.selected
        self.selected = value
        start = self.values.index(old_value) / len(self.values)
        target = self.values.index(value) / len(self.values)
        steps = 8

        def animate(step=0):
            progress = min(step / steps, 1)

            eased = progress * progress * (3 - 2 * progress)
            position = start + (target - start) * eased
            self.indicator.place_configure(
                relx=position,
                rely=0,
                relwidth=1 / len(self.values),
                relheight=1
            )
            if step < steps:
                self._animation_job = self.after(15, lambda: animate(step + 1))
            else:
                self._animation_job = None

        animate()
        if notify and self.command:
            self.command(value)

    def get(self):
        return self.selected


class SpeakWiseApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SpeakWise AI — Practice. Analyze. Improve.")
        self.geometry("1920x1080")
        self.minsize(1280, 720)
        self.configure(fg_color=BG_DARK)

        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass
        self.after(50, self._ensure_maximized)

        self.bind("<F11>", self._toggle_fullscreen)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        try:
            initialize_database()
        except Exception:
            pass

        self.current_user = load_remembered_user()
        self.admin_authenticated = False

        self.home_video = None
        self.home_video_label = None
        self.home_video_running = False
        self.home_video_image = None
        self.home_video_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "home_background.mp4"
        )

        self.current_step = 1
        self._topic_generation_id = 0
        self.selected_category = PRESET_CATEGORIES[0]
        self.selected_duration = DURATION_OPTIONS[2]
        self.current_topic_data = self._empty_topic_data()

        self._build_app_shell()

        self.show_page("home")

    def _ensure_maximized(self):
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass

    def _toggle_fullscreen(self, event=None):
        try:
            is_fs = bool(self.attributes("-fullscreen"))
            self.attributes("-fullscreen", not is_fs)
        except Exception:
            pass

    def safe_after(self, ms, func, *args):
        """Thread-safe and exception-safe wrapper around self.after."""
        try:
            if self.winfo_exists():
                return self.after(ms, func, *args)
        except Exception:
            pass
        return None


    def _build_app_shell(self):
        self.grid_columnconfigure(0, weight=0, minsize=260)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self,
            fg_color=SIDEBAR_BG,
            corner_radius=0,
            border_width=1,
            border_color="#2d2427",
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(7, weight=1)

        logo_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_box.grid(row=0, column=0, padx=24, pady=(28, 24), sticky="w")

        logo_title = ctk.CTkLabel(
            logo_box,
            text="SpeakWise AI",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_WHITE,
        )
        logo_title.pack(anchor="w")

        logo_sub = ctk.CTkLabel(
            logo_box,
            text="Practice. Analyze. Improve.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_CYAN,
        )
        logo_sub.pack(anchor="w", pady=(2, 0))

        self.nav_buttons = {}
        nav_items = [
            ("home", "  🏠  Home"),
            ("practice", "  🎙️ Practice"),
            ("history", "  🕒  History"),
            ("profile", "  👤  Profile"),
            ("settings", "  ⚙️  Settings"),
            ("admin", "  🗄️  Admin"),
        ]

        for i, (key, label) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=14),
                anchor="w",
                fg_color="transparent",
                text_color=TEXT_MUTED,
                hover_color=CARD_HOVER,
                corner_radius=10,
                height=44,
                command=lambda k=key: self.show_page(k),
            )
            btn.grid(row=i, column=0, padx=16, pady=4, sticky="ew")
            self.nav_buttons[key] = btn

        bot_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bot_frame.grid(row=8, column=0, padx=20, pady=20, sticky="sew")

        quote_lbl = ctk.CTkLabel(
            bot_frame,
            text='“Progress turns\npractice into\npossibilities.”',
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, slant="italic"),
            text_color=TEXT_SUBTLE,
            justify="left",
        )
        quote_lbl.pack(anchor="w", pady=(0, 14))

        v_lbl = ctk.CTkLabel(
            bot_frame,
            text="SpeakWise AI",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_SUBTLE,
        )
        v_lbl.pack(anchor="w")

        self.main_area = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self._build_top_bar()

        self.pages_container = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.pages_container.grid(row=1, column=0, sticky="nsew", padx=(32, 2), pady=(0, 16))
        self.pages_container.grid_rowconfigure(0, weight=1)
        self.pages_container.grid_columnconfigure(0, weight=1)

        self.pages = {}
        self.pages["home"] = self._create_home_view()
        self.pages["practice"] = self._create_practice_view()
        self.pages["history"] = self._create_history_view()
        self.pages["reports"] = self._create_reports_view()
        self.pages["profile"] = self._create_profile_view()
        self.pages["settings"] = self._create_settings_view()
        self.pages["admin"] = self._create_admin_view()

    def _build_top_bar(self):
        """Build top progress stepper bar and user badge."""
        self.top_bar = ctk.CTkFrame(self.main_area, fg_color="transparent", height=70)
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=40, pady=(16, 12))
        self.top_bar.grid_columnconfigure(0, weight=1)
        self.top_bar.grid_columnconfigure(1, weight=0)

        stepper_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        stepper_frame.grid(row=0, column=0, sticky="w")

        self.step_indicators = {}
        steps = [
            (1, "1. Topic", "✓", "1"),
            (2, "2. Prepare", "✓", "🤖"),
            (3, "3. Speak", "✓", "🎙️"),
            (4, "4. Results", "✓", "📊"),
        ]

        for idx, (step_num, step_name, done_icon, def_icon) in enumerate(steps):
            s_box = ctk.CTkFrame(stepper_frame, fg_color="transparent")
            s_box.pack(side="left", padx=(0, 10))

            circle = ctk.CTkButton(
                s_box,
                text=def_icon,
                width=32,
                height=32,
                corner_radius=16,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                fg_color=ACCENT_BLUE if step_num == 1 else "#261e21",
                text_color=TEXT_WHITE if step_num == 1 else TEXT_MUTED,
                hover=False,
            )
            circle.pack(side="left", padx=(0, 8))

            name_lbl = ctk.CTkLabel(
                s_box,
                text=step_name,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold" if step_num == 1 else "normal"),
                text_color=TEXT_WHITE if step_num == 1 else TEXT_MUTED,
            )
            name_lbl.pack(side="left")

            self.step_indicators[step_num] = (circle, name_lbl, done_icon, def_icon)

            if idx < len(steps) - 1:
                line = ctk.CTkFrame(stepper_frame, width=22, height=2, fg_color="#352b2e")
                line.pack(side="left", padx=(4, 14))

        right_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        right_box.grid(row=0, column=1, sticky="e")

        quote_top = ctk.CTkLabel(
            right_box,
            text='"Great conversations start with great topics."',
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, slant="italic"),
            text_color=TEXT_SUBTLE,
        )
        quote_top.pack(side="left", padx=(0, 24))

        if self.current_user:
            u_name = self.current_user.get("name", "User")
            initials = "".join([part[0].upper() for part in u_name.split()[:2]]) or "U"
            role_text = "Student"
            circle_bg = ACCENT_BLUE
        else:
            u_name = "Sign In / Register"
            initials = "👤"
            role_text = "Guest Mode"
            circle_bg = "#282023"

        user_card = ctk.CTkFrame(right_box, fg_color=CARD_BG, corner_radius=20, border_width=1, border_color=CARD_BORDER, cursor="hand2")
        user_card.pack(side="left")

        self.top_u_circle = ctk.CTkLabel(
            user_card,
            text=initials,
            width=32,
            height=32,
            corner_radius=16,
            fg_color=circle_bg,
            text_color=TEXT_WHITE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
        )
        self.top_u_circle.pack(side="left", padx=(4, 8), pady=4)

        u_info = ctk.CTkFrame(user_card, fg_color="transparent")
        u_info.pack(side="left", padx=(0, 12))

        self.top_u_name_lbl = ctk.CTkLabel(
            u_info,
            text=u_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_WHITE,
        )
        self.top_u_name_lbl.pack(anchor="w")

        self.top_u_role_lbl = ctk.CTkLabel(
            u_info,
            text=role_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_CYAN if self.current_user else TEXT_MUTED,
        )
        self.top_u_role_lbl.pack(anchor="w")

        for w in (user_card, self.top_u_circle, u_info, self.top_u_name_lbl, self.top_u_role_lbl):
            w.bind("<Button-1>", lambda e: self.open_auth_modal("login"))

    def update_stepper(self, step_num):
        """Update top stepper bar active status."""
        self.current_step = step_num
        for s_num, (circle, name_lbl, done_icon, def_icon) in self.step_indicators.items():
            if s_num == step_num:
                circle.configure(fg_color=ACCENT_BLUE, text_color=TEXT_WHITE, text=def_icon)
                name_lbl.configure(text_color=TEXT_WHITE, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
            elif s_num < step_num:
                circle.configure(fg_color=ACCENT_CYAN, text_color="#191516", text=done_icon)
                name_lbl.configure(text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=13))
            else:
                circle.configure(fg_color="#261e21", text_color=TEXT_MUTED, text=def_icon)
                name_lbl.configure(text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=13))

    def start_new_practice_session(self):
        """Start a completely new practice session from Step 1 with a fresh topic."""
        self._topic_generation_id += 1
        self._cancel_prep_timer()
        if getattr(self, "_audio_is_playing", False):
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
            self._audio_is_playing = False

        self.current_step = 1
        self.update_stepper(1)

        self.current_topic_data = self._empty_topic_data()

        self._build_step1_topic_selection()
        self.show_page("practice")

    def _end_session(self):
        """Cleanly end current practice session and navigate back to Home."""
        self._cancel_prep_timer()
        if getattr(self, "_audio_is_playing", False):
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
            self._audio_is_playing = False

        self.current_step = 1
        self.update_stepper(1)
        self._build_step1_topic_selection()
        self.show_page("home")


    def _start_home_background_video(self):
        """Start the looping Home-page background video."""
        self._stop_home_background_video()

        if not os.path.exists(self.home_video_path):
            return

        try:
            self.home_video = cv.VideoCapture(self.home_video_path)
            if not self.home_video.isOpened():
                self.home_video.release()
                self.home_video = None
                return

            self.home_video_running = True
            self._update_home_background_video()
        except Exception:
            self.home_video = None
            self.home_video_running = False

    def _stop_home_background_video(self):
        """Stop and release the Home-page background video."""
        self.home_video_running = False

        if self.home_video is not None:
            try:
                self.home_video.release()
            except Exception:
                pass
            self.home_video = None

    def _update_home_background_video(self):
        """Display the next video frame, crop-to-fill, and loop automatically."""
        if not self.home_video_running or self.home_video is None:
            return

        try:
            if not self.home_video_label or not self.home_video_label.winfo_exists():
                self._stop_home_background_video()
                return

            ret, frame = self.home_video.read()

            if not ret:
                self.home_video.set(cv.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.home_video.read()

            if not ret:
                self._stop_home_background_video()
                return

            width = self.home_video_label.winfo_width()
            height = self.home_video_label.winfo_height()

            if width < 2 or height < 2:
                self.safe_after(50, self._update_home_background_video)
                return

            frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

            video_h, video_w = frame.shape[:2]
            scale = max(width / video_w, height / video_h)
            new_w = max(1, int(video_w * scale))
            new_h = max(1, int(video_h * scale))

            frame = cv.resize(frame, (new_w, new_h), interpolation=cv.INTER_AREA)

            x = max(0, (new_w - width) // 2)
            y = max(0, (new_h - height) // 2)
            frame = frame[y:y + height, x:x + width]

            frame = (frame.astype("float32") * 0.48).clip(0, 255).astype("uint8")

            image = Image.fromarray(frame)
            self.home_video_image = ImageTk.PhotoImage(image=image)
            self.home_video_label.configure(image=self.home_video_image, text="")

            self.safe_after(33, self._update_home_background_video)

        except Exception:
            self._stop_home_background_video()

    def show_page(self, page_key):
        """Switch navigation page."""
        if page_key == "practice" and self.current_step == 4:
            self.start_new_practice_session()
            return

        for key, btn in self.nav_buttons.items():
            if key == page_key:
                btn.configure(
                    fg_color="#261e21",
                    text_color=COLOR_CYAN,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=TEXT_MUTED,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="normal"),
                )

        if getattr(self, "_audio_is_playing", False):
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
            self._audio_is_playing = False
            if hasattr(self, "_audio_play_timer") and self._audio_play_timer:
                try:
                    self.after_cancel(self._audio_play_timer)
                except Exception:
                    pass
                self._audio_play_timer = None

        if page_key == "home":
            self._render_home_content()
            self._start_home_background_video()
        else:
            self._stop_home_background_video()

        if page_key == "history":
            self._render_history_items()
        elif page_key == "reports":
            if not self.reports_container.winfo_children():
                self._render_speech_report(self.reports_container)

        for p in self.pages.values():
            p.grid_remove()

        if page_key in self.pages:
            self.pages[page_key].grid(row=0, column=0, sticky="nsew")


    def _create_practice_view(self):
        self.practice_container = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        self.practice_container.grid_columnconfigure(0, weight=1)
        self.practice_container.grid_rowconfigure(0, weight=1)

        self._build_step1_topic_selection()
        return self.practice_container

    def _build_step1_topic_selection(self):
        """Construct the exact Topic Selection Page from the user's mockup."""
        self.update_stepper(1)

        for w in self.practice_container.winfo_children():
            w.destroy()

        scroll = ctk.CTkScrollableFrame(self.practice_container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        scroll.grid_columnconfigure(0, weight=6, uniform="topic_columns")
        scroll.grid_columnconfigure(1, weight=4, uniform="topic_columns")

        header_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))

        step_tag = ctk.CTkLabel(
            header_frame,
            text="STEP 1 OF 4",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=ACCENT_BLUE,
        )
        step_tag.pack(anchor="w")

        main_title = ctk.CTkLabel(
            header_frame,
            text="Choose Your Topic",
            font=ctk.CTkFont(family=FONT_FAMILY, size=32, weight="bold"),
            text_color=TEXT_WHITE,
        )
        main_title.pack(anchor="w", pady=(2, 4))

        main_sub = ctk.CTkLabel(
            header_frame,
            text="Select a category, set your speaking time, and get an AI-generated topic tailored for you.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_MUTED,
        )
        main_sub.pack(anchor="w")

        left_col = ctk.CTkFrame(scroll, fg_color="transparent")
        left_col.grid(row=1, column=0, sticky="nsew", padx=(0, 20))

        cat_sec_head = ctk.CTkFrame(left_col, fg_color="transparent")
        cat_sec_head.pack(fill="x", pady=(0, 12))

        cat_num = ctk.CTkButton(
            cat_sec_head,
            text="1",
            width=24,
            height=24,
            corner_radius=12,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=ACCENT_BLUE,
            text_color=TEXT_WHITE,
            hover=False,
        )
        cat_num.pack(side="left", padx=(0, 10))

        cat_title_box = ctk.CTkFrame(cat_sec_head, fg_color="transparent")
        cat_title_box.pack(side="left")

        cat_title = ctk.CTkLabel(
            cat_title_box,
            text="Select a Category",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_WHITE,
        )
        cat_title.pack(anchor="w")

        cat_sub = ctk.CTkLabel(
            cat_title_box,
            text="Choose an area that interests you.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        )
        cat_sub.pack(anchor="w")

        cat_grid = ctk.CTkFrame(left_col, fg_color="transparent")
        cat_grid.pack(fill="x", pady=(0, 24))
        for col in range(4):
            cat_grid.grid_columnconfigure(col, weight=1, uniform="cat_card")

        self.category_card_widgets = {}

        for idx, cat in enumerate(PRESET_CATEGORIES):
            r = idx // 4
            c = idx % 4
            is_active = (cat["id"] == self.selected_category["id"])

            card = ctk.CTkFrame(
                cat_grid,
                fg_color=CARD_ACTIVE_BG if is_active else CARD_BG,
                corner_radius=12,
                border_width=2 if is_active else 1,
                border_color=CARD_ACTIVE_BORDER if is_active else CARD_BORDER,
                cursor="hand2",
            )
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

            top_bar = ctk.CTkFrame(card, fg_color="transparent")
            top_bar.pack(fill="x", padx=12, pady=(12, 0))

            icon_box = ctk.CTkFrame(
                top_bar,
                width=36,
                height=36,
                corner_radius=8,
                fg_color="#261e21",
            )
            icon_box.pack(side="left")
            icon_box.pack_propagate(False)

            icon_lbl = ctk.CTkLabel(
                icon_box,
                text=cat["icon"],
                font=ctk.CTkFont(size=18),
            )
            icon_lbl.pack(expand=True)

            check_lbl = ctk.CTkLabel(
                top_bar,
                text="✓" if is_active else "",
                font=ctk.CTkFont(size=12, weight="bold"),
                width=20,
                height=20,
                corner_radius=10,
                fg_color=ACCENT_BLUE if is_active else "transparent",
                text_color=TEXT_WHITE,
            )
            check_lbl.pack(side="right")

            c_name = ctk.CTkLabel(
                card,
                text=cat["name"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                text_color=TEXT_WHITE,
            )
            c_name.pack(anchor="w", padx=14, pady=(10, 2))

            c_desc = ctk.CTkLabel(
                card,
                text=cat["desc"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED,
                justify="left",
                wraplength=120,
            )
            c_desc.pack(anchor="w", padx=14, pady=(0, 14))

            for widget in (card, top_bar, icon_box, icon_lbl, c_name, c_desc):
                widget.bind("<Button-1>", lambda e, c=cat: self._on_select_category(c))

            self.category_card_widgets[cat["id"]] = (card, check_lbl)

        time_sec_head = ctk.CTkFrame(left_col, fg_color="transparent")
        time_sec_head.pack(fill="x", pady=(0, 12))

        time_num = ctk.CTkButton(
            time_sec_head,
            text="2",
            width=24,
            height=24,
            corner_radius=12,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=ACCENT_BLUE,
            text_color=TEXT_WHITE,
            hover=False,
        )
        time_num.pack(side="left", padx=(0, 10))

        time_title_box = ctk.CTkFrame(time_sec_head, fg_color="transparent")
        time_title_box.pack(side="left")

        time_title = ctk.CTkLabel(
            time_title_box,
            text="Set Speaking Time",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_WHITE,
        )
        time_title.pack(anchor="w")

        time_sub = ctk.CTkLabel(
            time_title_box,
            text="Choose how long you want to speak.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        )
        time_sub.pack(anchor="w")

        time_grid = ctk.CTkFrame(left_col, fg_color="transparent")
        time_grid.pack(fill="x", pady=(0, 20))
        for col in range(5):
            time_grid.grid_columnconfigure(col, weight=1, uniform="time_card")

        self.duration_card_widgets = {}

        for idx, dur in enumerate(DURATION_OPTIONS):
            is_active = (dur["seconds"] == self.selected_duration["seconds"])

            t_card = ctk.CTkFrame(
                time_grid,
                fg_color=CARD_ACTIVE_BG if is_active else CARD_BG,
                corner_radius=12,
                border_width=2 if is_active else 1,
                border_color=CARD_ACTIVE_BORDER if is_active else CARD_BORDER,
                cursor="hand2",
                height=74,
            )
            t_card.grid(row=0, column=idx, padx=6, sticky="nsew")

            t_top = ctk.CTkFrame(t_card, fg_color="transparent")
            t_top.pack(fill="x", padx=8, pady=(6, 0))

            t_check = ctk.CTkLabel(
                t_top,
                text="✓" if is_active else "",
                font=ctk.CTkFont(size=10, weight="bold"),
                width=16,
                height=16,
                corner_radius=8,
                fg_color=ACCENT_BLUE if is_active else "transparent",
                text_color=TEXT_WHITE,
            )
            t_check.pack(side="right")

            t_lbl = ctk.CTkLabel(
                t_card,
                text=dur["label"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                text_color=TEXT_WHITE,
                justify="center",
            )
            t_lbl.pack(expand=True, pady=(0, 8))

            for widget in (t_card, t_top, t_lbl):
                widget.bind("<Button-1>", lambda e, d=dur: self._on_select_duration(d))

            self.duration_card_widgets[dur["seconds"]] = (t_card, t_check)

        tip_box = ctk.CTkFrame(
            left_col,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=CARD_BORDER,
        )
        tip_box.pack(fill="x", pady=(4, 10))

        tip_inner = ctk.CTkFrame(tip_box, fg_color="transparent")
        tip_inner.pack(fill="x", padx=16, pady=12)

        tip_icon = ctk.CTkLabel(tip_inner, text="💡", font=ctk.CTkFont(size=18))
        tip_icon.pack(side="left", padx=(0, 12))

        tip_text_box = ctk.CTkFrame(tip_inner, fg_color="transparent")
        tip_text_box.pack(side="left")

        tip_head = ctk.CTkLabel(
            tip_text_box,
            text="Tip",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_CYAN,
        )
        tip_head.pack(anchor="w")

        tip_body = ctk.CTkLabel(
            tip_text_box,
            text="Choose a topic you find interesting. You'll speak more naturally and confidently!",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        )
        tip_body.pack(anchor="w")

        right_col = ctk.CTkFrame(scroll, fg_color="transparent")
        right_col.grid(row=1, column=1, sticky="nsew", padx=(20, 0))

        r_head = ctk.CTkFrame(right_col, fg_color="transparent")
        r_head.pack(fill="x", pady=(0, 12))

        topic_num = ctk.CTkButton(
            r_head,
            text="3",
            width=24,
            height=24,
            corner_radius=12,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=ACCENT_BLUE,
            text_color=TEXT_WHITE,
            hover=False,
        )
        topic_num.pack(side="left", padx=(0, 10))

        r_title_box = ctk.CTkFrame(r_head, fg_color="transparent")
        r_title_box.pack(side="left")

        r_title = ctk.CTkLabel(
            r_title_box,
            text="Your Topic",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_WHITE,
        )
        r_title.pack(anchor="w")

        r_sub = ctk.CTkLabel(
            r_title_box,
            text="Generate a topic using AI or pick another.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        )
        r_sub.pack(anchor="w")
        r_sub.configure(text="Generate a topic when you're ready.")

        self.btn_gen_another = ctk.CTkButton(
            r_head,
            text="🔄 Generate Another",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color="#261e21",
            text_color=TEXT_WHITE,
            hover_color=CARD_HOVER,
            border_width=1,
            border_color=CARD_BORDER,
            corner_radius=8,
            height=34,
            command=self._generate_fresh_topic,
        )
        self.btn_gen_another.pack_forget()
        self.btn_gen_another.destroy()
        self.btn_gen_another = ctk.CTkButton(
            left_col,
            text="▦   Generate Topic",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            fg_color=ACCENT_BLUE,
            text_color=TEXT_WHITE,
            hover_color="#008f77",
            height=52,
            corner_radius=12,
            border_width=0,
            command=self._generate_fresh_topic,
        )
        self.btn_gen_another.pack(fill="x", pady=(0, 12))

        self.hero_card = ctk.CTkFrame(
            right_col,
            fg_color=CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=CARD_BORDER,
        )
        self.hero_card.pack(fill="x", pady=(0, 16))

        hero_inner = ctk.CTkFrame(self.hero_card, fg_color="transparent")
        hero_inner.pack(fill="both", expand=True, padx=22, pady=22)

        tags_row = ctk.CTkFrame(hero_inner, fg_color="transparent")
        tags_row.pack(anchor="w", pady=(0, 12))

        self.pill_cat = ctk.CTkLabel(
            tags_row,
            text=f" ⚙️ {self.current_topic_data['category']} ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#172825",
            text_color=COLOR_CYAN,
            corner_radius=6,
        )
        self.pill_cat.pack(side="left", padx=(0, 8))

        self.pill_diff = ctk.CTkLabel(
            tags_row,
            text=f" 🔥 {self.current_topic_data['difficulty']} ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#2b141a",
            text_color=COLOR_RUBY,
            corner_radius=6,
        )
        self.pill_diff.pack(side="left")

        self.lbl_topic_title = ctk.CTkLabel(
            hero_inner,
            text=self.current_topic_data["title"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_WHITE,
            justify="left",
            wraplength=480,
            anchor="w",
        )
        self.lbl_topic_title.pack(anchor="w", pady=(0, 10))

        self.lbl_topic_desc = ctk.CTkLabel(
            hero_inner,
            text=self.current_topic_data["description"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
            justify="left",
            wraplength=480,
            anchor="w",
        )
        self.lbl_topic_desc.pack(anchor="w")

        details_card = ctk.CTkFrame(
            right_col,
            fg_color="#1e181a",
            corner_radius=14,
            border_width=1,
            border_color=CARD_BORDER,
        )
        details_card.pack(fill="x", pady=(0, 20))

        d_inner = ctk.CTkFrame(details_card, fg_color="transparent")
        d_inner.pack(fill="both", expand=True, padx=20, pady=16)

        d_head = ctk.CTkLabel(
            d_inner,
            text="Topic Details",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_WHITE,
        )
        d_head.pack(anchor="w", pady=(0, 12))

        self.lbl_d_cat = self._add_detail_row(d_inner, "⚙️  Category", self.current_topic_data["category"])
        self.lbl_d_time = self._add_detail_row(d_inner, "⏱️  Speaking Time", self.selected_duration["display"])
        self.lbl_d_diff = self._add_detail_row(d_inner, "📊  Difficulty Level", self.current_topic_data["difficulty"])

        fp_head = ctk.CTkLabel(
            d_inner,
            text="📝  Suggested Focus Points",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_MUTED,
        )
        fp_head.pack(anchor="w", pady=(10, 6))

        self.focus_points_frame = ctk.CTkFrame(d_inner, fg_color="transparent")
        self.focus_points_frame.pack(fill="x")

        self._render_focus_points()

        self.btn_start_prep = ctk.CTkButton(
            right_col,
            text="Start Preparation  ➔",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            fg_color=ACCENT_BLUE if self.current_topic_data.get("generated") else "#343438",
            hover_color="#008f77" if self.current_topic_data.get("generated") else "#343438",
            text_color=TEXT_WHITE if self.current_topic_data.get("generated") else TEXT_SUBTLE,
            height=50,
            state="normal" if self.current_topic_data.get("generated") else "disabled",
            corner_radius=12,
            command=self._advance_to_step2_prepare,
        )
        self.btn_start_prep.pack(fill="x", pady=(0, 16))

    def _add_detail_row(self, parent, label, val):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)

        l = ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
        )
        l.pack(side="left")

        v = ctk.CTkLabel(
            row,
            text=val,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_WHITE,
        )
        v.pack(side="right")
        return v

    def _render_focus_points(self):
        for w in self.focus_points_frame.winfo_children():
            w.destroy()

        for pt in self.current_topic_data.get("focus_points", []):
            pt_lbl = ctk.CTkLabel(
                self.focus_points_frame,
                text=f"•  {pt}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED,
                justify="left",
                wraplength=440,
                anchor="w",
            )
            pt_lbl.pack(anchor="w", pady=2)


    def _on_select_category(self, cat):
        self._topic_generation_id += 1
        self.selected_category = cat

        for c_id, (card, check_lbl) in self.category_card_widgets.items():
            if c_id == cat["id"]:
                card.configure(
                    fg_color=CARD_ACTIVE_BG,
                    border_color=CARD_ACTIVE_BORDER,
                    border_width=2,
                )
                check_lbl.configure(text="✓", fg_color=ACCENT_BLUE)
            else:
                card.configure(
                    fg_color=CARD_BG,
                    border_color=CARD_BORDER,
                    border_width=1,
                )
                check_lbl.configure(text="", fg_color="transparent")

        self.current_topic_data = self._empty_topic_data()
        self._apply_generated_topic_ui()
        if hasattr(self, "btn_gen_another") and self.btn_gen_another.winfo_exists():
            self.btn_gen_another.configure(text="▦   Generate Topic", state="normal")

    def _on_select_duration(self, dur):
        self.selected_duration = dur

        for s_val, (card, check_lbl) in self.duration_card_widgets.items():
            if s_val == dur["seconds"]:
                card.configure(
                    fg_color=CARD_ACTIVE_BG,
                    border_color=CARD_ACTIVE_BORDER,
                    border_width=2,
                )
                check_lbl.configure(text="✓", fg_color=ACCENT_BLUE)
            else:
                card.configure(
                    fg_color=CARD_BG,
                    border_color=CARD_BORDER,
                    border_width=1,
                )
                check_lbl.configure(text="", fg_color="transparent")

        if hasattr(self, "lbl_d_time"):
            self.lbl_d_time.configure(text=dur["display"])

    @staticmethod
    def _empty_topic_data():
        return {
            "title": "Your topic will appear here",
            "category": "Not generated",
            "difficulty": "Medium",
            "description": "Choose a category and click Generate Topic when you're ready.",
            "focus_points": [],
            "generated": False,
        }

    def _generate_fresh_topic(self):
        """Asynchronously query Gemini AI topic generator and update right-hand card."""
        self._topic_generation_id += 1
        generation_id = self._topic_generation_id
        if hasattr(self, "btn_gen_another") and self.btn_gen_another.winfo_exists():
            self.btn_gen_another.configure(text="⌛ Generating...", state="disabled")

        cat_backend = self.selected_category["backend_key"]
        category_name = self.selected_category["name"]

        def _worker():
            try:
                cat_name, topic_title = get_random_topic(cat_backend)
            except Exception:
                topic_title = "The Evolution of Modern Artificial Intelligence"

            if generation_id != self._topic_generation_id:
                return

            focus_pts = [
                f"Core foundations and key aspects of {topic_title.lower()}",
                "Practical examples and real-world relevance",
                "Perspectives, debates and potential challenges",
                "Key takeaway message and future outlook",
            ]

            desc = f"Examine the core themes and implications of '{topic_title}'. Share your thoughts, real-world examples, and structure a clear, engaging delivery."

            self.current_topic_data = {
                "title": topic_title,
                "category": category_name,
                "difficulty": "Medium",
                "description": desc,
                "focus_points": focus_pts,
                "generated": True,
            }

            self.safe_after(0, self._apply_generated_topic_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_generated_topic_ui(self):
        """Update right-hand card with new topic."""
        try:
            if hasattr(self, "pill_cat") and self.pill_cat.winfo_exists():
                self.pill_cat.configure(text=f" ⚙️ {self.current_topic_data['category']} ")
            if hasattr(self, "lbl_topic_title") and self.lbl_topic_title.winfo_exists():
                self.lbl_topic_title.configure(text=self.current_topic_data["title"])
            if hasattr(self, "lbl_topic_desc") and self.lbl_topic_desc.winfo_exists():
                self.lbl_topic_desc.configure(text=self.current_topic_data["description"])
            if hasattr(self, "lbl_d_cat") and self.lbl_d_cat.winfo_exists():
                self.lbl_d_cat.configure(text=self.current_topic_data["category"])
            if hasattr(self, "lbl_d_time") and self.lbl_d_time.winfo_exists():
                self.lbl_d_time.configure(text=self.selected_duration["display"])
            if hasattr(self, "btn_start_prep") and self.btn_start_prep.winfo_exists():
                generated = self.current_topic_data.get("generated", False)
                self.btn_start_prep.configure(
                    state="normal" if generated else "disabled",
                    fg_color=ACCENT_BLUE if generated else "#343438",
                    hover_color="#008f77" if generated else "#343438",
                    text_color=TEXT_WHITE if generated else TEXT_SUBTLE,
                )
            self._render_focus_points()

            if hasattr(self, "btn_gen_another") and self.btn_gen_another.winfo_exists():
                self.btn_gen_another.configure(text="🔄 Generate Another", state="normal")
        except Exception:
            pass



    def _advance_to_step2_prepare(self):
        """Construct Step 2: Prepare with AI matching mockup layout and features."""
        self._cancel_prep_timer()
        self.update_stepper(2)

        self.prep_time_total = 300
        self.prep_time_remaining = 300
        self.prep_timer_running = False
        self.prep_timer_after_id = None

        self.coach_session = None

        for w in self.practice_container.winfo_children():
            w.destroy()

        main_frame = ctk.CTkFrame(self.practice_container, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=6, uniform="step2_grid")
        main_frame.grid_columnconfigure(1, weight=4, uniform="step2_grid")

        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        step_tag = ctk.CTkLabel(
            header_frame,
            text="STEP 2 OF 4",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_CYAN,
        )
        step_tag.pack(anchor="w", pady=(0, 2))

        btn_back_top = ctk.CTkButton(
            header_frame,
            text="←  Back to Topic Selection",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color=CARD_BG,
            anchor="w",
            height=28,
            command=self._on_back_to_topics,
        )
        btn_back_top.pack(anchor="w", pady=(0, 4))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="Prepare with AI",
            font=ctk.CTkFont(family=FONT_FAMILY, size=32, weight="bold"),
            text_color=TEXT_WHITE,
        )
        title_lbl.pack(anchor="w", pady=(0, 2))

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Get insights, talking points and guidance before your speech.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
        )
        sub_lbl.pack(anchor="w")

        left_chat_card = ctk.CTkFrame(
            main_frame,
            fg_color="#19191B",
            corner_radius=16,
            border_width=1,
            border_color="#303033",
        )
        left_chat_card.grid(row=1, column=0, sticky="nsew", padx=(0, 14), pady=(0, 10))
        left_chat_card.grid_rowconfigure(1, weight=1)
        left_chat_card.grid_columnconfigure(0, weight=1)

        chat_top = ctk.CTkFrame(left_chat_card, fg_color="#202023", height=60, corner_radius=14)
        chat_top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        chat_top.pack_propagate(False)

        c_head_left = ctk.CTkFrame(chat_top, fg_color="transparent")
        c_head_left.pack(side="left", padx=14, pady=10)

        bot_icon_box = ctk.CTkFrame(c_head_left, width=38, height=38, corner_radius=19, fg_color="#172825")
        bot_icon_box.pack(side="left", padx=(0, 12))
        bot_icon_box.pack_propagate(False)

        bot_icon = ctk.CTkLabel(bot_icon_box, text="🤖", font=ctk.CTkFont(size=18))
        bot_icon.pack(expand=True)

        bot_title_box = ctk.CTkFrame(c_head_left, fg_color="transparent")
        bot_title_box.pack(side="left")

        coach_name = ctk.CTkLabel(
            bot_title_box,
            text="SpeakWise Coach",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_WHITE,
        )
        coach_name.pack(anchor="w")

        coach_sub = ctk.CTkLabel(
            bot_title_box,
            text="Your AI speaking assistant",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_CYAN,
        )
        coach_sub.pack(anchor="w")

        btn_clear = ctk.CTkButton(
            chat_top,
            text="🗑️ Clear Chat",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color="transparent",
            hover_color=CARD_HOVER,
            border_width=1,
            border_color=CARD_BORDER,
            text_color=TEXT_MUTED,
            corner_radius=8,
            height=32,
            command=self._clear_prep_chat,
        )
        btn_clear.pack(side="right", padx=14, pady=12)

        self.prep_chat_scroll = ctk.CTkScrollableFrame(left_chat_card, fg_color="transparent")
        self.prep_chat_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self.prep_chat_scroll.grid_columnconfigure(0, weight=1)

        bottom_chat_area = ctk.CTkFrame(left_chat_card, fg_color="transparent")
        bottom_chat_area.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 12))

        input_bar = ctk.CTkFrame(
            bottom_chat_area,
            fg_color="#1a1517",
            corner_radius=12,
            border_width=1,
            border_color=CARD_BORDER,
            height=48,
        )
        input_bar.pack(fill="x", pady=(0, 10))
        input_bar.pack_propagate(False)

        clip_lbl = ctk.CTkLabel(
            input_bar,
            text="📎",
            font=ctk.CTkFont(size=16),
            text_color=TEXT_SUBTLE,
            cursor="hand2",
            width=32,
        )
        clip_lbl.pack(side="left", padx=(10, 4))

        self.prep_entry = ctk.CTkEntry(
            input_bar,
            placeholder_text="Ask the AI coach anything...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="transparent",
            border_width=0,
            text_color=TEXT_WHITE,
            placeholder_text_color=TEXT_SUBTLE,
        )
        self.prep_entry.pack(side="left", fill="both", expand=True, padx=4)
        self.prep_entry.bind("<Return>", lambda e: self._on_prep_send_click())

        self.btn_prep_send = ctk.CTkButton(
            input_bar,
            text="➤",
            width=34,
            height=34,
            corner_radius=17,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#008f77",
            state="disabled",
            command=self._on_prep_send_click,
        )
        self.btn_prep_send.pack(side="right", padx=8, pady=7)

        pills_frame = ctk.CTkFrame(bottom_chat_area, fg_color="transparent")
        pills_frame.pack(fill="x")

        prompts = [
            "Give me a strong introduction",
            "What are the main theories?",
            "Give a conclusion idea",
            "Any interesting facts?",
        ]

        for p_text in prompts:
            p_btn = ctk.CTkButton(
                pills_frame,
                text=p_text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                fg_color="#261e21",
                hover_color=CARD_HOVER,
                border_width=1,
                border_color=CARD_BORDER,
                text_color=COLOR_ICE,
                corner_radius=14,
                height=28,
                command=lambda pt=p_text: self._send_quick_prompt(pt),
            )
            p_btn.pack(side="left", padx=(0, 6), pady=2)

        right_scroll = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        right_scroll.grid(row=1, column=1, sticky="nsew", padx=(14, 0), pady=(0, 10))
        right_scroll.grid_columnconfigure(0, weight=1)

        timer_card = ctk.CTkFrame(
            right_scroll,
            fg_color="#142321",
            corner_radius=14,
            border_width=1,
            border_color="#087D76",
        )
        timer_card.pack(fill="x", pady=(0, 14))

        t_inner = ctk.CTkFrame(timer_card, fg_color="transparent")
        t_inner.pack(fill="both", expand=True, padx=18, pady=16)

        t_head = ctk.CTkFrame(t_inner, fg_color="transparent")
        t_head.pack(fill="x", pady=(0, 8))

        t_icon_title = ctk.CTkLabel(
            t_head,
            text="⏱️  Preparation Time (5 Mins)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_WHITE,
        )
        t_icon_title.pack(side="left")

        clock_row = ctk.CTkFrame(t_inner, fg_color="transparent")
        clock_row.pack(fill="x", pady=(0, 8))

        mins = self.prep_time_remaining // 60
        secs = self.prep_time_remaining % 60
        self.lbl_prep_clock = ctk.CTkLabel(
            clock_row,
            text=f"{mins:02d}:{secs:02d}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=48, weight="bold"),
            text_color=TEXT_WHITE,
        )
        self.lbl_prep_clock.pack(side="left")

        self.btn_prep_pause = ctk.CTkButton(
            clock_row,
            text="⏸",
            width=46,
            height=46,
            corner_radius=23,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            fg_color="#261e21",
            hover_color=CARD_HOVER,
            text_color=TEXT_WHITE,
            command=self._toggle_prep_timer,
        )
        self.btn_prep_pause.pack(side="right")

        self.prep_pbar = ctk.CTkProgressBar(
            t_inner,
            height=6,
            corner_radius=3,
            progress_color=COLOR_TEAL,
            fg_color="#261e21",
        )
        self.prep_pbar.pack(fill="x", pady=(0, 6))
        self.prep_pbar.set(self.prep_time_remaining / self.prep_time_total)

        self.lbl_prep_sub = ctk.CTkLabel(
            t_inner,
            text="⏳ Waiting for AI Coach to connect...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_CYAN,
        )
        self.lbl_prep_sub.pack(anchor="w")

        overview_card = ctk.CTkFrame(
            right_scroll,
            fg_color="#19191B",
            corner_radius=14,
            border_width=1,
            border_color="#303033",
        )
        overview_card.pack(fill="x", pady=(0, 14))

        o_inner = ctk.CTkFrame(overview_card, fg_color="transparent")
        o_inner.pack(fill="both", expand=True, padx=18, pady=16)

        o_head_row = ctk.CTkFrame(o_inner, fg_color="transparent")
        o_head_row.pack(fill="x", pady=(0, 10))

        o_head_title = ctk.CTkLabel(
            o_head_row,
            text="📄  Topic Overview",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_WHITE,
        )
        o_head_title.pack(side="left")

        btn_chg_topic = ctk.CTkButton(
            o_head_row,
            text="🔄 Change Topic",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="transparent",
            hover_color=CARD_HOVER,
            border_width=1,
            border_color=CARD_BORDER,
            text_color=TEXT_MUTED,
            corner_radius=8,
            height=28,
            command=self._on_back_to_topics,
        )
        btn_chg_topic.pack(side="right")

        cur_title = self.current_topic_data.get("title", "The Voynich Manuscript")
        o_title = ctk.CTkLabel(
            o_inner,
            text=cur_title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
            text_color=TEXT_WHITE,
            justify="left",
            wraplength=380,
            anchor="w",
        )
        o_title.pack(anchor="w", pady=(0, 10))

        tags_row = ctk.CTkFrame(o_inner, fg_color="transparent")
        tags_row.pack(anchor="w", pady=(0, 10))

        cur_cat = self.current_topic_data.get("category", "History")
        cat_badge = ctk.CTkLabel(
            tags_row,
            text=f" 🏛️ {cur_cat} ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#2b141a",
            text_color=COLOR_RUBY,
            corner_radius=6,
        )
        cat_badge.pack(side="left", padx=(0, 6))

        cur_diff = self.current_topic_data.get("difficulty", "Medium")
        diff_badge = ctk.CTkLabel(
            tags_row,
            text=f" 📊 {cur_diff} ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#172825",
            text_color=COLOR_CYAN,
            corner_radius=6,
        )
        diff_badge.pack(side="left", padx=(0, 6))

        dur_text = self.selected_duration.get("display", "2 Minutes")
        dur_badge = ctk.CTkLabel(
            tags_row,
            text=f" ⏱️ {dur_text} ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#172825",
            text_color=COLOR_TEAL,
            corner_radius=6,
        )
        dur_badge.pack(side="left")

        cur_desc = self.current_topic_data.get(
            "description",
            "An unidentified manuscript written in an unknown script, filled with mysterious illustrations. Despite centuries of study, its meaning remains a mystery.",
        )
        o_desc = ctk.CTkLabel(
            o_inner,
            text=cur_desc,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
            justify="left",
            wraplength=380,
            anchor="w",
        )
        o_desc.pack(anchor="w")

        tip_card = ctk.CTkFrame(
            right_scroll,
            fg_color="#19191B",
            corner_radius=12,
            border_width=1,
            border_color="#303033",
        )
        tip_card.pack(fill="x", pady=(0, 14))

        tip_inner = ctk.CTkFrame(tip_card, fg_color="transparent")
        tip_inner.pack(fill="both", expand=True, padx=16, pady=14)

        tip_icon_box = ctk.CTkFrame(tip_inner, fg_color="transparent")
        tip_icon_box.pack(side="left", anchor="n", padx=(0, 10))

        tip_bulb = ctk.CTkLabel(tip_icon_box, text="💡", font=ctk.CTkFont(size=20))
        tip_bulb.pack()

        tip_content = ctk.CTkFrame(tip_inner, fg_color="transparent")
        tip_content.pack(side="left", fill="x", expand=True)

        tip_title = ctk.CTkLabel(
            tip_content,
            text="Pro Tip",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_CYAN,
        )
        tip_title.pack(anchor="w", pady=(0, 2))

        tip_text = ctk.CTkLabel(
            tip_content,
            text="Don't try to memorize a full speech. Focus on understanding the topic and organizing your ideas. Speak naturally!",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_ICE,
            justify="left",
            wraplength=330,
            anchor="w",
        )
        tip_text.pack(anchor="w")

        self.btn_start_speaking = ctk.CTkButton(
            right_scroll,
            text="Start Speaking Now 🎙️",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            fg_color="#343438",
            hover_color="#343438",
            text_color=TEXT_SUBTLE,
            corner_radius=26,
            height=52,
            state="disabled",
            command=self._advance_to_step3_speak,
        )
        self.btn_start_speaking.pack(fill="x", pady=(4, 16))

        self._render_coach_loading()
        self._init_coach_session_async()


    def _render_coach_loading(self):
        """Show animated waiting screen in chat while Gemini Flash initializes."""
        if not hasattr(self, "prep_chat_scroll") or not self.prep_chat_scroll.winfo_exists():
            return
        for w in self.prep_chat_scroll.winfo_children():
            w.destroy()

        row = ctk.CTkFrame(self.prep_chat_scroll, fg_color="transparent")
        row.pack(fill="x", pady=16, padx=8, anchor="w")

        avatar = ctk.CTkFrame(row, width=36, height=36, corner_radius=18, fg_color="#172825")
        avatar.pack(side="left", anchor="n", padx=(0, 10), pady=2)
        avatar.pack_propagate(False)

        a_lbl = ctk.CTkLabel(avatar, text="🤖", font=ctk.CTkFont(size=18))
        a_lbl.pack(expand=True)

        bubble = ctk.CTkFrame(
            row,
            fg_color="#1e181a",
            corner_radius=14,
            border_width=1,
            border_color=CARD_BORDER,
        )
        bubble.pack(side="left")

        msg_lbl = ctk.CTkLabel(
            bubble,
            text="⌛ Connecting to SpeakWise Coach via Gemini Flash...\nPreparing your speaking insights & talking points...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, slant="italic"),
            text_color=COLOR_CYAN,
            justify="left",
        )
        msg_lbl.pack(padx=16, pady=12, anchor="w")

    def _init_coach_session_async(self):
        """Initialize AI Coach multi-model fallback in a background thread."""
        user_name = self.current_user.get("name", "Rahul") if self.current_user else "Rahul"
        topic_title = self.current_topic_data.get("title", "Speech Practice")
        dur_desc = self.selected_duration.get("display", "2 Minutes")

        def _worker():
            session = None
            try:
                session = CoachChatSession(
                    topic=topic_title,
                    user_name=user_name,
                    speaking_time_desc=dur_desc,
                )
            except Exception:
                pass

            def _on_ready():
                self.coach_session = session
                if hasattr(self, "prep_chat_scroll") and self.prep_chat_scroll.winfo_exists():
                    for w in self.prep_chat_scroll.winfo_children():
                        w.destroy()
                    self._render_initial_ai_greeting()
                if hasattr(self, "btn_prep_send") and self.btn_prep_send.winfo_exists():
                    self.btn_prep_send.configure(state="normal")
                if hasattr(self, "lbl_prep_sub") and self.lbl_prep_sub.winfo_exists():
                    self.lbl_prep_sub.configure(
                        text="Preparation time is running! Speak naturally!",
                        text_color=COLOR_CYAN,
                    )
                self._start_prep_timer()

            self.safe_after(0, _on_ready)

        threading.Thread(target=_worker, daemon=True).start()

    def _render_initial_ai_greeting(self):
        """Render the rich initial greeting from the AI coach matching mockup."""
        first_name = "Rahul"
        if self.current_user and self.current_user.get("name"):
            first_name = self.current_user["name"].split()[0]

        topic = self.current_topic_data.get("title", "The Voynich Manuscript")
        welcome_text = (
            f"Hi {first_name}! 👋\n"
            f"I'm here to help you prepare for your speech on \"{topic}\".\n\n"
            f"This is a fascinating topic! I can help you with:\n"
            f"• Key points and structure\n"
            f"• Important facts and background\n"
            f"• Examples and interesting angles\n"
            f"• Tips on how to present it effectively\n\n"
            f"What would you like to explore first? You can also pick one of the quick prompts below!"
        )
        self._add_ai_bubble(welcome_text)

    def _add_ai_bubble(self, text, ts=None):
        """Render an AI Coach chat response bubble."""
        if not hasattr(self, "prep_chat_scroll") or not self.prep_chat_scroll.winfo_exists():
            return

        if not ts:
            ts = time.strftime("%I:%M %p")

        row = ctk.CTkFrame(self.prep_chat_scroll, fg_color="transparent")
        row.pack(fill="x", pady=6)

        av = ctk.CTkLabel(
            row,
            text="✨",
            width=32,
            height=32,
            corner_radius=16,
            fg_color="#172825",
            text_color=COLOR_CYAN,
            font=ctk.CTkFont(size=14),
        )
        av.pack(side="left", anchor="n", padx=(0, 10))

        content_col = ctk.CTkFrame(row, fg_color="transparent")
        content_col.pack(side="left", fill="x", expand=True)

        meta = ctk.CTkFrame(content_col, fg_color="transparent")
        meta.pack(fill="x", pady=(0, 3))

        n_lbl = ctk.CTkLabel(
            meta,
            text="AI Coach",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_WHITE,
        )
        n_lbl.pack(side="left")

        t_lbl = ctk.CTkLabel(
            meta,
            text=ts,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SUBTLE,
        )
        t_lbl.pack(side="left", padx=(8, 0))

        bubble = ctk.CTkFrame(
            content_col,
            fg_color="#1e181a",
            corner_radius=12,
            border_width=1,
            border_color=CARD_BORDER,
        )
        bubble.pack(fill="x", anchor="w")

        msg_lbl = ctk.CTkLabel(
            bubble,
            text=text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_ICE,
            justify="left",
            wraplength=480,
            anchor="w",
        )
        msg_lbl.pack(padx=16, pady=12, anchor="w")

        self.after(50, self._scroll_chat_to_bottom)

    def _add_user_bubble(self, text, ts=None):
        """Render a User message bubble."""
        if not hasattr(self, "prep_chat_scroll") or not self.prep_chat_scroll.winfo_exists():
            return

        if not ts:
            ts = time.strftime("%I:%M %p")

        first_name = "Rahul"
        if self.current_user and self.current_user.get("name"):
            first_name = self.current_user["name"].split()[0]
        initials = "".join([part[0].upper() for part in (self.current_user["name"] if self.current_user else "RK").split()[:2]]) or "RK"

        row = ctk.CTkFrame(self.prep_chat_scroll, fg_color="transparent")
        row.pack(fill="x", pady=6)

        content_col = ctk.CTkFrame(row, fg_color="transparent")
        content_col.pack(side="left", fill="x", expand=True)

        meta = ctk.CTkFrame(content_col, fg_color="transparent")
        meta.pack(fill="x", pady=(0, 3))

        t_lbl = ctk.CTkLabel(
            meta,
            text=ts,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SUBTLE,
        )
        t_lbl.pack(side="right", padx=(0, 8))

        n_lbl = ctk.CTkLabel(
            meta,
            text=first_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_WHITE,
        )
        n_lbl.pack(side="right")

        bubble = ctk.CTkFrame(
            content_col,
            fg_color="#172825",
            corner_radius=12,
            border_width=1,
            border_color="#00B295",
        )
        bubble.pack(fill="x", anchor="e")

        msg_lbl = ctk.CTkLabel(
            bubble,
            text=text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_WHITE,
            justify="left",
            wraplength=480,
            anchor="w",
        )
        msg_lbl.pack(padx=16, pady=12, anchor="w")

        av = ctk.CTkLabel(
            row,
            text=initials,
            width=32,
            height=32,
            corner_radius=16,
            fg_color=ACCENT_BLUE,
            text_color=TEXT_WHITE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
        )
        av.pack(side="left", anchor="n", padx=(10, 0))

        self.after(50, self._scroll_chat_to_bottom)

    def _scroll_chat_to_bottom(self):
        try:
            if hasattr(self, "prep_chat_scroll") and self.prep_chat_scroll.winfo_exists():
                self.prep_chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _on_prep_send_click(self):
        user_msg = self.prep_entry.get().strip()
        if not user_msg:
            return
        self.prep_entry.delete(0, "end")
        self._dispatch_user_message(user_msg)

    def _send_quick_prompt(self, prompt_text):
        self._dispatch_user_message(prompt_text)

    def _dispatch_user_message(self, user_msg):
        self._add_user_bubble(user_msg)

        if hasattr(self, "btn_prep_send"):
            self.btn_prep_send.configure(state="disabled")

        def _worker():
            reply = "I'm here to help you structure your speech. Feel free to ask about talking points, facts, or introduction ideas!"
            try:
                if self.coach_session:
                    reply = self.coach_session.send_message(user_msg)
            except Exception:
                pass

            def _update_ui():
                self._add_ai_bubble(reply)
                if hasattr(self, "btn_prep_send") and self.btn_prep_send.winfo_exists():
                    self.btn_prep_send.configure(state="normal")

            self.safe_after(0, _update_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def _clear_prep_chat(self):
        """Clear all chat messages and reset with initial AI greeting."""
        if hasattr(self, "prep_chat_scroll") and self.prep_chat_scroll.winfo_exists():
            for w in self.prep_chat_scroll.winfo_children():
                w.destroy()
            self._render_initial_ai_greeting()

    def _start_prep_timer(self):
        self.prep_timer_running = True
        if hasattr(self, "btn_start_speaking") and self.btn_start_speaking.winfo_exists():
            self.btn_start_speaking.configure(
                state="normal",
                fg_color=ACCENT_BLUE,
                hover_color="#008f77",
                text_color=TEXT_WHITE,
            )
        self._schedule_prep_tick()

    def _schedule_prep_tick(self):
        self._cancel_prep_timer()
        if self.prep_timer_running:
            self.prep_timer_after_id = self.after(1000, self._tick_prep_timer)

    def _cancel_prep_timer(self):
        if hasattr(self, "prep_timer_after_id") and self.prep_timer_after_id is not None:
            try:
                self.after_cancel(self.prep_timer_after_id)
            except Exception:
                pass
            self.prep_timer_after_id = None

    def _toggle_prep_timer(self):
        """Pause or resume preparation timer."""
        self.prep_timer_running = not self.prep_timer_running
        if hasattr(self, "btn_prep_pause") and self.btn_prep_pause.winfo_exists():
            if self.prep_timer_running:
                self.btn_prep_pause.configure(text="⏸")
                self._schedule_prep_tick()
            else:
                self.btn_prep_pause.configure(text="▶")
                self._cancel_prep_timer()

    def _tick_prep_timer(self):
        if not self.prep_timer_running:
            return

        if self.prep_time_remaining > 0:
            self.prep_time_remaining -= 1

        mins = self.prep_time_remaining // 60
        secs = self.prep_time_remaining % 60
        prog = max(0.0, self.prep_time_remaining / self.prep_time_total)

        if hasattr(self, "lbl_prep_clock") and self.lbl_prep_clock.winfo_exists():
            self.lbl_prep_clock.configure(text=f"{mins:02d}:{secs:02d}")
        if hasattr(self, "prep_pbar") and self.prep_pbar.winfo_exists():
            self.prep_pbar.set(prog)

        if self.prep_time_remaining > 0:
            self._schedule_prep_tick()
        else:
            self.prep_timer_running = False
            if hasattr(self, "btn_prep_pause") and self.btn_prep_pause.winfo_exists():
                self.btn_prep_pause.configure(text="▶")

    def _on_back_to_topics(self):
        """Cancel prep timer and return to Step 1 Topic Selection."""
        self._cancel_prep_timer()
        self._build_step1_topic_selection()



    def _advance_to_step3_speak(self):
        """Construct Step 3: Live Speech Recording with embedded camera and circular timer."""
        self._cancel_prep_timer()
        self.update_stepper(3)

        for w in self.practice_container.winfo_children():
            w.destroy()

        dur = self.selected_duration["seconds"]
        session_stop_event = threading.Event()
        self.stop_recording_event = session_stop_event

        main_frame = ctk.CTkFrame(self.practice_container, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=64, uniform="step3_grid")
        main_frame.grid_columnconfigure(1, weight=36, uniform="step3_grid")

        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="It's Time to Speak!",
            font=ctk.CTkFont(family=FONT_FAMILY, size=30, weight="bold"),
            text_color=TEXT_WHITE,
        )
        title_lbl.pack(anchor="w", pady=(0, 2))

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Speak on the given topic. Be yourself, speak clearly, and do your best!",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
        )
        sub_lbl.pack(anchor="w")

        left_col = ctk.CTkFrame(
            main_frame,
            fg_color=CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=CARD_BORDER,
        )
        left_col.grid(row=1, column=0, sticky="nsew", padx=(0, 14), pady=(0, 10))
        left_col.grid_rowconfigure(1, weight=1)
        left_col.grid_columnconfigure(0, weight=1)

        top_info_bar = ctk.CTkFrame(left_col, fg_color="transparent", height=54)
        top_info_bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))

        t_left = ctk.CTkFrame(top_info_bar, fg_color="transparent")
        t_left.pack(side="left")

        doc_icon_box = ctk.CTkFrame(t_left, width=36, height=36, corner_radius=10, fg_color="#2b2326")
        doc_icon_box.pack(side="left", padx=(0, 10))
        doc_icon_box.pack_propagate(False)

        doc_icon = ctk.CTkLabel(doc_icon_box, text="📄", font=ctk.CTkFont(size=16))
        doc_icon.pack(expand=True)

        t_text_box = ctk.CTkFrame(t_left, fg_color="transparent")
        t_text_box.pack(side="left")

        t_caption = ctk.CTkLabel(
            t_text_box,
            text="Your Topic",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SUBTLE,
        )
        t_caption.pack(anchor="w")

        t_title = ctk.CTkLabel(
            t_text_box,
            text=self.current_topic_data.get("title", "The Voynich Manuscript"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_WHITE,
            justify="left",
            wraplength=480,
            anchor="w",
        )
        t_title.pack(anchor="w")

        t_right = ctk.CTkFrame(top_info_bar, fg_color="transparent")
        t_right.pack(side="right")

        dur_caption = ctk.CTkLabel(
            t_right,
            text="Speaking Time",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SUBTLE,
        )
        dur_caption.pack(anchor="e")

        dur_val = ctk.CTkLabel(
            t_right,
            text=f"⏱️  {self.selected_duration.get('display', '2 Minutes')}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_CYAN,
        )
        dur_val.pack(anchor="e")

        cam_status_card = ctk.CTkFrame(
            left_col,
            fg_color="#181315",
            corner_radius=14,
            border_width=1,
            border_color="#2b2225",
        )
        cam_status_card.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 14))
        cam_status_card.grid_rowconfigure(0, weight=1)
        cam_status_card.grid_columnconfigure(0, weight=1)

        cam_center = ctk.CTkFrame(cam_status_card, fg_color="transparent")
        cam_center.grid(row=0, column=0)

        icon_box = ctk.CTkFrame(cam_center, width=80, height=80, corner_radius=40, fg_color="#172825")
        icon_box.pack(pady=(0, 16))
        icon_box.pack_propagate(False)

        cam_icon = ctk.CTkLabel(icon_box, text="🎥", font=ctk.CTkFont(size=36))
        cam_icon.pack(expand=True)

        cam_title = ctk.CTkLabel(
            cam_center,
            text="Camera Active in Dedicated Window",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_WHITE,
        )
        cam_title.pack(pady=(0, 6))

        cam_desc = ctk.CTkLabel(
            cam_center,
            text="Your camera feed is live in the 'SpeakWise Camera' window.\nLook naturally at the camera while delivering your speech.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
            justify="center",
        )
        cam_desc.pack(pady=(0, 16))

        pill_box = ctk.CTkLabel(
            cam_center,
            text="  💡 Press 'q' in the camera window or click 'Stop Recording' below to finish early.  ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#172825",
            text_color=COLOR_CYAN,
            corner_radius=8,
            height=30,
        )
        pill_box.pack()

        dev_row = ctk.CTkFrame(left_col, fg_color="transparent")
        dev_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))

        badges = [
            ("camera", "🎥", "Camera Window\nLive (Active)", "#172825", COLOR_CYAN),
            ("mic", "🎙️", "Microphone\nRecording", "#172825", COLOR_CYAN),
            ("preview", "👁️", "Eye Contact\nTracking On", "#221c1e", COLOR_ICE),
        ]

        for _, icon, txt, bg_circle, text_col in badges:
            card = ctk.CTkFrame(
                dev_row,
                fg_color="#1c1719",
                corner_radius=10,
                border_width=1,
                border_color=CARD_BORDER,
                height=48,
            )
            card.pack(side="left", fill="x", expand=True, padx=4)

            c_box = ctk.CTkFrame(card, width=32, height=32, corner_radius=16, fg_color=bg_circle)
            c_box.pack(side="left", padx=(10, 8), pady=8)
            c_box.pack_propagate(False)

            i_lbl = ctk.CTkLabel(c_box, text=icon, font=ctk.CTkFont(size=13))
            i_lbl.pack(expand=True)

            t_lbl = ctk.CTkLabel(
                card,
                text=txt,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=TEXT_WHITE,
                justify="left",
            )
            t_lbl.pack(side="left", pady=6)

        right_col = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_col.grid(row=1, column=1, sticky="nsew", padx=(14, 0), pady=(0, 10))
        right_col.grid_columnconfigure(0, weight=1)

        timer_card = ctk.CTkFrame(
            right_col,
            fg_color=CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=CARD_BORDER,
        )
        timer_card.pack(fill="x", pady=(0, 14))

        t_inner = ctk.CTkFrame(timer_card, fg_color="transparent")
        t_inner.pack(fill="both", expand=True, padx=18, pady=16)

        t_h_lbl = ctk.CTkLabel(
            t_inner,
            text="⏱️  Time Remaining",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_WHITE,
        )
        t_h_lbl.pack(anchor="w", pady=(0, 6))

        self.ring_canvas = tk.Canvas(
            t_inner,
            width=180,
            height=180,
            bg="#221c1e",
            highlightthickness=0,
        )
        self.ring_canvas.pack(pady=(4, 8))
        self._draw_timer_ring(dur, dur)

        sub_encourage = ctk.CTkLabel(
            t_inner,
            text="Keep going! You're doing great!",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_CYAN,
        )
        sub_encourage.pack()

        self.btn_stop_rec = ctk.CTkButton(
            right_col,
            text="⏹   Stop Recording",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color="#2b141a",
            hover_color="#3d1b24",
            border_width=1,
            border_color=COLOR_RUBY,
            text_color=COLOR_RUBY,
            corner_radius=10,
            height=48,
            command=self._stop_recording_early,
        )
        self.btn_stop_rec.pack(fill="x", pady=(2, 10))

        audio_path, video_path = generate_recording_paths()
        self.audio_path = audio_path
        self.video_path = video_path

        def _rec_thread():
            def update_timer(remaining, total):
                self.safe_after(0, lambda r=remaining, d=total: self._draw_timer_ring(r, d))

            self.recording_status, _timing = record_session(
                dur,
                audio_path,
                video_path,
                stop_event=session_stop_event,
                show_window=True,
                on_tick=update_timer,
            )

            self.safe_after(0, self._advance_to_step4_results)

        threading.Thread(target=_rec_thread, daemon=True).start()

    def _draw_timer_ring(self, rem_seconds, total_seconds):
        """Draw the circular ring countdown timer on the Tkinter canvas."""
        try:
            if not hasattr(self, "ring_canvas") or not self.ring_canvas.winfo_exists():
                return

            self.ring_canvas.delete("all")
            rem = max(0.0, rem_seconds)
            mins = int(rem) // 60
            secs = int(rem) % 60
            prog = max(0.0, min(1.0, rem / total_seconds)) if total_seconds > 0 else 0.0

            cx, cy, r = 90, 90, 68
            x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r

            self.ring_canvas.create_arc(
                x0, y0, x1, y1,
                start=0, extent=359.9,
                style="arc",
                outline="#352b2e",
                width=8,
            )

            extent_angle = -(359.9 * prog)
            if abs(extent_angle) > 0.5:
                self.ring_canvas.create_arc(
                    x0, y0, x1, y1,
                    start=90, extent=extent_angle,
                    style="arc",
                    outline=COLOR_CYAN,
                    width=8,
                )

            self.ring_canvas.create_text(
                cx, cy,
                text=f"{mins:02d}:{secs:02d}",
                fill="#ffffff",
                font=(FONT_FAMILY, 30, "bold"),
            )
        except Exception:
            pass

    def _stop_recording_early(self):
        """Signal recording threads to stop immediately and advance to results."""
        if hasattr(self, "stop_recording_event"):
            self.stop_recording_event.set()
        if hasattr(self, "btn_stop_rec") and self.btn_stop_rec.winfo_exists():
            self.btn_stop_rec.configure(text="⏳ Stopping...", state="disabled")


    def _advance_to_step4_results(self):
        self.update_stepper(4)

        for w in self.practice_container.winfo_children():
            w.destroy()

        loading_box = ctk.CTkFrame(self.practice_container, fg_color="transparent")
        loading_box.pack(pady=100)

        l_title = ctk.CTkLabel(
            loading_box,
            text="⚙️ Analyzing Speech, Video & Audio...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
            text_color=ACCENT_CYAN,
        )
        l_title.pack(pady=(0, 10))

        l_sub = ctk.CTkLabel(
            loading_box,
            text="Transcribing audio with CrisperWhisper, measuring eye contact, and diagnosing 'What Went Wrong'...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
        )
        l_sub.pack()

        def _analysis_job():
            video_report = None
            recording_status = getattr(self, "recording_status", {})
            video_status = "unavailable"
            video_error = recording_status.get("video_error")
            if recording_status.get("video_analysis_eligible", True):
                try:
                    video_report = analyze_video(self.video_path)
                    video_status = video_report.get("analysis_status", "success") if video_report else "unavailable"
                    video_error = video_report.get("analysis_error") or video_error
                except Exception as error:
                    video_status = "failed"
                    video_error = str(error)

            audio_duration = get_audio_duration(self.audio_path)
            audio_status = "available" if recording_status.get("audio_recording_valid") and audio_duration > 0 and not recording_status.get("audio_error") else "unavailable"
            if recording_status.get("audio_error"):
                transcription_result = {"text": "", "status": "failed", "error": recording_status["audio_error"]}
            else:
                transcription_result = transcribe_audio_detailed(self.audio_path)
            transcription = transcription_result["text"]
            total_words = count_words(transcription)

            fillers = detect_fillers(transcription)
            total_fillers = sum(fillers.values())
            pauses, pause_error = detect_pauses_detailed(self.audio_path)
            pause_status = "available" if pause_error is None else "unavailable"

            relevance_res = None
            try:
                relevance_res = analyze_relevance(self.current_topic_data["title"], transcription)
            except Exception:
                logging.getLogger(__name__).exception("Topic relevance analysis failed")

            target_duration = self.selected_duration["seconds"]
            dur = audio_duration or target_duration

            report_data = print_report(
                video_report=video_report,
                total_words=total_words,
                total_fillers=total_fillers,
                pauses=pauses,
                duration=dur,
                transcription=transcription,
                topic=self.current_topic_data["title"],
                relevance_result=relevance_res,
                filler_breakdown=fillers,
                transcription_status=transcription_result["status"],
                transcription_error=transcription_result.get("error"),
                audio_status=audio_status,
                video_status=video_status,
                video_error=video_error,
                pause_status=pause_status,
                pause_error=pause_error,
            )

            if self.current_user:
                try:
                    save_speech_session(
                        user_id=self.current_user["user_id"],
                        category=self.selected_category["name"],
                        topic_name=self.current_topic_data["title"],
                        speaking_time=target_duration,
                        audio_path=self.audio_path,
                        video_path=self.video_path,
                        transcription=transcription,
                        report=report_data,
                    )
                except Exception:
                    pass
            else:
                self.last_unsaved_session = {
                    "category": self.selected_category["name"],
                    "topic_name": self.current_topic_data["title"],
                    "speaking_time": target_duration,
                    "audio_path": self.audio_path,
                    "video_path": self.video_path,
                    "transcription": transcription,
                    "report": report_data,
                }

            self.safe_after(0, lambda: self._render_results_ui(report_data, transcription))

        threading.Thread(target=_analysis_job, daemon=True).start()

    def _render_results_ui(self, rep, transcription):
        """Render results into practice container and cache latest session."""
        self.latest_report_data = rep
        self.latest_transcription = transcription
        self.latest_session_date = time.strftime("%d %b %Y, %I:%M %p")
        self._render_speech_report(
            self.practice_container,
            rep=rep,
            transcription=transcription,
            session_date=self.latest_session_date,
            video_path=getattr(self, "video_path", None),
            audio_path=getattr(self, "audio_path", None),
            back_callback=self._end_session,
        )

    def _create_reports_view(self):
        """Build standalone Reports navigation page."""
        self.reports_container = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        self.reports_container.grid_columnconfigure(0, weight=1)
        self.reports_container.grid_rowconfigure(0, weight=1)
        self._render_speech_report(self.reports_container)
        return self.reports_container


    def _render_speech_report(self, container, rep=None, transcription=None, session_date=None, back_callback=None, video_path=None, audio_path=None):
        """Render a modern, high-fidelity Speech Report dashboard using actual recorded metrics."""
        for w in container.winfo_children():
            w.destroy()

        if rep is None:
            rep = getattr(self, "latest_report_data", None)

        if rep is None:
            empty_box = ctk.CTkFrame(container, fg_color="transparent")
            empty_box.pack(expand=True, fill="both", padx=40, pady=60)

            icon_lbl = ctk.CTkLabel(empty_box, text="🎙️", font=ctk.CTkFont(size=64))
            icon_lbl.pack(pady=(40, 16))

            empty_title = ctk.CTkLabel(
                empty_box,
                text="No Speech Sessions Yet",
                font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
                text_color=TEXT_WHITE,
            )
            empty_title.pack(pady=(0, 8))

            empty_sub = ctk.CTkLabel(
                empty_box,
                text="Start an extempore practice session to analyze your speech pacing, filler words, eye contact, and get instant AI diagnostics.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=TEXT_MUTED,
                wraplength=460,
                justify="center",
            )
            empty_sub.pack(pady=(0, 24))

            btn_start = ctk.CTkButton(
                empty_box,
                text="Start Practice Session  ➔",
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                fg_color=ACCENT_BLUE,
                hover_color="#2563eb",
                height=46,
                corner_radius=10,
                command=self.start_new_practice_session,
            )
            btn_start.pack()
            return

        report_body = ctk.CTkFrame(container, fg_color="transparent")
        report_body.pack(fill="both", expand=True, padx=(0, 20), pady=(0, 8))
        report_body.grid_rowconfigure(0, weight=0)
        report_body.grid_rowconfigure(1, weight=0)
        report_body.grid_rowconfigure(2, weight=0)
        report_body.grid_rowconfigure(3, weight=1)
        report_body.grid_columnconfigure(0, weight=1, uniform="report_col")
        report_body.grid_columnconfigure(1, weight=1, uniform="report_col")

        topic_title = rep.get("topic") or getattr(self, "current_topic_data", {}).get("title", "Speech Practice")
        category_name = rep.get("category") or getattr(self, "selected_category", {}).get("name", "General")
        spk_time_sec = rep.get("duration") or rep.get("speaking_time", 60)
        target_time_sec = rep.get("target_time") or getattr(self, "selected_duration", {}).get("seconds", spk_time_sec)
        diff_level = rep.get("difficulty", "Standard")

        total_words = rep.get("total_words", 0)
        total_fillers = rep.get("total_fillers", 0)
        filler_breakdown = rep.get("filler_breakdown", {})
        filler_pct = rep.get("filler_pct", (total_fillers / total_words * 100.0) if total_words > 0 else 0.0)
        pace_wpm = rep.get("pace_wpm", int(round(total_words / (spk_time_sec / 60.0))) if spk_time_sec > 0 else 0)
        pauses_list = rep.get("pauses_list", rep.get("pauses", []))
        if not isinstance(pauses_list, list):
            pauses_list = []

        eye_pct = rep.get("eye_contact_pct")
        head_pct = rep.get("head_centering_pct")
        eye_pct_label = f"{eye_pct:.0f}%" if eye_pct is not None else "N/A"
        head_pct_label = f"{head_pct:.0f}%" if head_pct is not None else "N/A"
        overall_val = float(rep.get("overall", 0.0))
        is_silent = rep.get("is_silent", total_words == 0)

        actual_video_path = video_path if video_path is not None else getattr(self, "video_path", None)

        if not session_date:
            session_date = getattr(self, "latest_session_date", time.strftime("%d %b %Y, %I:%M %p"))

        top_header = ctk.CTkFrame(report_body, fg_color="transparent")
        top_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        h_left = ctk.CTkFrame(top_header, fg_color="transparent")
        h_left.pack(side="left")

        back_cmd = back_callback if back_callback else self._end_session
        is_from_history = (back_callback is not None and back_callback != self._end_session)
        back_btn_text = "←  Back to History" if is_from_history else "←  Back to Home"

        btn_back_hist = ctk.CTkButton(
            h_left,
            text=back_btn_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color=CARD_BG,
            anchor="w",
            height=26,
            command=back_cmd,
        )
        btn_back_hist.pack(anchor="w", pady=(0, 2))

        title_row = ctk.CTkFrame(h_left, fg_color="transparent")
        title_row.pack(anchor="w", pady=(0, 2))

        rep_title = ctk.CTkLabel(
            title_row,
            text="Speech Performance Report",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_WHITE,
        )
        rep_title.pack(side="left", padx=(0, 12))

        analysis_unavailable = rep.get("transcription_status") in ("failed", "audio_missing") or rep.get("audio_status") == "unavailable"
        analysis_partial = rep.get("video_status") != "success" or rep.get("pause_status") != "available"
        if analysis_unavailable:
            badge_txt = "Analysis Unavailable"
        elif analysis_partial:
            badge_txt = "Partial Analysis"
        elif is_silent:
            badge_txt = "No Speech Detected"
        elif overall_val >= 8.0:
            badge_txt = "Outstanding"
        elif overall_val >= 5.5:
            badge_txt = "Solid Effort"
        else:
            badge_txt = "Practice Needed"
        badge_fg = "#2b141a" if (is_silent or analysis_unavailable or analysis_partial) else ("#172825" if overall_val >= 8.0 else ("#221c1e" if overall_val >= 5.5 else "#2b141a"))
        badge_tc = COLOR_RUBY if (is_silent or analysis_unavailable or analysis_partial) else (COLOR_CYAN if overall_val >= 8.0 else (COLOR_ICE if overall_val >= 5.5 else COLOR_RUBY))

        stat_badge = ctk.CTkLabel(
            title_row,
            text=f"  {badge_txt}  ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=badge_fg,
            text_color=badge_tc,
            corner_radius=8,
            height=24,
        )
        stat_badge.pack(side="left")

        rep_sub = ctk.CTkLabel(
            h_left,
            text=f"Comprehensive AI speech delivery & visual presence diagnostics for \"{topic_title}\".",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        )
        rep_sub.pack(anchor="w")

        h_right = ctk.CTkFrame(top_header, fg_color="transparent")
        h_right.pack(side="right")

        date_box = ctk.CTkFrame(h_right, fg_color="transparent")
        date_box.pack(side="left", padx=(0, 16))

        d_cap = ctk.CTkLabel(
            date_box,
            text="Session Date",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SUBTLE,
        )
        d_cap.pack(anchor="e")

        d_val = ctk.CTkLabel(
            date_box,
            text=f"📅 {session_date}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_WHITE,
        )
        d_val.pack(anchor="e")

        btn_again_top = ctk.CTkButton(
            h_right,
            text="Practice Again  ➔",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#008f77",
            text_color=TEXT_WHITE,
            corner_radius=8,
            height=36,
            command=self.start_new_practice_session,
        )
        btn_again_top.pack(side="left", padx=(0, 8))

        btn_end_sess_top = ctk.CTkButton(
            h_right,
            text="⏹️  End Session",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color="#2b141a",
            hover_color="#3d1b24",
            border_width=1,
            border_color=COLOR_RUBY,
            text_color=COLOR_RUBY,
            corner_radius=8,
            height=36,
            command=self._end_session,
        )
        btn_end_sess_top.pack(side="left")

        metrics_row = ctk.CTkFrame(report_body, fg_color="transparent")
        metrics_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        for i in range(4):
            metrics_row.grid_columnconfigure(i, weight=1, uniform="m_card")

        c1 = ctk.CTkFrame(metrics_row, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        c1.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        c1_in = ctk.CTkFrame(c1, fg_color="transparent")
        c1_in.pack(fill="both", expand=True, padx=14, pady=10)

        icon1 = ctk.CTkLabel(c1_in, text="📄", font=ctk.CTkFont(size=18), width=34, height=34, corner_radius=10, fg_color="#2b2326")
        icon1.pack(side="left", padx=(0, 10))

        c1_text = ctk.CTkFrame(c1_in, fg_color="transparent")
        c1_text.pack(side="left", fill="x", expand=True)

        ct1 = ctk.CTkLabel(c1_text, text="Speech Topic", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SUBTLE)
        ct1.pack(anchor="w")
        cv1 = ctk.CTkLabel(c1_text, text=topic_title, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_WHITE, justify="left", wraplength=170)
        cv1.pack(anchor="w", pady=(0, 3))
        tag1 = ctk.CTkLabel(c1_text, text=f" 🎯 {category_name} ", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#172825", text_color=COLOR_CYAN, corner_radius=6)
        tag1.pack(anchor="w")

        c2 = ctk.CTkFrame(metrics_row, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        c2.grid(row=0, column=1, padx=4, sticky="nsew")
        c2_in = ctk.CTkFrame(c2, fg_color="transparent")
        c2_in.pack(fill="both", expand=True, padx=14, pady=10)

        icon2 = ctk.CTkLabel(c2_in, text="⏱️", font=ctk.CTkFont(size=18), width=34, height=34, corner_radius=10, fg_color="#2b2326")
        icon2.pack(side="left", padx=(0, 10))

        c2_text = ctk.CTkFrame(c2_in, fg_color="transparent")
        c2_text.pack(side="left", fill="x", expand=True)

        ct2 = ctk.CTkLabel(c2_text, text="Speaking Duration", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SUBTLE)
        ct2.pack(anchor="w")
        time_m = spk_time_sec // 60
        time_s = spk_time_sec % 60
        cv2 = ctk.CTkLabel(c2_text, text=f"{time_m}:{time_s:02d}", font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"), text_color=TEXT_WHITE)
        cv2.pack(anchor="w", pady=(0, 2))
        tgt_m = target_time_sec // 60
        tgt_s = target_time_sec % 60
        cs2 = ctk.CTkLabel(c2_text, text=f"Target: {tgt_m}:{tgt_s:02d} | Words: {total_words}", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_SUBTLE)
        cs2.pack(anchor="w")

        c3 = ctk.CTkFrame(metrics_row, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        c3.grid(row=0, column=2, padx=4, sticky="nsew")
        c3_in = ctk.CTkFrame(c3, fg_color="transparent")
        c3_in.pack(fill="both", expand=True, padx=14, pady=10)

        icon3 = ctk.CTkLabel(c3_in, text="👁️", font=ctk.CTkFont(size=18), width=34, height=34, corner_radius=10, fg_color="#172825")
        icon3.pack(side="left", padx=(0, 10))

        c3_text = ctk.CTkFrame(c3_in, fg_color="transparent")
        c3_text.pack(side="left", fill="x", expand=True)

        ct3 = ctk.CTkLabel(c3_text, text="Eye Contact & Presence", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SUBTLE)
        ct3.pack(anchor="w")
        cv3 = ctk.CTkLabel(c3_text, text=f"{eye_pct_label} Contact", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=COLOR_CYAN)
        cv3.pack(anchor="w", pady=(0, 2))
        cs3 = ctk.CTkLabel(c3_text, text=f"Head Steady: {head_pct_label}", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_SUBTLE)
        cs3.pack(anchor="w")

        c4 = ctk.CTkFrame(metrics_row, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        c4.grid(row=0, column=3, padx=(8, 0), sticky="nsew")
        c4_in = ctk.CTkFrame(c4, fg_color="transparent")
        c4_in.pack(fill="both", expand=True, padx=14, pady=10)

        icon4 = ctk.CTkLabel(c4_in, text="🏆", font=ctk.CTkFont(size=18), width=34, height=34, corner_radius=10, fg_color="#2b2326")
        icon4.pack(side="left", padx=(0, 10))

        c4_text = ctk.CTkFrame(c4_in, fg_color="transparent")
        c4_text.pack(side="left", fill="x", expand=True)

        ct4 = ctk.CTkLabel(c4_text, text="Overall Score", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SUBTLE)
        ct4.pack(anchor="w")

        score_box = ctk.CTkFrame(c4_text, fg_color="transparent")
        score_box.pack(anchor="w", pady=(0, 2))

        cv4_big = ctk.CTkLabel(score_box, text=f"{overall_val:.1f}", font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"), text_color=TEXT_WHITE)
        cv4_big.pack(side="left")
        cv4_sub = ctk.CTkLabel(score_box, text=" / 10", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=TEXT_MUTED)
        cv4_sub.pack(side="left", padx=(2, 0))

        rating_color = COLOR_RUBY if is_silent else (COLOR_CYAN if overall_val >= 7.0 else (COLOR_ICE if overall_val >= 5.0 else COLOR_RUBY))
        rating_msg = "No speech detected" if is_silent else ("Great performance!" if overall_val >= 7.0 else ("Room to improve" if overall_val >= 5.0 else "Needs practice"))
        cs4 = ctk.CTkLabel(c4_text, text=rating_msg, font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=rating_color)
        cs4.pack(anchor="w")

        row_3 = ctk.CTkFrame(report_body, fg_color="transparent")
        row_3.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        for c_idx in range(3):
            row_3.grid_columnconfigure(c_idx, weight=1, uniform="sub3")

        mc1 = ctk.CTkFrame(row_3, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        mc1.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        mc1_in = ctk.CTkFrame(mc1, fg_color="transparent")
        mc1_in.pack(fill="both", expand=True, padx=14, pady=10)

        mc1_h = ctk.CTkLabel(mc1_in, text="🗣️  Speaking Pace", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=TEXT_WHITE)
        mc1_h.pack(anchor="w", pady=(0, 4))

        pace_cv = tk.Canvas(mc1_in, width=140, height=72, bg="#221c1e", highlightthickness=0)
        pace_cv.pack(pady=(2, 6))
        self._draw_pace_gauge(pace_cv, pace_wpm if not is_silent else 0)

        analysis_unavailable = rep.get("transcription_status") in ("failed", "audio_missing") or rep.get("audio_status") == "unavailable"
        if analysis_unavailable:
            pace_badge_text = " Analysis unavailable "
            pace_badge_bg = "#2b141a"
            pace_badge_tc = COLOR_RUBY
        elif is_silent:
            pace_badge_text = " 0 WPM (Silent) "
            pace_badge_bg = "#2b141a"
            pace_badge_tc = COLOR_RUBY
        elif 120 <= pace_wpm <= 160:
            pace_badge_text = " Ideal (120–160 wpm) "
            pace_badge_bg = "#172825"
            pace_badge_tc = COLOR_CYAN
        elif pace_wpm < 120:
            pace_badge_text = f" Slow ({pace_wpm} wpm) "
            pace_badge_bg = "#2b2326"
            pace_badge_tc = COLOR_ICE
        else:
            pace_badge_text = f" Fast ({pace_wpm} wpm) "
            pace_badge_bg = "#2b141a"
            pace_badge_tc = COLOR_RUBY

        mc1_badge = ctk.CTkLabel(mc1_in, text=pace_badge_text, font=ctk.CTkFont(size=10, weight="bold"), fg_color=pace_badge_bg, text_color=pace_badge_tc, corner_radius=6)
        mc1_badge.pack()

        mc2 = ctk.CTkFrame(row_3, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        mc2.grid(row=0, column=1, padx=4, sticky="nsew")
        mc2_in = ctk.CTkFrame(mc2, fg_color="transparent")
        mc2_in.pack(fill="both", expand=True, padx=14, pady=10)

        mc2_h = ctk.CTkLabel(mc2_in, text="💬  Filler Words", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=TEXT_WHITE)
        mc2_h.pack(anchor="w", pady=(0, 4))

        donut_row = ctk.CTkFrame(mc2_in, fg_color="transparent")
        donut_row.pack(fill="x", pady=(2, 4))

        donut_cv = tk.Canvas(donut_row, width=64, height=64, bg="#221c1e", highlightthickness=0)
        donut_cv.pack(side="left", padx=(0, 6))
        self._draw_donut(donut_cv, total_fillers)

        f_list_box = ctk.CTkFrame(donut_row, fg_color="transparent")
        f_list_box.pack(side="left", fill="x", expand=True)

        if filler_breakdown:
            for f_word, f_num in list(filler_breakdown.items())[:3]:
                fl = ctk.CTkLabel(f_list_box, text=f"• {f_word} ({f_num})", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_MUTED)
                fl.pack(anchor="w")
        else:
            fl_none = ctk.CTkLabel(f_list_box, text="No fillers detected", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_SUBTLE)
            fl_none.pack(anchor="w")

        f_badge_txt = " 0% fillers (Clean) " if total_fillers == 0 else f" {total_fillers} fillers ({filler_pct:.1f}%) "
        f_badge_bg = "#172825" if total_fillers <= 2 else "#2b141a"
        f_badge_tc = COLOR_CYAN if total_fillers <= 2 else COLOR_RUBY
        mc2_badge = ctk.CTkLabel(mc2_in, text=f_badge_txt, font=ctk.CTkFont(size=9, weight="bold"), fg_color=f_badge_bg, text_color=f_badge_tc, corner_radius=6)
        mc2_badge.pack()

        mc3 = ctk.CTkFrame(row_3, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        mc3.grid(row=0, column=2, padx=(6, 0), sticky="nsew")
        mc3_in = ctk.CTkFrame(mc3, fg_color="transparent")
        mc3_in.pack(fill="both", expand=True, padx=14, pady=10)

        mc3_h = ctk.CTkLabel(mc3_in, text="⏸️  Pauses & Rhythm", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=TEXT_WHITE)
        mc3_h.pack(anchor="w", pady=(0, 4))

        ring_time_cv = tk.Canvas(mc3_in, width=64, height=64, bg="#221c1e", highlightthickness=0)
        ring_time_cv.pack(pady=(2, 6))
        self._draw_time_ring_mini(ring_time_cv, spk_time_sec, target_time_sec)

        num_p = len(pauses_list)
        p_badge_txt = " Natural flow " if (num_p <= 3 and total_words > 10) else f" {num_p} pauses (>=0.5s) "
        mc3_badge = ctk.CTkLabel(mc3_in, text=p_badge_txt, font=ctk.CTkFont(size=10, weight="bold"), fg_color="#1c1719", text_color=COLOR_ICE, corner_radius=6)
        mc3_badge.pack()

        left_col = ctk.CTkFrame(report_body, fg_color="transparent")
        left_col.grid(row=3, column=0, sticky="nsew", padx=(0, 8))

        flaws_card = ctk.CTkFrame(left_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        flaws_card.pack(fill="x", pady=(0, 14))

        fl_inner = ctk.CTkFrame(flaws_card, fg_color="transparent")
        fl_inner.pack(fill="both", expand=True, padx=18, pady=12)

        fl_head = ctk.CTkLabel(fl_inner, text="🔍  Diagnostic Analysis (What Went Wrong)", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_RUBY)
        fl_head.pack(anchor="w", pady=(0, 8))

        flaws = rep.get("what_went_wrong", [])
        if not flaws:
            flaws = ["No major delivery mistakes detected!"]

        for item in flaws[:4]:
            fl_row = ctk.CTkFrame(fl_inner, fg_color="transparent")
            fl_row.pack(fill="x", pady=3)

            is_ok = item.startswith("No major")
            icon_char = "✓" if is_ok else "!"
            icon_bg = "#172825" if is_ok else "#2b141a"
            icon_tc = COLOR_CYAN if is_ok else COLOR_RUBY

            chk = ctk.CTkLabel(fl_row, text=icon_char, font=ctk.CTkFont(size=10, weight="bold"), fg_color=icon_bg, text_color=icon_tc, width=18, height=18, corner_radius=9)
            chk.pack(side="left", padx=(0, 8), anchor="n")

            fl_txt = ctk.CTkLabel(fl_row, text=item, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_ICE, justify="left", wraplength=420, anchor="w")
            fl_txt.pack(side="left", fill="x", expand=True)

        adv_card = ctk.CTkFrame(left_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        adv_card.pack(fill="x", pady=(0, 14))

        adv_inner = ctk.CTkFrame(adv_card, fg_color="transparent")
        adv_inner.pack(fill="both", expand=True, padx=18, pady=12)

        adv_head = ctk.CTkLabel(adv_inner, text="💡  Actionable Advice for Next Take", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_CYAN)
        adv_head.pack(anchor="w", pady=(0, 8))

        improvements = rep.get("improvements", [])
        if not improvements:
            improvements = ["Keep up the steady pace and natural eye contact!"]

        for item in improvements[:4]:
            adv_row = ctk.CTkFrame(adv_inner, fg_color="transparent")
            adv_row.pack(fill="x", pady=3)

            chk2 = ctk.CTkLabel(adv_row, text="➔", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#172825", text_color=COLOR_CYAN, width=18, height=18, corner_radius=9)
            chk2.pack(side="left", padx=(0, 8), anchor="n")

            adv_txt = ctk.CTkLabel(adv_row, text=item, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_ICE, justify="left", wraplength=420, anchor="w")
            adv_txt.pack(side="left", fill="x", expand=True)

        drill_card = ctk.CTkFrame(left_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        drill_card.pack(fill="x", pady=(0, 14))

        dr_inner = ctk.CTkFrame(drill_card, fg_color="transparent")
        dr_inner.pack(fill="both", expand=True, padx=18, pady=12)

        dr_head = ctk.CTkLabel(dr_inner, text="🚀  Recommended Next Drill", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_RUBY if is_silent else COLOR_CYAN)
        dr_head.pack(anchor="w", pady=(0, 6))

        drill_text = (
            "🎙️ Mic Check & 30s Warmup: Verify microphone input in system settings, then record a rapid 30-second introduction."
            if is_silent else
            ("⚡ Impromptu Sprint: Try practicing with a randomized topic and a strict 60s timer to sharpen articulation under pressure."
             if overall_val >= 7.0 else
             "📝 Outline & Structure: Use the Gemini AI chat coach to formulate 3 key bullet points before speaking.")
        )

        dr_desc = ctk.CTkLabel(dr_inner, text=drill_text, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_ICE, justify="left", wraplength=420)
        dr_desc.pack(anchor="w")

        right_col = ctk.CTkFrame(report_body, fg_color="transparent")
        right_col.grid(row=3, column=1, sticky="nsew", padx=(8, 0))

        det_card = ctk.CTkFrame(right_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        det_card.pack(fill="x", pady=(0, 14))

        d_inner = ctk.CTkFrame(det_card, fg_color="transparent")
        d_inner.pack(fill="both", expand=True, padx=18, pady=12)

        d_head = ctk.CTkLabel(d_inner, text="🏆  Detailed Score Breakdown", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_WHITE)
        d_head.pack(anchor="w", pady=(0, 10))

        score_rows = [
            ("〰️", "Fluency", rep.get("fluency", 0.0), COLOR_TEAL, "Filler word management and flow."),
            ("📄", "Topic Relevance", rep.get("relevance", 0.0), COLOR_CYAN, "Alignment with assigned topic."),
            ("⏱️", "Speech Pace", rep.get("pace", 0.0), COLOR_ICE, f"Delivery speed ({pace_wpm} WPM)."),
            ("⏸️", "Pause Mgmt", rep.get("pauses", 0.0), COLOR_TEAL, "Hesitation and pause balance."),
            ("👁️", "Eye Contact", rep.get("eye_contact"), COLOR_CYAN, f"Camera gaze ({eye_pct_label} contact)."),
            ("👤", "Head Stability", rep.get("head_stability"), COLOR_TEAL, f"Head posture ({head_pct_label} centered)."),
        ]

        for icon, name, val, bar_color, desc in score_rows:
            score_available = val is not None
            val_f = float(val) if score_available else 0.0

            s_row = ctk.CTkFrame(d_inner, fg_color="transparent")
            s_row.pack(fill="x", pady=3)

            top_line = ctk.CTkFrame(s_row, fg_color="transparent")
            top_line.pack(fill="x")

            nl = ctk.CTkLabel(top_line, text=f"{icon}  {name}", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=TEXT_WHITE, width=120, anchor="w")
            nl.pack(side="left")

            pbar = ctk.CTkProgressBar(top_line, width=110, height=7, corner_radius=4, progress_color=bar_color, fg_color="#352b2e")
            pbar.pack(side="left", padx=8)
            pbar.set(max(0.0, min(1.0, val_f / 10.0)))

            vl = ctk.CTkLabel(top_line, text=f"{val_f:.1f}/10" if score_available else "N/A", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=TEXT_WHITE)
            vl.pack(side="right")

            dl = ctk.CTkLabel(s_row, text=desc, font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_SUBTLE, justify="left", wraplength=320, anchor="w")
            dl.pack(anchor="w", padx=(22, 0), pady=(1, 0))



    def _draw_pace_gauge(self, canvas, wpm):
        """Draw semi-circle speedometer gauge for speaking pace."""
        try:
            canvas.delete("all")
            cx, cy, r = 70, 68, 50
            x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r

            canvas.create_arc(x0, y0, x1, y1, start=180, extent=-180, style="arc", outline="#352b2e", width=7)

            prog = max(0.0, min(1.0, wpm / 200.0))
            active_color = COLOR_CYAN if (120 <= wpm <= 160) else (COLOR_ICE if wpm > 0 else "#352b2e")
            canvas.create_arc(x0, y0, x1, y1, start=180, extent=-(180 * prog), style="arc", outline=active_color, width=7)

            canvas.create_text(cx, cy - 18, text=f"{int(wpm)}", fill="#ffffff", font=(FONT_FAMILY, 18, "bold"))
            canvas.create_text(cx, cy - 2, text="words / min", fill=COLOR_ICE, font=(FONT_FAMILY, 9))
        except Exception:
            pass

    def _draw_donut(self, canvas, total_fillers):
        """Draw donut chart for filler words count."""
        try:
            canvas.delete("all")
            cx, cy, r = 32, 32, 25
            x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r

            if total_fillers == 0:
                canvas.create_arc(x0, y0, x1, y1, start=0, extent=359.9, style="arc", outline=COLOR_TEAL, width=5)
            else:
                canvas.create_arc(x0, y0, x1, y1, start=0, extent=160, style="arc", outline=COLOR_TEAL, width=5)
                canvas.create_arc(x0, y0, x1, y1, start=160, extent=100, style="arc", outline=COLOR_CYAN, width=5)
                canvas.create_arc(x0, y0, x1, y1, start=260, extent=100, style="arc", outline=COLOR_RUBY, width=5)

            canvas.create_text(cx, cy - 6, text=f"{total_fillers}", fill="#ffffff", font=(FONT_FAMILY, 13, "bold"))
            canvas.create_text(cx, cy + 7, text="total", fill=COLOR_ICE, font=(FONT_FAMILY, 8))
        except Exception:
            pass

    def _draw_time_ring_mini(self, canvas, spk_sec, target_sec):
        """Draw circular progress ring for speaking time."""
        try:
            canvas.delete("all")
            cx, cy, r = 32, 32, 25
            x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r

            canvas.create_arc(x0, y0, x1, y1, start=0, extent=359.9, style="arc", outline="#352b2e", width=5)

            prog = min(1.0, spk_sec / target_sec) if target_sec > 0 else 1.0
            canvas.create_arc(x0, y0, x1, y1, start=90, extent=-(359.9 * prog), style="arc", outline=COLOR_CYAN, width=5)

            m = spk_sec // 60
            s = spk_sec % 60
            canvas.create_text(cx, cy - 6, text=f"{m}:{s:02d}", fill="#ffffff", font=(FONT_FAMILY, 10, "bold"))
            tm = target_sec // 60
            ts = target_sec % 60
            canvas.create_text(cx, cy + 7, text=f"/ {tm}:{ts:02d}", fill=COLOR_ICE, font=(FONT_FAMILY, 8))
        except Exception:
            pass



    def _create_home_view(self):
        """Construct the dashboard-style home landing page."""
        self.home_scroll = ctk.CTkFrame(self.pages_container, fg_color=BG_DARK, corner_radius=0)
        self.home_scroll.grid_rowconfigure(0, weight=1)
        self.home_scroll.grid_columnconfigure(0, weight=1)

        self.home_container = ctk.CTkScrollableFrame(
            self.home_scroll,
            fg_color=BG_DARK,
            corner_radius=0,
            scrollbar_button_color="#38383B",
            scrollbar_button_hover_color=COLOR_CYAN,
        )
        self.home_container.grid(row=0, column=0, sticky="nsew")
        self.home_container.grid_columnconfigure(0, weight=1)

        self._render_home_content()
        return self.home_scroll

    def _render_home_content(self):
        """Render the home page contents based on whether user is logged in or guest."""
        if not hasattr(self, "home_container") or not self.home_container.winfo_exists():
            return

        for w in self.home_container.winfo_children():
            w.destroy()

        bottom_box = ctk.CTkFrame(self.home_container, fg_color="transparent")
        bottom_box.pack(side="bottom", fill="x", pady=(20, 10))

        feat_label = ctk.CTkLabel(
            bottom_box,
            text="✨  Core Capabilities",
            font=ctk.CTkFont(family=FONT_FAMILY, size=19, weight="bold"),
            text_color=TEXT_WHITE,
        )
        feat_label.pack(anchor="w", pady=(0, 14))

        feat_row = ctk.CTkFrame(bottom_box, fg_color="transparent")
        feat_row.pack(fill="x")
        for col_idx in range(3):
            feat_row.grid_columnconfigure(col_idx, weight=1, uniform="home_feat")

        features = [
            ("🤖", "Interactive AI Coach", "Chat in real-time with Gemini Flash to brainstorm compelling points, structure your speech, and refine introductions."),
            ("🎥", "Computer Vision Tracking", "Monitor gaze stability, camera alignment, eye contact percentage, and confident body posture during live recording."),
            ("📊", "Multimodal Evaluation", "Analyze words-per-minute pacing, filler word count, full speech transcription, and playable synchronized audio."),
        ]

        for idx, (f_icon, f_title, f_desc) in enumerate(features):
            fc = ctk.CTkFrame(feat_row, fg_color="#19191B", corner_radius=14, border_width=1, border_color="#303033")
            fc.grid(row=0, column=idx, padx=(0 if idx == 0 else 8, 0 if idx == 2 else 8), sticky="nsew")

            fc_inner = ctk.CTkFrame(fc, fg_color="transparent")
            fc_inner.pack(fill="both", expand=True, padx=20, pady=18)

            ic = ctk.CTkLabel(fc_inner, text=f_icon, width=42, height=42, corner_radius=10, fg_color="#29292C", text_color=COLOR_CYAN, font=ctk.CTkFont(size=23, weight="bold"))
            ic.pack(anchor="w", pady=(0, 8))

            t = ctk.CTkLabel(fc_inner, text=f_title, font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"), text_color=TEXT_WHITE)
            t.pack(anchor="w", pady=(0, 4))

            d = ctk.CTkLabel(fc_inner, text=f_desc, font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=TEXT_ICE, justify="left", wraplength=340)
            d.pack(anchor="w")

        top_box = ctk.CTkFrame(self.home_container, fg_color="transparent")
        top_box.pack(side="top", fill="x")

        hero = ctk.CTkFrame(top_box, fg_color="transparent")
        hero.pack(anchor="w", pady=(2, 4))
        ctk.CTkLabel(
            hero, text="SpeakWise", text_color=TEXT_WHITE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=76, weight="bold"),
        ).pack(side="left")
        ctk.CTkLabel(
            hero, text=" AI", text_color=COLOR_CYAN,
            font=ctk.CTkFont(family=FONT_FAMILY, size=76, weight="bold"),
        ).pack(side="left")

        sub = ctk.CTkLabel(
            top_box,
            text="Master extempore speaking with instant AI coaching, live video analysis, and deep multimodal feedback on body language, pacing, and clarity.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16),
            text_color=TEXT_MUTED,
            justify="left",
            wraplength=1050,
            anchor="w",
        )
        sub.pack(anchor="w", pady=(0, 18))

        action_card = ctk.CTkFrame(
            top_box,
            fg_color="#142321",
            corner_radius=18,
            border_width=1,
            border_color="#087D76",
        )
        action_card.pack(fill="x", pady=(0, 18))

        ac_inner = ctk.CTkFrame(action_card, fg_color="transparent")
        ac_inner.pack(fill="both", expand=True, padx=24, pady=22)

        if not self.current_user:
            g_head = ctk.CTkLabel(
                ac_inner,
                text="🚀  Get Started with Your Speaking Journey",
                font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
                text_color=TEXT_WHITE,
            )
            g_head.pack(anchor="w", pady=(0, 4))

            g_desc = ctk.CTkLabel(
                ac_inner,
                text="Sign in to your account or create a new one to save your speech recordings, track metrics over time, and unlock full reports.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=14),
                text_color=TEXT_MUTED,
            )
            g_desc.pack(anchor="w", pady=(0, 16))

            btn_row = ctk.CTkFrame(ac_inner, fg_color="transparent")
            btn_row.pack(anchor="w")

            btn_signin = ctk.CTkButton(
                btn_row,
                text="🔑  Sign In to Account",
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                fg_color=ACCENT_BLUE,
                hover_color="#008f77",
                height=52,
                corner_radius=26,
                command=lambda: self.open_auth_modal("login"),
            )
            btn_signin.pack(side="left", padx=(0, 12))

            btn_signup = ctk.CTkButton(
                btn_row,
                text="✨  Create Free Account",
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                fg_color=COLOR_CYAN,
                text_color="#191516",
                hover_color="#00d4c9",
                height=52,
                corner_radius=26,
                command=lambda: self.open_auth_modal("register"),
            )
            btn_signup.pack(side="left", padx=(0, 12))

            btn_guest = ctk.CTkButton(
                btn_row,
                text="🎙️  Practice as Guest  ➔",
                font=ctk.CTkFont(family=FONT_FAMILY, size=14),
                fg_color="#261e21",
                hover_color="#30262a",
                border_width=1,
                border_color=CARD_BORDER,
                text_color=COLOR_ICE,
                height=52,
                corner_radius=26,
                command=self.start_new_practice_session,
            )
            btn_guest.pack(side="left")

        else:
            u_name = self.current_user.get("name", "User")
            u_email = self.current_user.get("email", "")

            user_row = ctk.CTkFrame(ac_inner, fg_color="transparent")
            user_row.pack(fill="x", pady=(0, 14))

            u_head = ctk.CTkLabel(
                user_row,
                text=f"👋  Welcome back, {u_name}!",
                font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
                text_color=TEXT_WHITE,
            )
            u_head.pack(anchor="w", pady=(0, 3))

            u_sub = ctk.CTkLabel(
                user_row,
                text=f"Signed in as {u_email} • All your practice takes and speech analytics are automatically saved to your profile.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=TEXT_MUTED,
            )
            u_sub.pack(anchor="w")

            btn_row = ctk.CTkFrame(ac_inner, fg_color="transparent")
            btn_row.pack(anchor="w")

            btn_start = ctk.CTkButton(
                btn_row,
                text="🎙️  Start Speech Practice  ➔",
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                fg_color=ACCENT_BLUE,
                hover_color="#008f77",
                height=44,
                corner_radius=10,
                command=self.start_new_practice_session,
            )
            btn_start.pack(side="left", padx=(0, 12))

            btn_hist = ctk.CTkButton(
                btn_row,
                text="📜  View History",
                font=ctk.CTkFont(family=FONT_FAMILY, size=14),
                fg_color="#261e21",
                hover_color="#30262a",
                border_width=1,
                border_color=CARD_BORDER,
                text_color=COLOR_ICE,
                height=44,
                corner_radius=10,
                command=lambda: self.show_page("history"),
            )
            btn_hist.pack(side="left", padx=(0, 12))

            btn_logout = ctk.CTkButton(
                btn_row,
                text="🚪  Sign Out",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                fg_color="transparent",
                hover_color="#3a131b",
                border_width=1,
                border_color="#521724",
                text_color=COLOR_RUBY,
                height=44,
                corner_radius=10,
                command=self._handle_logout,
            )
            btn_logout.pack(side="left")

            user_sessions = []
            try:
                user_sessions = get_user_sessions(self.current_user["user_id"])
            except Exception:
                pass

            session_count = len(user_sessions)
            total_time_s = sum([s.get("speaking_time", 0) for s in user_sessions])
            total_mins = total_time_s // 60

            stats_label = ctk.CTkLabel(
                top_box,
                text="📊  Your Practice Snapshot",
                font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
                text_color=TEXT_WHITE,
            )
            stats_label.pack(anchor="w", pady=(0, 8))

            stats_row = ctk.CTkFrame(top_box, fg_color="transparent")
            stats_row.pack(fill="x", pady=(0, 4))
            for col_idx in range(3):
                stats_row.grid_columnconfigure(col_idx, weight=1, uniform="home_stats")

            u_stats = [
                ("🎙️", f"{session_count} Completed", "Total Practice Sessions", "Sessions saved in MySQL"),
                ("⏱️", f"{total_mins} Minutes", "Total Speaking Time", "Practiced in Extempore"),
                ("🎯", "Ready to Speak", "AI Coach is Standing By", "Start your next practice take"),
            ]

            for idx, (st_icon, st_val, st_title, st_sub) in enumerate(u_stats):
                sc = ctk.CTkFrame(stats_row, fg_color="#1e181a", corner_radius=12, border_width=1, border_color=CARD_BORDER)
                sc.grid(row=0, column=idx, padx=(0 if idx == 0 else 6, 0 if idx == 2 else 6), sticky="nsew")

                sc_inner = ctk.CTkFrame(sc, fg_color="transparent")
                sc_inner.pack(fill="both", expand=True, padx=14, pady=12)

                s_row = ctk.CTkFrame(sc_inner, fg_color="transparent")
                s_row.pack(anchor="w", pady=(0, 4))

                ic_lbl = ctk.CTkLabel(s_row, text=st_icon, font=ctk.CTkFont(size=18))
                ic_lbl.pack(side="left", padx=(0, 8))

                val_lbl = ctk.CTkLabel(s_row, text=st_val, font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=TEXT_WHITE)
                val_lbl.pack(side="left")

                t_lbl = ctk.CTkLabel(sc_inner, text=st_title, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_CYAN)
                t_lbl.pack(anchor="w")

                sub_lbl = ctk.CTkLabel(sc_inner, text=st_sub, font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_MUTED)
                sub_lbl.pack(anchor="w")


    def _create_history_view(self):
        """Construct History page with dynamic MySQL sessions and empty state."""
        frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.history_main_scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.history_main_scroll.grid(row=0, column=0, sticky="nsew")
        self.history_main_scroll.grid_columnconfigure(0, weight=1)

        self._render_history_page()
        return frame

    def _load_user_history_from_db(self):
        """Fetch all sessions and parsed take reports from MySQL for active user."""
        sessions = []
        if not self.current_user:
            return sessions

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
                (self.current_user["user_id"],),
            )
            rows = cursor.fetchall()
            cursor.close()
            db.close()

            cat_icons = {
                "technology": "🪐",
                "science": "🧠",
                "history": "🏛️",
                "business": "📈",
                "society": "👥",
                "environment": "🌿",
                "entertainment": "🎮",
                "mystery": "⛵",
            }
            cat_bgs = {
                "technology": "#172825",
                "science": "#221c1e",
                "history": "#2b141a",
                "business": "#172825",
                "society": "#221c1e",
                "environment": "#172825",
                "entertainment": "#2b141a",
                "mystery": "#1c1719",
            }

            for r in rows:
                rep_raw = r.get("report") or ""
                rep_dict = {}
                if isinstance(rep_raw, dict):
                    rep_dict = rep_raw
                elif isinstance(rep_raw, str) and rep_raw.strip().startswith("{"):
                    try:
                        rep_dict = json.loads(rep_raw)
                    except Exception:
                        rep_dict = {}

                cat = r.get("category") or rep_dict.get("category") or "General"
                cat_lower = cat.lower().strip()
                icon = cat_icons.get(cat_lower, "🎙️")
                icon_bg = cat_bgs.get(cat_lower, "#172825")

                score = float(rep_dict.get("overall", 7.5)) if rep_dict.get("overall") is not None else 7.5
                fluency = float(rep_dict.get("fluency", score)) if rep_dict.get("fluency") is not None else score

                if score >= 8.0:
                    score_label = "Great job!"
                    score_color = COLOR_CYAN
                elif score >= 7.0:
                    score_label = "Good job!"
                    score_color = COLOR_TEAL
                elif score >= 6.0:
                    score_label = "Keep going!"
                    score_color = COLOR_ICE
                else:
                    score_label = "Needs work"
                    score_color = COLOR_RUBY

                spk_sec = r.get("speaking_time") or 60
                mins = spk_sec // 60
                secs = spk_sec % 60
                dur_str = f"{mins}:{secs:02d}"

                dt = r.get("created_at")
                if dt:
                    try:
                        date_str = dt.strftime("%d %b %Y, %I:%M %p")
                    except Exception:
                        date_str = str(dt)
                else:
                    date_str = time.strftime("%d %b %Y, %I:%M %p")

                fillers_count = rep_dict.get("total_fillers", 0)
                fillers_str = f"{fillers_count}" if fillers_count else "0"

                sessions.append({
                    "session_id": r.get("session_id"),
                    "topic": r.get("topic_name") or "Speech Practice",
                    "category": cat,
                    "icon": icon,
                    "icon_bg": icon_bg,
                    "date": date_str,
                    "duration": dur_str,
                    "target": dur_str,
                    "score": score,
                    "fluency": fluency,
                    "score_label": score_label,
                    "score_color": score_color,
                    "fillers": fillers_str,
                    "speaking_time": spk_sec,
                    "transcription": r.get("transcription", "") or "",
                    "report_data": rep_dict,
                    "audio_path": r.get("audio_path", ""),
                    "video_path": r.get("video_path", ""),
                })

        except Exception:
            pass

        return sessions

    def _render_history_empty_state(self):
        """Show a calm, centered prompt when no saved sessions are available."""
        header = ctk.CTkFrame(self.history_main_scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0, 18))

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(anchor="w")

        icon = ctk.CTkLabel(
            title_row,
            text="◷",
            width=46,
            height=46,
            corner_radius=23,
            fg_color="#142321",
            text_color=COLOR_CYAN,
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        icon.pack(side="left", padx=(0, 12))

        title = ctk.CTkLabel(
            title_row,
            text="History",
            font=ctk.CTkFont(family=FONT_FAMILY, size=30, weight="bold"),
            text_color=TEXT_WHITE,
        )
        title.pack(side="left")

        subtitle = ctk.CTkLabel(
            header,
            text="Your past practice sessions, performance and progress — all in one place.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
        )
        subtitle.pack(anchor="w", pady=(6, 0))

        empty_card = ctk.CTkFrame(
            self.history_main_scroll,
            fg_color="#1D191B",
            corner_radius=16,
            border_width=1,
            border_color="#352B2E",
            height=286,
        )
        empty_card.pack(fill="x", pady=(0, 16))
        empty_card.pack_propagate(False)

        content = ctk.CTkFrame(empty_card, fg_color="transparent")
        content.pack(expand=True)

        clock = ctk.CTkLabel(
            content,
            text="◷",
            font=ctk.CTkFont(size=42, weight="bold"),
            text_color=TEXT_ICE,
        )
        clock.pack(pady=(0, 10))

        heading = ctk.CTkLabel(
            content,
            text="No Practice Sessions Yet",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_WHITE,
        )
        heading.pack(pady=(0, 6))

        description = ctk.CTkLabel(
            content,
            text="You haven't completed any speech practice sessions yet.\nStart your first session in Practice mode to track your speaking progress, fluency, and analytics here!",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_ICE,
            justify="center",
        )
        description.pack(pady=(0, 18))

        start_button = ctk.CTkButton(
            content,
            text="Start Practice Now  →",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#008F77",
            text_color=TEXT_WHITE,
            corner_radius=10,
            height=44,
            width=200,
            command=self.start_new_practice_session,
        )
        start_button.pack()

    def _render_history_page(self):
        """Render saved practice sessions in a simple, single-column history view."""
        for widget in self.history_main_scroll.winfo_children():
            widget.destroy()

        self.cached_history_sessions = self._load_user_history_from_db()
        if not self.cached_history_sessions:
            self._render_history_empty_state()
            return

        header = ctk.CTkFrame(self.history_main_scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0, 18))

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(
            title_row,
            text="History",
            font=ctk.CTkFont(family=FONT_FAMILY, size=30, weight="bold"),
            text_color=TEXT_WHITE,
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text="Your past practice sessions.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=(4, 0))

        self.history_items_container = ctk.CTkFrame(self.history_main_scroll, fg_color="transparent")
        self.history_items_container.pack(fill="both", expand=True)
        self._render_session_cards()

    def _render_session_cards(self):
        """Populate the sessions list from dynamic MySQL records with empty state handling."""
        for w in self.history_items_container.winfo_children():
            w.destroy()

        sessions = getattr(self, "cached_history_sessions", None)
        if sessions is None:
            sessions = self._load_user_history_from_db()
            self.cached_history_sessions = sessions

        if not sessions:
            empty_card = ctk.CTkFrame(
                self.history_items_container,
                fg_color=CARD_BG,
                corner_radius=16,
                border_width=1,
                border_color=CARD_BORDER,
            )
            empty_card.pack(fill="x", pady=20)

            e_inner = ctk.CTkFrame(empty_card, fg_color="transparent")
            e_inner.pack(fill="both", expand=True, padx=24, pady=40)

            e_icon = ctk.CTkLabel(e_inner, text="🕒", font=ctk.CTkFont(size=44))
            e_icon.pack(pady=(0, 12))

            e_title = ctk.CTkLabel(
                e_inner,
                text="No Practice Sessions Yet",
                font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
                text_color=TEXT_WHITE,
            )
            e_title.pack(pady=(0, 6))

            e_desc = ctk.CTkLabel(
                e_inner,
                text="You haven't completed any speech practice sessions yet.\nStart your first session in Practice mode to track your speaking progress, fluency, and analytics here!",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=TEXT_MUTED,
                justify="center",
            )
            e_desc.pack(pady=(0, 20))

            if not has_any:
                btn_start_now = ctk.CTkButton(
                    e_inner,
                    text="Start Practice Now  ➔",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                    fg_color=ACCENT_BLUE,
                    hover_color="#008f77",
                    corner_radius=10,
                    height=44,
                    width=200,
                    command=self.start_new_practice_session,
                )
                btn_start_now.pack()

            return

        for sess in sessions:
            self._build_history_card(self.history_items_container, sess)

    def _build_history_card(self, parent, sess):
        """Construct a single session card matching the mockup with full card clickability."""
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_BG,
            corner_radius=14,
            border_width=1,
            border_color=CARD_BORDER,
            height=90,
            cursor="hand2",
        )
        card.pack(fill="x", pady=6)

        inner = ctk.CTkFrame(card, fg_color="transparent", cursor="hand2")
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        thumb_box = ctk.CTkFrame(inner, width=48, height=48, corner_radius=10, fg_color=sess.get("icon_bg", "#172825"), cursor="hand2")
        thumb_box.pack(side="left", padx=(0, 14))
        thumb_box.pack_propagate(False)

        icon_lbl = ctk.CTkLabel(thumb_box, text=sess.get("icon", "🎙️"), font=ctk.CTkFont(size=20), cursor="hand2")
        icon_lbl.pack(expand=True)

        chk_badge = ctk.CTkLabel(
            thumb_box,
            text="✓",
            font=ctk.CTkFont(size=8, weight="bold"),
            fg_color=COLOR_TEAL,
            text_color=TEXT_WHITE,
            width=14,
            height=14,
            corner_radius=7,
            cursor="hand2",
        )
        chk_badge.place(relx=1.0, rely=0.0, x=-2, y=2, anchor="ne")

        info_col = ctk.CTkFrame(inner, fg_color="transparent", width=240, cursor="hand2")
        info_col.pack(side="left", fill="y", padx=(0, 10))

        t_lbl = ctk.CTkLabel(
            info_col,
            text=sess.get("topic", "Speech Practice"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_WHITE,
            anchor="w",
            wraplength=220,
            justify="left",
            cursor="hand2",
        )
        t_lbl.pack(anchor="w")

        sub_row = ctk.CTkFrame(info_col, fg_color="transparent", cursor="hand2")
        sub_row.pack(anchor="w", pady=(2, 0))

        cat_lbl = ctk.CTkLabel(
            sub_row,
            text=f" {sess.get('category', 'General')} ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#172825",
            text_color=COLOR_CYAN,
            corner_radius=4,
            cursor="hand2",
        )
        cat_lbl.pack(side="left", padx=(0, 8))

        date_lbl = ctk.CTkLabel(
            sub_row,
            text=f"📅 {sess.get('date', '')}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SUBTLE,
            cursor="hand2",
        )
        date_lbl.pack(side="left")

        time_col = ctk.CTkFrame(inner, fg_color="transparent", width=110, cursor="hand2")
        time_col.pack(side="left", fill="y", padx=(0, 10))

        time_cap = ctk.CTkLabel(time_col, text="⏱️  Speaking Time", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_SUBTLE, anchor="w", cursor="hand2")
        time_cap.pack(anchor="w")

        time_val = ctk.CTkLabel(time_col, text=sess.get("duration", "1:00"), font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_WHITE, anchor="w", cursor="hand2")
        time_val.pack(anchor="w")

        time_tgt = ctk.CTkLabel(time_col, text=f"Target: {sess.get('target', '1:00')}", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_SUBTLE, anchor="w", cursor="hand2")
        time_tgt.pack(anchor="w")

        score_col = ctk.CTkFrame(inner, fg_color="transparent", width=100, cursor="hand2")
        score_col.pack(side="left", fill="y", padx=(0, 10))

        s_cap = ctk.CTkLabel(score_col, text="Score", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_SUBTLE, anchor="w", cursor="hand2")
        s_cap.pack(anchor="w")

        s_val = ctk.CTkLabel(score_col, text=f"🏆 {sess.get('score', 7.5):.1f}/10", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_WHITE, anchor="w", cursor="hand2")
        s_val.pack(anchor="w")

        s_note = ctk.CTkLabel(score_col, text=sess.get("score_label", "Good job!"), font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=sess.get("score_color", COLOR_CYAN), anchor="w", cursor="hand2")
        s_note.pack(anchor="w")

        fill_col = ctk.CTkFrame(inner, fg_color="transparent", width=100, cursor="hand2")
        fill_col.pack(side="left", fill="y", padx=(0, 14))

        f_cap = ctk.CTkLabel(fill_col, text="💬  Filler Words", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_SUBTLE, anchor="w", cursor="hand2")
        f_cap.pack(anchor="w")

        f_val = ctk.CTkLabel(fill_col, text=f"💬 {sess.get('fillers', '0')}", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=TEXT_WHITE, anchor="w", cursor="hand2")
        f_val.pack(anchor="w")

        btn_details = ctk.CTkButton(
            inner,
            text="View Details  ➔",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="transparent",
            hover_color=CARD_HOVER,
            border_width=1,
            border_color=CARD_BORDER,
            text_color=COLOR_ICE,
            corner_radius=8,
            height=32,
            width=100,
            command=lambda s=sess: self._open_session_report_from_history(s),
        )
        btn_details.pack(side="right", padx=(6, 0))

        btn_more = ctk.CTkLabel(inner, text=" ⋮ ", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_MUTED, cursor="hand2")
        btn_more.pack(side="right")

        def _on_card_click(event=None):
            self._open_session_report_from_history(sess)

        clickable_items = [
            card, inner, thumb_box, icon_lbl, chk_badge,
            info_col, t_lbl, sub_row, cat_lbl, date_lbl,
            time_col, time_cap, time_val, time_tgt,
            score_col, s_cap, s_val, s_note,
            fill_col, f_cap, f_val, btn_more
        ]
        for w in clickable_items:
            w.bind("<Button-1>", _on_card_click)

        def _on_hover_enter(event=None):
            card.configure(fg_color=CARD_HOVER, border_color=COLOR_CYAN)
        def _on_hover_leave(event=None):
            card.configure(fg_color=CARD_BG, border_color=CARD_BORDER)

        card.bind("<Enter>", _on_hover_enter)
        card.bind("<Leave>", _on_hover_leave)
        for w in clickable_items:
            if w != card:
                w.bind("<Enter>", _on_hover_enter)
                w.bind("<Leave>", _on_hover_leave)

    def _open_session_report_from_history(self, sess):
        """Open the full Speech Report page for a history item using its actual saved take report, audio, and video."""
        rep_dict = sess.get("report_data") or {}
        transcription_text = sess.get("transcription") or rep_dict.get("transcription", "")
        word_count = rep_dict.get("total_words", len(transcription_text.split()))

        rep_data = {
            **rep_dict,
            "topic": sess.get("topic") or rep_dict.get("topic", "Speech Practice"),
            "category": sess.get("category") or rep_dict.get("category", "General"),
            "duration": sess.get("speaking_time") or rep_dict.get("duration", 60),
            "speaking_time": sess.get("speaking_time") or rep_dict.get("speaking_time", 60),
            "overall": float(sess.get("score") if sess.get("score") is not None else rep_dict.get("overall", 0.0)),
            "fluency": float(sess.get("fluency") if sess.get("fluency") is not None else rep_dict.get("fluency", 0.0)),
            "total_words": word_count,
            "is_silent": rep_dict.get("is_silent", word_count == 0),
            "transcription": transcription_text,
        }
        self._render_speech_report(
            self.reports_container,
            rep=rep_data,
            transcription=transcription_text,
            session_date=sess.get("date"),
            back_callback=lambda: self.show_page("history"),
            video_path=sess.get("video_path"),
            audio_path=sess.get("audio_path"),
        )
        self.show_page("reports")


    def _render_history_items(self):
        """Callback from sidebar history button."""
        if hasattr(self, "history_main_scroll"):
            self._render_history_page()

    def _create_profile_view(self):
        frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)

        self.profile_content = ctk.CTkFrame(frame, fg_color="transparent")
        self.profile_content.pack(fill="both", expand=True)

        self._refresh_profile_content()
        return frame

    def _refresh_profile_content(self):
        if not hasattr(self, "profile_content") or not self.profile_content.winfo_exists():
            return
        for w in self.profile_content.winfo_children():
            w.destroy()

        title = ctk.CTkLabel(
            self.profile_content,
            text="User Profile & Account",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_WHITE,
        )
        title.pack(anchor="w", pady=(0, 20))

        if not self.current_user:
            card = ctk.CTkFrame(self.profile_content, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
            card.pack(fill="x", pady=(0, 20))

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=24, pady=24)

            p_row = ctk.CTkFrame(inner, fg_color="transparent")
            p_row.pack(fill="x", pady=(0, 16))

            av = ctk.CTkLabel(
                p_row,
                text="👤",
                width=56,
                height=56,
                corner_radius=28,
                fg_color="#2b2326",
                text_color=COLOR_ICE,
                font=ctk.CTkFont(size=24),
            )
            av.pack(side="left", padx=(0, 16))

            info = ctk.CTkFrame(p_row, fg_color="transparent")
            info.pack(side="left")

            n_lbl = ctk.CTkLabel(info, text="Guest Account", font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"), text_color=TEXT_WHITE)
            n_lbl.pack(anchor="w")

            e_lbl = ctk.CTkLabel(info, text="Not signed in • Browse & guest practice mode", font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=TEXT_MUTED)
            e_lbl.pack(anchor="w", pady=(2, 0))

            g_desc = ctk.CTkLabel(
                inner,
                text="You are currently practicing as a Guest. Sign in or register for free to save speech recordings, monitor progress, and access detailed analytics.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=TEXT_MUTED,
                justify="left",
            )
            g_desc.pack(anchor="w", pady=(0, 20))

            btn_bar = ctk.CTkFrame(inner, fg_color="transparent")
            btn_bar.pack(anchor="w")

            btn_login = ctk.CTkButton(
                btn_bar,
                text="🔑 Sign In",
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                fg_color=ACCENT_BLUE,
                hover_color="#008f77",
                corner_radius=10,
                height=44,
                command=lambda: self.open_auth_modal("login"),
            )
            btn_login.pack(side="left", padx=(0, 12))

            btn_register = ctk.CTkButton(
                btn_bar,
                text="✨ Create New Account",
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                fg_color=COLOR_CYAN,
                text_color="#191516",
                hover_color="#00d4c9",
                corner_radius=10,
                height=44,
                command=lambda: self.open_auth_modal("register"),
            )
            btn_register.pack(side="left")

        else:
            card = ctk.CTkFrame(self.profile_content, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
            card.pack(fill="x", pady=(0, 20))

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=24, pady=24)

            name = self.current_user.get("name", "User")
            email = self.current_user.get("email", "")
            user_id = self.current_user.get("user_id", 1)
            initials = "".join([part[0].upper() for part in name.split()[:2]]) or "U"

            p_row = ctk.CTkFrame(inner, fg_color="transparent")
            p_row.pack(fill="x")

            av = ctk.CTkLabel(
                p_row,
                text=initials,
                width=56,
                height=56,
                corner_radius=28,
                fg_color=COLOR_TEAL,
                text_color="#191516",
                font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            )
            av.pack(side="left", padx=(0, 16))

            info = ctk.CTkFrame(p_row, fg_color="transparent")
            info.pack(side="left")

            n_lbl = ctk.CTkLabel(info, text=name, font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"), text_color=TEXT_WHITE)
            n_lbl.pack(anchor="w")

            e_lbl = ctk.CTkLabel(info, text=f"{email}   •   User ID: #{user_id}", font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=TEXT_MUTED)
            e_lbl.pack(anchor="w", pady=(2, 0))

            btn_bar = ctk.CTkFrame(self.profile_content, fg_color="transparent")
            btn_bar.pack(fill="x", pady=(0, 0))

            btn_login = ctk.CTkButton(
                btn_bar,
                text="🔑 Switch User / Log In",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                fg_color="#1c1719",
                hover_color=CARD_HOVER,
                border_width=1,
                border_color=CARD_BORDER,
                text_color=COLOR_ICE,
                corner_radius=10,
                height=44,
                command=lambda: self.open_auth_modal("login"),
            )
            btn_login.pack(side="left", padx=(0, 10))

            btn_register = ctk.CTkButton(
                btn_bar,
                text="➕ Register New User",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                fg_color=ACCENT_BLUE,
                hover_color="#008f77",
                corner_radius=10,
                height=44,
                command=lambda: self.open_auth_modal("register"),
            )
            btn_register.pack(side="left", padx=(0, 10))

            btn_logout = ctk.CTkButton(
                btn_bar,
                text="🚪 Sign Out",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                fg_color="#1c1719",
                hover_color=CARD_HOVER,
                border_width=1,
                border_color=CARD_BORDER,
                text_color=COLOR_ICE,
                corner_radius=10,
                height=44,
                command=self._handle_logout,
            )
            btn_logout.pack(side="left", padx=(0, 10))

            btn_delete = ctk.CTkButton(
                btn_bar,
                text="🗑️ Delete Account",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                fg_color="#2b141a",
                hover_color="#3d1b24",
                border_width=1,
                border_color=COLOR_RUBY,
                text_color=COLOR_RUBY,
                corner_radius=10,
                height=44,
                command=self._handle_delete_user_account,
            )
            btn_delete.pack(side="left")

    def _handle_logout(self):
        """Log out current user and return to guest state."""
        clear_remembered_user()
        self.current_user = None
        self._update_current_user_ui()
        self._refresh_profile_content()
        self.show_page("home")

    def _handle_delete_user_account(self, confirmed=False):
        if not self.current_user:
            return

        if not confirmed:
            for child in self.profile_content.winfo_children():
                if getattr(child, "_delete_confirmation_panel", False):
                    child.destroy()

            confirm_panel = ctk.CTkFrame(
                self.profile_content,
                fg_color="#2b141a",
                corner_radius=10,
                border_width=1,
                border_color=COLOR_RUBY,
            )
            confirm_panel._delete_confirmation_panel = True
            confirm_panel.pack(fill="x", pady=(14, 0))
            ctk.CTkLabel(
                confirm_panel,
                text=f"Permanently delete account '{self.current_user['name']}' and all saved speech takes?",
                font=ctk.CTkFont(size=13),
                text_color=COLOR_ICE,
                wraplength=620,
                justify="left",
            ).pack(anchor="w", padx=16, pady=(14, 10))

            actions = ctk.CTkFrame(confirm_panel, fg_color="transparent")
            actions.pack(anchor="w", padx=12, pady=(0, 12))
            ctk.CTkButton(
                actions,
                text="Delete Account",
                fg_color=COLOR_RUBY,
                hover_color="#a83248",
                text_color=COLOR_ICE,
                command=lambda: self._handle_delete_user_account(confirmed=True),
            ).pack(side="left", padx=4)
            ctk.CTkButton(
                actions,
                text="Cancel",
                fg_color="#1c1719",
                hover_color=CARD_HOVER,
                text_color=COLOR_ICE,
                command=confirm_panel.destroy,
            ).pack(side="left", padx=4)
            return

        success, msg = delete_user(self.current_user["user_id"])
        if success:
            clear_remembered_user()
            self.current_user = None
            self._update_current_user_ui()
            self._refresh_profile_content()
            self.show_page("home")
        else:
            error_label = ctk.CTkLabel(
                self.profile_content,
                text=f"Could not delete account: {msg}",
                font=ctk.CTkFont(size=12),
                text_color=COLOR_RUBY,
                wraplength=620,
                justify="left",
            )
            error_label.pack(anchor="w", pady=(12, 0))


    def open_auth_modal(self, initial_tab="login"):
        """Open modern modal dialog supporting both Login and New User Registration with real-time MySQL persistence."""
        modal = ctk.CTkToplevel(self)
        modal.title("Account Authentication — SpeakWise AI")
        modal.geometry("520x640")
        modal.resizable(False, False)
        modal.configure(fg_color=BG_DARK)
        modal.grab_set()

        modal.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 260
        y = self.winfo_y() + (self.winfo_height() // 2) - 320
        modal.geometry(f"+{x}+{y}")
        modal.lift()
        modal.focus_force()

        container = ctk.CTkFrame(modal, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        tabview = ctk.CTkTabview(
            container,
            fg_color="transparent",
            segmented_button_fg_color="#1c1719",
            segmented_button_selected_color=ACCENT_BLUE,
            segmented_button_selected_hover_color="#008f77",
            segmented_button_unselected_color="#1c1719",
            segmented_button_unselected_hover_color=CARD_HOVER,
        )
        tabview.pack(fill="both", expand=True, padx=16, pady=12)

        tab_login = tabview.add("Log In")
        tab_register = tabview.add("Create Account")

        if initial_tab == "register":
            tabview.set("Create Account")
        else:
            tabview.set("Log In")

        l_head = ctk.CTkLabel(
            tab_login,
            text="Welcome Back!",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_WHITE,
        )
        l_head.pack(pady=(16, 4))

        l_sub = ctk.CTkLabel(
            tab_login,
            text="Sign in to track your speech sessions and progress.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        )
        l_sub.pack(pady=(0, 16))

        l_email = ctk.CTkEntry(tab_login, placeholder_text="Email Address or Name", fg_color="#1c1719", border_color=CARD_BORDER, text_color=COLOR_ICE, height=44, corner_radius=8, font=ctk.CTkFont(size=13))
        l_email.pack(fill="x", padx=16, pady=8)

        l_pw = ctk.CTkEntry(tab_login, placeholder_text="Password", show="•", fg_color="#1c1719", border_color=CARD_BORDER, text_color=COLOR_ICE, height=44, corner_radius=8, font=ctk.CTkFont(size=13))
        l_pw.pack(fill="x", padx=16, pady=8)

        l_status = ctk.CTkLabel(tab_login, text="", font=ctk.CTkFont(size=12), text_color=COLOR_RUBY)
        l_status.pack(pady=4)

        def do_login():
            ident = l_email.get().strip()
            pw = l_pw.get().strip()
            if not ident or not pw:
                if l_status.winfo_exists():
                    l_status.configure(text="Please enter both email/name and password.", text_color=COLOR_RUBY)
                return

            success, result = authenticate_user(ident, pw)
            if success:
                self.current_user = result
                remember_user(result)
                self._update_current_user_ui()
                self._refresh_profile_content()
                try:
                    modal.grab_release()
                    modal.destroy()
                except Exception:
                    pass
            else:
                if l_status.winfo_exists():
                    l_status.configure(text=str(result), text_color=COLOR_RUBY)

        l_email.bind("<Return>", lambda e: do_login())
        l_pw.bind("<Return>", lambda e: do_login())

        btn_l_submit = ctk.CTkButton(
            tab_login,
            text="Sign In",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#008f77",
            height=44,
            corner_radius=8,
            command=do_login,
        )
        btn_l_submit.pack(fill="x", padx=16, pady=(12, 10))

        btn_switch_reg = ctk.CTkButton(
            tab_login,
            text="Don't have an account? Register here",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color=COLOR_CYAN,
            hover=False,
            command=lambda: tabview.set("Create Account"),
        )
        btn_switch_reg.pack()

        r_head = ctk.CTkLabel(
            tab_register,
            text="Create New Account",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_WHITE,
        )
        r_head.pack(pady=(12, 4))

        r_sub = ctk.CTkLabel(
            tab_register,
            text="Join SpeakWise AI to practice and improve your speaking.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        )
        r_sub.pack(pady=(0, 14))

        r_name = ctk.CTkEntry(tab_register, placeholder_text="Full Name (e.g. Rahul Kulkarni)", fg_color="#1c1719", border_color=CARD_BORDER, text_color=COLOR_ICE, height=40, corner_radius=8, font=ctk.CTkFont(size=13))
        r_name.pack(fill="x", padx=16, pady=6)

        r_email = ctk.CTkEntry(tab_register, placeholder_text="Email Address (e.g. rahul@example.com)", fg_color="#1c1719", border_color=CARD_BORDER, text_color=COLOR_ICE, height=40, corner_radius=8, font=ctk.CTkFont(size=13))
        r_email.pack(fill="x", padx=16, pady=6)

        r_pw = ctk.CTkEntry(tab_register, placeholder_text="Password (min 6 characters)", show="•", fg_color="#1c1719", border_color=CARD_BORDER, text_color=COLOR_ICE, height=40, corner_radius=8, font=ctk.CTkFont(size=13))
        r_pw.pack(fill="x", padx=16, pady=6)

        r_confirm = ctk.CTkEntry(tab_register, placeholder_text="Confirm Password", show="•", fg_color="#1c1719", border_color=CARD_BORDER, text_color=COLOR_ICE, height=40, corner_radius=8, font=ctk.CTkFont(size=13))
        r_confirm.pack(fill="x", padx=16, pady=6)

        r_status = ctk.CTkLabel(tab_register, text="", font=ctk.CTkFont(size=12), text_color=COLOR_RUBY)
        r_status.pack(pady=2)

        def do_register():
            name_val = r_name.get().strip()
            email_val = r_email.get().strip().lower()
            pw_val = r_pw.get().strip()
            confirm_val = r_confirm.get().strip()

            if not name_val or not email_val or not pw_val or not confirm_val:
                if r_status.winfo_exists():
                    r_status.configure(text="Please fill out all registration fields.", text_color=COLOR_RUBY)
                return

            if pw_val != confirm_val:
                if r_status.winfo_exists():
                    r_status.configure(text="Passwords do not match.", text_color=COLOR_RUBY)
                return

            success, result = register_user(name_val, email_val, pw_val)
            if success:
                self.current_user = result
                remember_user(result)
                self._update_current_user_ui()
                self._refresh_profile_content()
                try:
                    modal.grab_release()
                    modal.destroy()
                except Exception:
                    pass
            else:
                if r_status.winfo_exists():
                    r_status.configure(text=str(result), text_color=COLOR_RUBY)

        r_name.bind("<Return>", lambda e: do_register())
        r_email.bind("<Return>", lambda e: do_register())
        r_pw.bind("<Return>", lambda e: do_register())
        r_confirm.bind("<Return>", lambda e: do_register())

        btn_r_submit = ctk.CTkButton(
            tab_register,
            text="Register & Sign In",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLOR_CYAN,
            text_color="#191516",
            hover_color="#00d4c9",
            height=44,
            corner_radius=8,
            command=do_register,
        )
        btn_r_submit.pack(fill="x", padx=16, pady=(10, 8))

        btn_switch_login = ctk.CTkButton(
            tab_register,
            text="Already have an account? Log in",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color=COLOR_CYAN,
            hover=False,
            command=lambda: tabview.set("Log In"),
        )
        btn_switch_login.pack()

        if initial_tab == "register":
            self.safe_after(50, lambda: r_name.focus_set() if r_name.winfo_exists() else None)
        else:
            self.safe_after(50, lambda: l_email.focus_set() if l_email.winfo_exists() else None)

    def _update_current_user_ui(self):
        """Update top bar user badge and initials upon login/register/logout and flush pending takes."""
        if self.current_user:
            u_name = self.current_user.get("name", "User")
            initials = "".join([part[0].upper() for part in u_name.split()[:2]]) or "U"
            role_text = "Student"
            circle_bg = COLOR_TEAL

            if getattr(self, "last_unsaved_session", None):
                try:
                    save_speech_session(
                        user_id=self.current_user["user_id"],
                        **self.last_unsaved_session,
                    )
                    self.last_unsaved_session = None
                except Exception:
                    pass
        else:
            u_name = "Sign In / Register"
            initials = "👤"
            role_text = "Guest Mode"
            circle_bg = "#221c1e"

        if hasattr(self, "top_u_circle"):
            self.top_u_circle.configure(text=initials, fg_color=circle_bg)
        if hasattr(self, "top_u_name_lbl"):
            self.top_u_name_lbl.configure(text=u_name)
        if hasattr(self, "top_u_role_lbl"):
            self.top_u_role_lbl.configure(text=role_text)

        if hasattr(self, "home_container"):
            self._render_home_content()

    def _create_admin_view(self):
        frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        self.admin_container = frame
        self._render_admin_page()
        return frame

    def _render_admin_page(self):
        """Show the admin sign-in form or the protected database browser."""
        if not hasattr(self, "admin_container") or not self.admin_container.winfo_exists():
            return
        for child in self.admin_container.winfo_children():
            child.destroy()

        if self.admin_authenticated:
            self._render_admin_database()
            return

        card = ctk.CTkFrame(
            self.admin_container,
            fg_color=CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=CARD_BORDER,
        )
        card.place(relx=0.5, rely=0.42, anchor="center", relwidth=0.62)

        ctk.CTkLabel(
            card,
            text="Administrator Sign In",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_WHITE,
        ).pack(anchor="w", padx=28, pady=(26, 4))
        ctk.CTkLabel(
            card,
            text="Sign in to inspect users, practice sessions, takes, and the SpeakWise database tables.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_MUTED,
            wraplength=620,
            justify="left",
        ).pack(anchor="w", padx=28, pady=(0, 18))

        username_entry = ctk.CTkEntry(
            card,
            placeholder_text="Admin username",
            fg_color="#1c1719",
            border_color=CARD_BORDER,
            text_color=COLOR_ICE,
            height=44,
        )
        username_entry.pack(fill="x", padx=28, pady=7)
        password_entry = ctk.CTkEntry(
            card,
            placeholder_text="Admin password",
            show="•",
            fg_color="#1c1719",
            border_color=CARD_BORDER,
            text_color=COLOR_ICE,
            height=44,
        )
        password_entry.pack(fill="x", padx=28, pady=7)
        status_label = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=12), text_color=COLOR_RUBY)
        status_label.pack(anchor="w", padx=28, pady=(2, 0))

        def sign_in(event=None):
            expected_user = os.getenv("ADMIN_USERNAME", "")
            expected_password = os.getenv("ADMIN_PASSWORD", "")
            if not expected_user or not expected_password:
                status_label.configure(
                    text="Admin credentials are missing. Set ADMIN_USERNAME and ADMIN_PASSWORD in .env."
                )
                return

            valid_user = hmac.compare_digest(username_entry.get().strip(), expected_user)
            valid_password = hmac.compare_digest(password_entry.get(), expected_password)
            if valid_user and valid_password:
                self.admin_authenticated = True
                self._render_admin_page()
            else:
                status_label.configure(text="Admin username or password is incorrect.")
                password_entry.delete(0, "end")
                password_entry.focus_set()

        password_entry.bind("<Return>", sign_in)
        username_entry.bind("<Return>", lambda _event: password_entry.focus_set())
        ctk.CTkButton(
            card,
            text="Sign In to Admin",
            fg_color=ACCENT_BLUE,
            hover_color="#008f77",
            height=44,
            command=sign_in,
        ).pack(fill="x", padx=28, pady=(14, 26))
        username_entry.focus_set()

    def _render_admin_database(self):
        db_name = os.getenv("DB_NAME", "speakwise")
        self.admin_table = getattr(self, "admin_table", "users")
        self.admin_page_number = getattr(self, "admin_page_number", 1)
        self.admin_search = getattr(self, "admin_search", "")

        page = ctk.CTkFrame(self.admin_container, fg_color="transparent")
        page.pack(fill="both", expand=True)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            title_box,
            text="Database Administration",
            font=ctk.CTkFont(family=FONT_FAMILY, size=27, weight="bold"),
            text_color=TEXT_WHITE,
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_box,
            text=f"Database: {db_name}  ?  User passwords are hidden",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=(3, 0))

        def admin_logout():
            self.admin_authenticated = False
            self._render_admin_page()

        ctk.CTkButton(
            header,
            text="Refresh",
            width=100,
            fg_color="#2b2326",
            hover_color=CARD_HOVER,
            command=self._render_admin_page,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            header,
            text="Sign Out",
            width=100,
            fg_color="#2b141a",
            hover_color="#3d1b24",
            command=admin_logout,
        ).pack(side="right")

        stats = get_db_stats() or {"users": 0, "sessions": 0, "takes": 0}
        metrics = ctk.CTkFrame(page, fg_color="transparent")
        metrics.pack(fill="x", pady=(0, 14))
        for icon, label, value in (
            ("?", "Registered users", stats.get("users", 0)),
            ("?", "Practice sessions", stats.get("sessions", 0)),
            ("?", "Recorded takes", stats.get("takes", 0)),
        ):
            metric = ctk.CTkFrame(
                metrics,
                fg_color=CARD_BG,
                corner_radius=12,
                border_width=1,
                border_color=CARD_BORDER,
            )
            metric.pack(side="left", fill="x", expand=True, padx=(0, 10))
            metric.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                metric,
                text=icon,
                width=56,
                height=50,
                corner_radius=10,
                fg_color="#172825",
                text_color=COLOR_CYAN,
                font=ctk.CTkFont(size=23, weight="bold"),
            ).grid(row=0, column=0, rowspan=2, padx=(14, 16), pady=12)
            ctk.CTkLabel(
                metric,
                text=str(value),
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color=COLOR_CYAN,
            ).grid(row=0, column=1, sticky="sw", pady=(11, 0))
            ctk.CTkLabel(
                metric,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=TEXT_MUTED,
            ).grid(row=1, column=1, sticky="nw", pady=(0, 11))

        table_names = get_database_tables(db_name)
        preferred = [name for name in ("users", "sessions", "takes") if name in table_names]
        if not preferred:
            preferred = table_names
        if self.admin_table not in preferred and preferred:
            self.admin_table = preferred[0]

        selector = ctk.CTkFrame(page, fg_color="#1c1719", corner_radius=10, border_width=1, border_color=CARD_BORDER)
        selector.pack(anchor="center", pady=(0, 10))
        for table_name in preferred:
            selected = table_name == self.admin_table
            ctk.CTkButton(
                selector,
                text=table_name,
                width=110,
                height=38,
                corner_radius=8,
                fg_color=ACCENT_BLUE if selected else "transparent",
                hover_color="#008f77" if selected else CARD_HOVER,
                text_color="#191516" if selected else TEXT_WHITE,
                font=ctk.CTkFont(size=13, weight="bold" if selected else "normal"),
                command=lambda name=table_name: self._select_admin_table(name),
            ).pack(side="left", padx=3, pady=3)

        panel = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        panel.pack(fill="x", expand=False)
        panel.grid_columnconfigure(0, weight=1)

        columns, rows = get_table_data(self.admin_table, db_name=db_name, limit=None)
        if self.admin_table == "users":
            count_by_user = {
                int(item["user_id"]): item.get("session_count", 0)
                for item in get_all_users()
                if item.get("user_id") is not None
            }
            rows = [dict(row, session_count=count_by_user.get(int(row["user_id"]), 0)) for row in rows]

        query = self.admin_search.strip().casefold()
        if query:
            rows = [
                row for row in rows
                if any(
                    query in str(value).casefold()
                    for key, value in row.items()
                    if "password" not in key.casefold() and value is not None
                )
            ]

        total_rows = len(rows)
        page_size = 10
        total_pages = max(1, (total_rows + page_size - 1) // page_size)
        self.admin_page_number = min(max(1, self.admin_page_number), total_pages)
        start_index = (self.admin_page_number - 1) * page_size
        visible_rows = rows[start_index:start_index + page_size]

        tools_row = ctk.CTkFrame(panel, fg_color="transparent")
        tools_row.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 10))
        ctk.CTkLabel(
            tools_row,
            text=f"{self.admin_table} ? {total_rows} records ? showing all records",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_CYAN,
        ).pack(side="left")
        search_box = ctk.CTkFrame(tools_row, fg_color="#181315", corner_radius=8, border_width=1, border_color=CARD_BORDER)
        search_box.pack(side="right")
        search_entry = ctk.CTkEntry(
            search_box,
            width=300,
            height=36,
            placeholder_text=f"Search {self.admin_table}...",
            fg_color="transparent",
            border_width=0,
            text_color=TEXT_WHITE,
        )
        search_entry.pack(side="left", padx=(10, 4))
        if self.admin_search:
            search_entry.insert(0, self.admin_search)
        ctk.CTkButton(
            search_box,
            text="?",
            width=36,
            height=32,
            fg_color="transparent",
            hover_color=CARD_HOVER,
            text_color=COLOR_CYAN,
            command=lambda: self._search_admin_table(search_entry.get()),
        ).pack(side="right", padx=3, pady=2)
        search_entry.bind("<Return>", lambda _event: self._search_admin_table(search_entry.get()))

        if self.admin_table == "users":
            display_columns = [
                ("User ID", "user_id"), ("Name", "name"), ("Email", "email"),
                ("Session Count", "session_count"),
            ]
        else:
            display_columns = [(column.replace("_", " ").title(), column) for column in columns]
        excluded_columns = {"created_at", "transcription", "report", "password"}
        display_columns = [
            (label, key) for label, key in display_columns
            if key.casefold() not in excluded_columns
            and (key in columns or key == "session_count")
        ]
        display_columns = [
            ("Speaking Time (s)" if key.casefold() == "speaking_time" else label, key)
            for label, key in display_columns
        ]
        headers = [("#", None), *display_columns]
        visible_grid_height = min(500, 38 + max(1, len(visible_rows)) * 44)
        grid = ctk.CTkScrollableFrame(
            panel, fg_color="#181315", corner_radius=10, height=visible_grid_height
        )
        grid.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        grid.grid_columnconfigure(0, weight=0, minsize=42)
        for column_index, (label, _key) in enumerate(headers):
            grid.grid_columnconfigure(column_index, weight=0 if label == "#" else 1)
            if label == "#":
                grid.grid_columnconfigure(column_index, minsize=48)
            elif self.admin_table == "users" and label == "Email":
                grid.grid_columnconfigure(column_index, minsize=220, weight=2)
            elif self.admin_table == "users" and label == "Name":
                grid.grid_columnconfigure(column_index, minsize=150)
            elif self.admin_table == "users" and label == "Session Count":
                grid.grid_columnconfigure(column_index, minsize=120)
            elif label.casefold().startswith("speaking time"):
                grid.grid_columnconfigure(column_index, minsize=140)
            ctk.CTkLabel(
                grid,
                text=label,
                height=34,
                fg_color="#221c1e",
                text_color=TEXT_WHITE,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="center",
            ).grid(row=0, column=column_index, sticky="ew", padx=1, pady=1)

        for visible_index, row in enumerate(visible_rows):
            grid_row = visible_index + 1
            row_bg = CARD_BG if visible_index % 2 == 0 else "#1e191b"
            values = [str(start_index + visible_index + 1)]
            values.extend("[hidden]" if "password" in key.casefold() else str(row.get(key) if row.get(key) is not None else "?") for _label, key in display_columns)
            for column_index, ((label, key), value) in enumerate(zip(headers, values)):
                if key and "password" in key.casefold():
                    value = "[hidden]"
                else:
                    value = value if len(value) <= 72 else value[:69] + "..."
                ctk.CTkLabel(
                    grid,
                    text=value,
                    height=44,
                    fg_color=row_bg,
                    text_color=TEXT_WHITE if key not in (None, "session_count") else TEXT_MUTED,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                    justify="center",
                    wraplength=240,
                ).grid(row=grid_row, column=column_index, sticky="nsew", padx=1, pady=1)

        if not visible_rows:
            ctk.CTkLabel(
                grid,
                text="No matching records.",
                height=76,
                text_color=TEXT_MUTED,
            ).grid(row=1, column=0, columnspan=len(headers), sticky="ew", padx=10)

        footer = ctk.CTkFrame(panel, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        first_record = start_index + 1 if total_rows else 0
        last_record = min(start_index + page_size, total_rows)
        ctk.CTkLabel(
            footer,
            text=f"Showing {first_record} to {last_record} of {total_rows} records",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).pack(side="left")
        pager = ctk.CTkFrame(footer, fg_color="transparent")
        pager.pack(side="right")
        ctk.CTkButton(
            pager, text="\u2039", width=38, height=36,
            fg_color="#2b2326" if self.admin_page_number > 1 else "#201b1d",
            text_color=TEXT_WHITE if self.admin_page_number > 1 else TEXT_SUBTLE,
            command=lambda: self._change_admin_page(-1),
        ).pack(side="left", padx=3)
        ctk.CTkLabel(
            pager,
            text=str(self.admin_page_number),
            width=38,
            height=36,
            corner_radius=8,
            fg_color=ACCENT_BLUE,
            text_color="#191516",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            pager, text="\u203a", width=38, height=36,
            fg_color="#2b2326" if self.admin_page_number < total_pages else "#201b1d",
            text_color=TEXT_WHITE if self.admin_page_number < total_pages else TEXT_SUBTLE,
            command=lambda: self._change_admin_page(1),
        ).pack(side="left", padx=3)

    def _select_admin_table(self, table_name):
        self.admin_table = table_name
        self.admin_page_number = 1
        self.admin_search = ""
        self._render_admin_page()

    def _search_admin_table(self, query):
        self.admin_search = query.strip()
        self.admin_page_number = 1
        self._render_admin_page()

    def _change_admin_page(self, offset):
        self.admin_page_number = max(1, self.admin_page_number + offset)
        self._render_admin_page()

    def _open_database_inspector(self):
        """Navigate to the database browser, which requires admin sign-in."""
        self.show_page("admin")

    def _create_settings_view(self):
        frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        header_box = ctk.CTkFrame(scroll, fg_color="transparent")
        header_box.pack(fill="x", pady=(0, 16))

        title = ctk.CTkLabel(
            header_box,
            text="Libraries & AI Models Architecture",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_WHITE,
        )
        title.pack(anchor="w", pady=(0, 4))

        subtitle = ctk.CTkLabel(
            header_box,
            text="Comprehensive reference of all artificial intelligence models, computer vision engines, and libraries powering SpeakWise AI.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
        )
        subtitle.pack(anchor="w")

        sections = [
            (
                "🧠  Artificial Intelligence & Machine Learning Models",
                COLOR_CYAN,
                [
                    ("CrisperWhisper 2.0 (ASR)", "crisperwhisper==2.0.2", "Advanced automatic speech recognition (ASR) engine with verbatim transcription. Accurately converts speech to text while preserving hesitation markers, repeated words, and filler vocalizations."),
                    ("Google Gemini 2.5 Flash / Pro (LLM)", "google-genai", "Large Language Model powering real-time conversational extempore coaching, dynamic 17+ category speech topic generation, structure outlining, and speech relevance evaluation."),
                    ("MediaPipe Face Mesh (3D Landmark)", "mediapipe==1.0.1", "Real-time 3D facial landmark pipeline detecting 468+ facial coordinates for iris gaze estimation, camera eye contact percentage, and head stability tracking."),
                    ("PyTorch Deep Learning Engine", "torch==2.8.0", "Core tensor and neural network computation framework executing transformer model inferences for speech transcription and audio embeddings."),
                ]
            ),
            (
                "🎙️  Audio Processing & Acoustic Analysis",
                COLOR_TEAL,
                [
                    ("SoundDevice", "sounddevice==0.5.6", "Low-latency audio I/O streaming library interfacing with PortAudio for live microphone recording, sample buffering, and multi-channel input handling."),
                    ("Librosa", "librosa==0.11.0", "Acoustic signal processing package used for audio time-series analysis, silent interval segmentation, pause duration measurement, and speech pace extraction."),
                    ("SciPy", "scipy==1.17.1", "Scientific computing library utilized for WAV audio I/O encoding (scipy.io.wavfile), sample rate standardization (16 kHz), and digital signal conditioning."),
                ]
            ),
            (
                "👁️  Computer Vision & Video Processing",
                COLOR_ICE,
                [
                    ("OpenCV (Open Source Computer Vision)", "opencv-python==5.0.0.93", "Real-time computer vision library handling live webcam video capture, multi-threaded frame processing, AVI/MP4 video encoding, and coordinate mapping."),
                ]
            ),
            (
                "💻  User Interface & Visualizations",
                COLOR_CYAN,
                [
                    ("CustomTkinter", "customtkinter", "Modern desktop graphical user interface framework providing dark-mode styling, responsive containers, glassmorphism cards, and UI animations."),
                    ("Pillow (PIL)", "pillow", "Python Imaging Library for image decoding, dynamic frame rendering, icon scaling, and graphical transformations."),
                    ("Tkinter Native Graphics Canvas", "tkinter", "Vector drawing engine rendering real-time animated audio waveforms, speedometers, circular dials, and progress donuts."),
                ]
            ),
            (
                "🗄️  Database, Security & Backend",
                COLOR_RUBY,
                [
                    ("MySQL Connector Python", "mysql-connector-python", "Enterprise relational database driver connecting to MySQL (speakwise) for persisting users, practice sessions, and multimodal evaluation reports."),
                    ("BCrypt", "bcrypt", "Cryptographic password hashing algorithm with adaptive salt work factors for secure user authentication."),
                    ("Python-DotEnv", "python-dotenv", "Secure environment configuration management for managing API keys and credentials."),
                ]
            ),
        ]

        for s_title, s_color, items in sections:
            sec_card = ctk.CTkFrame(scroll, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
            sec_card.pack(fill="x", pady=(0, 14))

            sec_in = ctk.CTkFrame(sec_card, fg_color="transparent")
            sec_in.pack(fill="both", expand=True, padx=20, pady=16)

            h_lbl = ctk.CTkLabel(
                sec_in,
                text=s_title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
                text_color=s_color,
            )
            h_lbl.pack(anchor="w", pady=(0, 10))

            for name, pkg, desc in items:
                row = ctk.CTkFrame(sec_in, fg_color="#181315", corner_radius=10, border_width=1, border_color=CARD_BORDER)
                row.pack(fill="x", pady=4)

                r_in = ctk.CTkFrame(row, fg_color="transparent")
                r_in.pack(fill="both", expand=True, padx=14, pady=10)

                top = ctk.CTkFrame(r_in, fg_color="transparent")
                top.pack(fill="x", pady=(0, 3))

                nl = ctk.CTkLabel(top, text=name, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_WHITE)
                nl.pack(side="left")

                badge = ctk.CTkLabel(
                    top,
                    text=f" {pkg} ",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                    fg_color="#221c1e",
                    text_color=COLOR_CYAN,
                    corner_radius=6,
                )
                badge.pack(side="right")

                dl = ctk.CTkLabel(
                    r_in,
                    text=desc,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                    text_color=TEXT_MUTED,
                    justify="left",
                    wraplength=780,
                    anchor="w",
                )
                dl.pack(anchor="w")

        return frame



if __name__ == "__main__":
    app = SpeakWiseApp()

    def _close_app():
        app._stop_home_background_video()
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", _close_app)
    app.mainloop()

