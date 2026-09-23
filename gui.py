import os
import sys
import json
import time
import threading
import winsound
import tkinter as tk
from tkinter import messagebox
from dotenv import load_dotenv
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2 as cv

load_dotenv()

# Backend imports
import speakwise_database
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
)
import login
from login import hash_password, verify_password, save_session
import topics
from topics import get_random_topic, get_all_categories, CATEGORIES
import ai
from ai import ai_prepare, analyze_relevance, CoachChatSession
import report
from report import print_report, calculate_overall
import audio
import video_capture
from filler_detection import detect_fillers
from transcription import transcribe_audio
from video_analysis import analyze_video
from audio_text import detect_pauses
from recording_paths import generate_recording_paths

# Set dark theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Theme Palette (matching high-fidelity mockup)
BG_DARK = "#090d14"
SIDEBAR_BG = "#06090e"
CARD_BG = "#101622"
CARD_BORDER = "#1b2536"
CARD_ACTIVE_BORDER = "#3b82f6"
CARD_HOVER = "#151d2c"
CARD_ACTIVE_BG = "#131f33"
ACCENT_BLUE = "#3b82f6"
ACCENT_PURPLE = "#8b5cf6"
ACCENT_CYAN = "#06b6d4"
ACCENT_EMERALD = "#10b981"
ACCENT_ORANGE = "#f59e0b"
TEXT_WHITE = "#f8fafc"
TEXT_MUTED = "#94a3b8"
TEXT_SUBTLE = "#64748b"


# Category Definitions with metadata matching the 8-card grid
PRESET_CATEGORIES = [
    {
        "id": "Technology",
        "name": "Technology",
        "icon": "💻",
        "desc": "Innovation, AI, gadgets and the digital world",
        "color": "#3b82f6",
        "backend_key": "Technology & Artificial Intelligence",
    },
    {
        "id": "Science",
        "name": "Science",
        "icon": "🧪",
        "desc": "Discoveries, research and the natural world",
        "color": "#10b981",
        "backend_key": "Scientific Wonders & Quantum Concepts",
    },
    {
        "id": "History",
        "name": "History",
        "icon": "🏛️",
        "desc": "Events, people and turning points",
        "color": "#f59e0b",
        "backend_key": "History & Historical Mysteries",
    },
    {
        "id": "Business",
        "name": "Business",
        "icon": "📈",
        "desc": "Economy, leadership and entrepreneurship",
        "color": "#8b5cf6",
        "backend_key": "Business, Startups & Economics",
    },
    {
        "id": "Society",
        "name": "Society",
        "icon": "👥",
        "desc": "People, culture and modern life",
        "color": "#ec4899",
        "backend_key": "Society & Modern Media",
    },
    {
        "id": "Environment",
        "name": "Environment",
        "icon": "🌿",
        "desc": "Nature, climate and sustainability",
        "color": "#14b8a6",
        "backend_key": "Environment & Climate Sustainability",
    },
    {
        "id": "Entertainment",
        "name": "Entertainment",
        "icon": "🎮",
        "desc": "Movies, music, games and pop culture",
        "color": "#f43f5e",
        "backend_key": "Literature, Cinema & Storytelling",
    },
    {
        "id": "Random",
        "name": "Random",
        "icon": "🎲",
        "desc": "Surprise me with anything!",
        "color": "#6366f1",
        "backend_key": None,
    },
]

# Time Options
DURATION_OPTIONS = [
    {"label": "30\nSeconds", "seconds": 30, "display": "30 Seconds"},
    {"label": "1\nMinute", "seconds": 60, "display": "1 Minute"},
    {"label": "2\nMinutes", "seconds": 120, "display": "2 Minutes"},
    {"label": "5\nMinutes", "seconds": 300, "display": "5 Minutes"},
    {"label": "10\nMinutes", "seconds": 600, "display": "10 Minutes"},
]


class SpeakWiseApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SpeakWise AI — Practice. Analyze. Improve.")
        self.geometry("1920x1080")
        self.minsize(1280, 720)
        self.configure(fg_color=BG_DARK)

        # Open in maximized/full screen mode when executed
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass
        self.after(50, self._ensure_maximized)

        # Fullscreen toggle shortcuts (F11 to toggle fullscreen, Escape to exit)
        self.bind("<F11>", self._toggle_fullscreen)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        # Database initialization
        try:
            initialize_database()
        except Exception as e:
            print(f"[DB Notice] {e}")

        # State (Guest by default, user can sign in or sign up)
        self.current_user = None
        self._init_user()

        # Speech Practice State
        self.current_step = 1  # 1: Topic, 2: Prepare, 3: Speak, 4: Results
        self.selected_category = PRESET_CATEGORIES[0]  # Technology default
        self.selected_duration = DURATION_OPTIONS[2]   # 2 Minutes default
        self.current_topic_data = {
            "title": "The Impact of Artificial Intelligence on Education",
            "category": "Technology",
            "difficulty": "Medium",
            "description": "Explore how AI is transforming the way we learn, teach and access knowledge. Discuss the benefits, challenges and what the future might look like.",
            "focus_points": [
                "Current applications of AI in education",
                "Benefits and personalized learning opportunities",
                "Challenges, ethics and academic integrity concerns",
                "The evolving future role of human educators",
            ],
        }

        # Build Main Frame Layout
        self._build_app_shell()

        # Open at Home page by default with Sign In / Sign Up options
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

    def _init_user(self):
        """Auto-load primary active user from MySQL so all speech sessions are saved to database."""
        try:
            users = get_all_users()
            if users:
                self.current_user = {
                    "user_id": users[0]["user_id"],
                    "name": users[0]["name"],
                    "email": users[0]["email"],
                }
            else:
                self.current_user = None
        except Exception:
            self.current_user = None

    # ============================================================
    # MAIN APP SHELL (SIDEBAR + TOP HEADER + MAIN CONTAINER)
    # ============================================================

    def _build_app_shell(self):
        self.grid_columnconfigure(0, weight=0, minsize=260)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --------------------------------------------------------
        # 1. LEFT SIDEBAR
        # --------------------------------------------------------
        self.sidebar = ctk.CTkFrame(
            self,
            fg_color=SIDEBAR_BG,
            corner_radius=0,
            border_width=1,
            border_color="#121a26",
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(7, weight=1)

        # App Logo & Header
        logo_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_box.grid(row=0, column=0, padx=24, pady=(28, 24), sticky="w")

        logo_title = ctk.CTkLabel(
            logo_box,
            text="SpeakWise AI",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT_WHITE,
        )
        logo_title.pack(anchor="w")

        logo_sub = ctk.CTkLabel(
            logo_box,
            text="Practice. Analyze. Improve.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED,
        )
        logo_sub.pack(anchor="w", pady=(2, 0))

        # Navigation Buttons
        self.nav_buttons = {}
        nav_items = [
            ("home", "  🏠  Home"),
            ("practice", "  🎙️  Practice"),
            ("history", "  🕒  History"),
            ("profile", "  👤  Profile"),
            ("settings", "  ⚙️  Settings"),
        ]

        for i, (key, label) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=14),
                anchor="w",
                fg_color="transparent",
                text_color=TEXT_MUTED,
                hover_color=CARD_BG,
                corner_radius=10,
                height=44,
                command=lambda k=key: self.show_page(k),
            )
            btn.grid(row=i, column=0, padx=16, pady=4, sticky="ew")
            self.nav_buttons[key] = btn

        # Sidebar Bottom Info
        bot_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bot_frame.grid(row=8, column=0, padx=20, pady=20, sticky="sew")

        quote_lbl = ctk.CTkLabel(
            bot_frame,
            text='“Progress turns\npractice into\npossibilities.”',
            font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"),
            text_color=TEXT_SUBTLE,
            justify="left",
        )
        quote_lbl.pack(anchor="w", pady=(0, 14))

        v_lbl = ctk.CTkLabel(
            bot_frame,
            text="SpeakWise AI",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#475569",
        )
        v_lbl.pack(anchor="w")

        # --------------------------------------------------------
        # 2. MAIN CONTAINER & TOP BAR
        # --------------------------------------------------------
        self.main_area = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        # Top Bar (Stepper Progress + User Profile)
        self._build_top_bar()

        # Dynamic Content Pages
        self.pages_container = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.pages_container.grid(row=1, column=0, sticky="nsew", padx=(32, 2), pady=(0, 16))
        self.pages_container.grid_rowconfigure(0, weight=1)
        self.pages_container.grid_columnconfigure(0, weight=1)

        # Build Pages
        self.pages = {}
        self.pages["home"] = self._create_home_view()
        self.pages["practice"] = self._create_practice_view()
        self.pages["history"] = self._create_history_view()
        self.pages["reports"] = self._create_reports_view()
        self.pages["profile"] = self._create_profile_view()
        self.pages["settings"] = self._create_settings_view()

    def _build_top_bar(self):
        """Build top progress stepper bar and user badge."""
        self.top_bar = ctk.CTkFrame(self.main_area, fg_color="transparent", height=70)
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=40, pady=(16, 12))
        self.top_bar.grid_columnconfigure(0, weight=1)
        self.top_bar.grid_columnconfigure(1, weight=0)

        # Stepper Progress Container (Center)
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

            # Number/Icon circle
            circle = ctk.CTkButton(
                s_box,
                text=def_icon,
                width=32,
                height=32,
                corner_radius=16,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                fg_color=ACCENT_BLUE if step_num == 1 else "#162030",
                text_color=TEXT_WHITE if step_num == 1 else TEXT_MUTED,
                hover=False,
            )
            circle.pack(side="left", padx=(0, 8))

            name_lbl = ctk.CTkLabel(
                s_box,
                text=step_name,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold" if step_num == 1 else "normal"),
                text_color=TEXT_WHITE if step_num == 1 else TEXT_MUTED,
            )
            name_lbl.pack(side="left")

            self.step_indicators[step_num] = (circle, name_lbl, done_icon, def_icon)

            if idx < len(steps) - 1:
                line = ctk.CTkFrame(stepper_frame, width=22, height=2, fg_color="#1c2738")
                line.pack(side="left", padx=(4, 14))

        # Top Right (Quote & User Avatar Profile)
        right_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        right_box.grid(row=0, column=1, sticky="e")

        quote_top = ctk.CTkLabel(
            right_box,
            text='"Great conversations start with great topics."',
            font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"),
            text_color=TEXT_SUBTLE,
        )
        quote_top.pack(side="left", padx=(0, 24))

        # User Pill (Clickable to Log in or Register)
        if self.current_user:
            u_name = self.current_user.get("name", "User")
            initials = "".join([part[0].upper() for part in u_name.split()[:2]]) or "U"
            role_text = "Student"
            circle_bg = ACCENT_BLUE
        else:
            u_name = "Sign In / Register"
            initials = "👤"
            role_text = "Guest Mode"
            circle_bg = "#1f293d"

        user_card = ctk.CTkFrame(right_box, fg_color="#101724", corner_radius=20, border_width=1, border_color=CARD_BORDER, cursor="hand2")
        user_card.pack(side="left")

        self.top_u_circle = ctk.CTkLabel(
            user_card,
            text=initials,
            width=32,
            height=32,
            corner_radius=16,
            fg_color=circle_bg,
            text_color=TEXT_WHITE,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.top_u_circle.pack(side="left", padx=(4, 8), pady=4)

        u_info = ctk.CTkFrame(user_card, fg_color="transparent")
        u_info.pack(side="left", padx=(0, 12))

        self.top_u_name_lbl = ctk.CTkLabel(
            u_info,
            text=u_name,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=TEXT_WHITE,
        )
        self.top_u_name_lbl.pack(anchor="w")

        self.top_u_role_lbl = ctk.CTkLabel(
            u_info,
            text=role_text,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_MUTED,
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
                name_lbl.configure(text_color=TEXT_WHITE, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
            elif s_num < step_num:
                circle.configure(fg_color="#1e3a8a", text_color=TEXT_WHITE, text=done_icon)
                name_lbl.configure(text_color=TEXT_MUTED, font=ctk.CTkFont(family="Segoe UI", size=13))
            else:
                circle.configure(fg_color="#162030", text_color=TEXT_MUTED, text=def_icon)
                name_lbl.configure(text_color=TEXT_MUTED, font=ctk.CTkFont(family="Segoe UI", size=13))

    def start_new_practice_session(self):
        """Start a completely new practice session from Step 1 with a fresh topic."""
        self._cancel_prep_timer()
        if getattr(self, "_audio_is_playing", False):
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
            self._audio_is_playing = False

        self.current_step = 1
        self.update_stepper(1)

        # Generate fresh topic for the active category
        cat_backend = self.selected_category.get("backend_key")
        try:
            cat_name, topic_title = get_random_topic(cat_backend)
        except Exception as e:
            print(f"[Topic Gen Notice] {e}")
            topic_title = "The Evolution of Modern Artificial Intelligence"

        focus_pts = [
            f"Core foundations and key aspects of {topic_title.lower()}",
            "Practical examples and real-world relevance",
            "Perspectives, debates and potential challenges",
            "Key takeaway message and future outlook",
        ]
        desc = f"Examine the core themes and implications of '{topic_title}'. Share your thoughts, real-world examples, and structure a clear, engaging delivery."

        self.current_topic_data = {
            "title": topic_title,
            "category": self.selected_category["name"],
            "difficulty": "Medium",
            "description": desc,
            "focus_points": focus_pts,
        }

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

    def show_page(self, page_key):
        """Switch navigation page."""
        if page_key == "practice" and self.current_step == 4:
            self.start_new_practice_session()
            return

        for key, btn in self.nav_buttons.items():
            if key == page_key:
                btn.configure(
                    fg_color="#152030",
                    text_color=TEXT_WHITE,
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=TEXT_MUTED,
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="normal"),
                )

        # Stop audio playback if navigating away from report
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
        elif page_key == "history":
            self._render_history_items()
        elif page_key == "reports":
            if not self.reports_container.winfo_children():
                self._render_speech_report(self.reports_container)

        for p in self.pages.values():
            p.grid_remove()

        if page_key in self.pages:
            self.pages[page_key].grid(row=0, column=0, sticky="nsew")

    # ============================================================
    # TOPIC SELECTION / PRACTICE PAGE (MATCHING THE SCREENSHOT)
    # ============================================================

    def _create_practice_view(self):
        self.practice_container = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        self.practice_container.grid_columnconfigure(0, weight=1)
        self.practice_container.grid_rowconfigure(0, weight=1)

        # Build Step 1 view by default
        self._build_step1_topic_selection()
        return self.practice_container

    def _build_step1_topic_selection(self):
        """Construct the exact Topic Selection Page from the user's mockup."""
        self.update_stepper(1)

        for w in self.practice_container.winfo_children():
            w.destroy()

        # Main Scrollable Frame for fluid layout
        scroll = ctk.CTkScrollableFrame(self.practice_container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        scroll.grid_columnconfigure(0, weight=6)  # Left column (60%)
        scroll.grid_columnconfigure(1, weight=4)  # Right column (40%)

        # --------------------------------------------------------
        # HEADER (STEP 1 OF 4 — Choose Your Topic)
        # --------------------------------------------------------
        header_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))

        step_tag = ctk.CTkLabel(
            header_frame,
            text="STEP 1 OF 4",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT_BLUE,
        )
        step_tag.pack(anchor="w")

        main_title = ctk.CTkLabel(
            header_frame,
            text="Choose Your Topic",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color=TEXT_WHITE,
        )
        main_title.pack(anchor="w", pady=(2, 4))

        main_sub = ctk.CTkLabel(
            header_frame,
            text="Select a category, set your speaking time, and get an AI-generated topic tailored for you.",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=TEXT_MUTED,
        )
        main_sub.pack(anchor="w")

        # --------------------------------------------------------
        # LEFT COLUMN: Category Grid + Speaking Time + Tip
        # --------------------------------------------------------
        left_col = ctk.CTkFrame(scroll, fg_color="transparent")
        left_col.grid(row=1, column=0, sticky="nsew", padx=(0, 20))

        # 1. Section: Select a Category
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
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=TEXT_WHITE,
        )
        cat_title.pack(anchor="w")

        cat_sub = ctk.CTkLabel(
            cat_title_box,
            text="Choose an area that interests you.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED,
        )
        cat_sub.pack(anchor="w")

        # 8 Category Cards Grid (4 columns x 2 rows)
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

            # Checkmark badge container
            top_bar = ctk.CTkFrame(card, fg_color="transparent")
            top_bar.pack(fill="x", padx=12, pady=(12, 0))

            # Icon Box
            icon_box = ctk.CTkFrame(
                top_bar,
                width=36,
                height=36,
                corner_radius=8,
                fg_color="#182334",
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

            # Title & Desc
            c_name = ctk.CTkLabel(
                card,
                text=cat["name"],
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=TEXT_WHITE,
            )
            c_name.pack(anchor="w", padx=14, pady=(10, 2))

            c_desc = ctk.CTkLabel(
                card,
                text=cat["desc"],
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=TEXT_MUTED,
                justify="left",
                wraplength=120,
            )
            c_desc.pack(anchor="w", padx=14, pady=(0, 14))

            # Bind click
            for widget in (card, top_bar, icon_box, icon_lbl, c_name, c_desc):
                widget.bind("<Button-1>", lambda e, c=cat: self._on_select_category(c))

            self.category_card_widgets[cat["id"]] = (card, check_lbl)

        # 2. Section: Set Speaking Time
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
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=TEXT_WHITE,
        )
        time_title.pack(anchor="w")

        time_sub = ctk.CTkLabel(
            time_title_box,
            text="Choose how long you want to speak.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED,
        )
        time_sub.pack(anchor="w")

        # 5 Speaking Duration Cards Row
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
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=TEXT_WHITE,
                justify="center",
            )
            t_lbl.pack(expand=True, pady=(0, 8))

            for widget in (t_card, t_top, t_lbl):
                widget.bind("<Button-1>", lambda e, d=dur: self._on_select_duration(d))

            self.duration_card_widgets[dur["seconds"]] = (t_card, t_check)

        # 3. Tip Banner Box
        tip_box = ctk.CTkFrame(
            left_col,
            fg_color="#101724",
            corner_radius=12,
            border_width=1,
            border_color="#1c283a",
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
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#f59e0b",
        )
        tip_head.pack(anchor="w")

        tip_body = ctk.CTkLabel(
            tip_text_box,
            text="Choose a topic you find interesting. You'll speak more naturally and confidently!",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED,
        )
        tip_body.pack(anchor="w")

        # --------------------------------------------------------
        # RIGHT COLUMN: Your Topic Card + AI Generation + CTA
        # --------------------------------------------------------
        right_col = ctk.CTkFrame(scroll, fg_color="transparent")
        right_col.grid(row=1, column=1, sticky="nsew", padx=(20, 0))

        # Section 3 Header: Your Topic + Generate Another Button
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
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=TEXT_WHITE,
        )
        r_title.pack(anchor="w")

        r_sub = ctk.CTkLabel(
            r_title_box,
            text="Generate a topic using AI or pick another.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED,
        )
        r_sub.pack(anchor="w")

        # Generate Another Button (Right aligned)
        self.btn_gen_another = ctk.CTkButton(
            r_head,
            text="🔄 Generate Another",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#182334",
            text_color=TEXT_WHITE,
            hover_color=CARD_HOVER,
            border_width=1,
            border_color=CARD_BORDER,
            corner_radius=8,
            height=34,
            command=self._generate_fresh_topic,
        )
        self.btn_gen_another.pack(side="right")

        # Topic Hero Banner Card
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

        # Tags Row (Category Pill + Difficulty Pill)
        tags_row = ctk.CTkFrame(hero_inner, fg_color="transparent")
        tags_row.pack(anchor="w", pady=(0, 12))

        self.pill_cat = ctk.CTkLabel(
            tags_row,
            text=f" ⚙️ {self.current_topic_data['category']} ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#1e293b",
            text_color=ACCENT_CYAN,
            corner_radius=6,
        )
        self.pill_cat.pack(side="left", padx=(0, 8))

        self.pill_diff = ctk.CTkLabel(
            tags_row,
            text=f" 🔥 {self.current_topic_data['difficulty']} ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#2b1828",
            text_color="#f43f5e",
            corner_radius=6,
        )
        self.pill_diff.pack(side="left")

        # Big Topic Title
        self.lbl_topic_title = ctk.CTkLabel(
            hero_inner,
            text=self.current_topic_data["title"],
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_WHITE,
            justify="left",
            wraplength=480,
            anchor="w",
        )
        self.lbl_topic_title.pack(anchor="w", pady=(0, 10))

        # Topic Description
        self.lbl_topic_desc = ctk.CTkLabel(
            hero_inner,
            text=self.current_topic_data["description"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_MUTED,
            justify="left",
            wraplength=480,
            anchor="w",
        )
        self.lbl_topic_desc.pack(anchor="w")

        # Topic Details Sub-Card
        details_card = ctk.CTkFrame(
            right_col,
            fg_color="#0c121d",
            corner_radius=14,
            border_width=1,
            border_color="#182335",
        )
        details_card.pack(fill="x", pady=(0, 20))

        d_inner = ctk.CTkFrame(details_card, fg_color="transparent")
        d_inner.pack(fill="both", expand=True, padx=20, pady=16)

        d_head = ctk.CTkLabel(
            d_inner,
            text="Topic Details",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=TEXT_WHITE,
        )
        d_head.pack(anchor="w", pady=(0, 12))

        # Rows: Category, Speaking Time, Difficulty
        self.lbl_d_cat = self._add_detail_row(d_inner, "⚙️  Category", self.current_topic_data["category"])
        self.lbl_d_time = self._add_detail_row(d_inner, "⏱️  Speaking Time", self.selected_duration["display"])
        self.lbl_d_diff = self._add_detail_row(d_inner, "📊  Difficulty Level", self.current_topic_data["difficulty"])

        # Focus Points List
        fp_head = ctk.CTkLabel(
            d_inner,
            text="📝  Suggested Focus Points",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_MUTED,
        )
        fp_head.pack(anchor="w", pady=(10, 6))

        self.focus_points_frame = ctk.CTkFrame(d_inner, fg_color="transparent")
        self.focus_points_frame.pack(fill="x")

        self._render_focus_points()

        # Start Preparation CTA Button
        self.btn_start_prep = ctk.CTkButton(
            right_col,
            text="Start Preparation  ➔",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
            height=50,
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
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_MUTED,
        )
        l.pack(side="left")

        v = ctk.CTkLabel(
            row,
            text=val,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
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
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=TEXT_MUTED,
                justify="left",
                wraplength=440,
                anchor="w",
            )
            pt_lbl.pack(anchor="w", pady=2)

    # --------------------------------------------------------
    # INTERACTION HANDLERS FOR TOPIC SELECTION
    # --------------------------------------------------------

    def _on_select_category(self, cat):
        self.selected_category = cat

        # Update category card highlights
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

        # Automatically fetch fresh topic for this category
        self._generate_fresh_topic()

    def _on_select_duration(self, dur):
        self.selected_duration = dur

        # Update duration card highlights
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

        # Update Details Card
        if hasattr(self, "lbl_d_time"):
            self.lbl_d_time.configure(text=dur["display"])

    def _generate_fresh_topic(self):
        """Asynchronously query Gemini AI topic generator and update right-hand card."""
        if hasattr(self, "btn_gen_another") and self.btn_gen_another.winfo_exists():
            self.btn_gen_another.configure(text="⌛ Generating...", state="disabled")

        cat_backend = self.selected_category["backend_key"]

        def _worker():
            try:
                cat_name, topic_title = get_random_topic(cat_backend)
            except Exception as e:
                print(f"[Topic Gen Notice] {e}")
                topic_title = "The Evolution of Modern Artificial Intelligence"

            # Generate smart focus points & description
            focus_pts = [
                f"Core foundations and key aspects of {topic_title.lower()}",
                "Practical examples and real-world relevance",
                "Perspectives, debates and potential challenges",
                "Key takeaway message and future outlook",
            ]

            desc = f"Examine the core themes and implications of '{topic_title}'. Share your thoughts, real-world examples, and structure a clear, engaging delivery."

            self.current_topic_data = {
                "title": topic_title,
                "category": self.selected_category["name"],
                "difficulty": "Medium",
                "description": desc,
                "focus_points": focus_pts,
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
            self._render_focus_points()

            if hasattr(self, "btn_gen_another") and self.btn_gen_another.winfo_exists():
                self.btn_gen_another.configure(text="🔄 Generate Another", state="normal")
        except Exception:
            pass

    # ============================================================
    # STEP 2: PREPARATION & AI COACH CHAT
    # ============================================================

    # ============================================================
    # STEP 2: PREPARATION & AI COACH CHAT (HIGH-FIDELITY REDESIGN)
    # ============================================================

    def _advance_to_step2_prepare(self):
        """Construct Step 2: Prepare with AI matching mockup layout and features."""
        self._cancel_prep_timer()
        self.update_stepper(2)

        # Prepare state (5 minutes = 300 seconds)
        self.prep_time_total = 300  # 5 minutes prep time
        self.prep_time_remaining = 300  # Starts at 05:00
        self.prep_timer_running = False  # Starts only when AI Coach is ready
        self.prep_timer_after_id = None

        self.prep_goals = [
            {"text": "Understand the topic and its key aspects", "done": False},
            {"text": "Identify 3–5 main talking points", "done": False},
            {"text": "Plan a clear structure (introduction, body, conclusion)", "done": False},
            {"text": "Gather interesting facts or examples", "done": False},
            {"text": "Feel confident before you start speaking", "done": False},
        ]
        self.prep_goal_widgets = []

        # Initialize AI Coach session asynchronously (non-blocking)
        self.coach_session = None

        for w in self.practice_container.winfo_children():
            w.destroy()

        # Main Page Container
        main_frame = ctk.CTkFrame(self.practice_container, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=6, uniform="step2_grid")  # Left Chat (~60%)
        main_frame.grid_columnconfigure(1, weight=4, uniform="step2_grid")  # Right Panel (~40%)

        # --------------------------------------------------------
        # TOP HEADER: Back Link + Page Title + Subtitle
        # --------------------------------------------------------
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        btn_back_top = ctk.CTkButton(
            header_frame,
            text="←  Back to Topic Selection",
            font=ctk.CTkFont(family="Segoe UI", size=13),
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
            font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
            text_color=TEXT_WHITE,
        )
        title_lbl.pack(anchor="w", pady=(0, 2))

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Get insights, talking points and guidance before your speech.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_MUTED,
        )
        sub_lbl.pack(anchor="w")

        # --------------------------------------------------------
        # LEFT COLUMN: Interactive AI Coach Chatbox
        # --------------------------------------------------------
        left_chat_card = ctk.CTkFrame(
            main_frame,
            fg_color="#0b111d",
            corner_radius=16,
            border_width=1,
            border_color="#182335",
        )
        left_chat_card.grid(row=1, column=0, sticky="nsew", padx=(0, 14), pady=(0, 10))
        left_chat_card.grid_rowconfigure(1, weight=1)
        left_chat_card.grid_columnconfigure(0, weight=1)

        # Chat Header
        chat_top = ctk.CTkFrame(left_chat_card, fg_color="#0e1626", height=60, corner_radius=14)
        chat_top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        chat_top.pack_propagate(False)

        c_head_left = ctk.CTkFrame(chat_top, fg_color="transparent")
        c_head_left.pack(side="left", padx=14, pady=10)

        # Robot Icon Badge
        bot_icon_box = ctk.CTkFrame(c_head_left, width=38, height=38, corner_radius=19, fg_color="#1d2d47")
        bot_icon_box.pack(side="left", padx=(0, 12))
        bot_icon_box.pack_propagate(False)

        bot_icon = ctk.CTkLabel(bot_icon_box, text="🤖", font=ctk.CTkFont(size=18))
        bot_icon.pack(expand=True)

        bot_title_box = ctk.CTkFrame(c_head_left, fg_color="transparent")
        bot_title_box.pack(side="left")

        coach_name = ctk.CTkLabel(
            bot_title_box,
            text="SpeakWise Coach",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=TEXT_WHITE,
        )
        coach_name.pack(anchor="w")

        coach_sub = ctk.CTkLabel(
            bot_title_box,
            text="Your AI speaking assistant",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_SUBTLE,
        )
        coach_sub.pack(anchor="w")

        # Clear Chat Button
        btn_clear = ctk.CTkButton(
            chat_top,
            text="🗑️ Clear Chat",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="transparent",
            hover_color="#182436",
            border_width=1,
            border_color="#22334c",
            text_color=TEXT_MUTED,
            corner_radius=8,
            height=32,
            command=self._clear_prep_chat,
        )
        btn_clear.pack(side="right", padx=14, pady=12)

        # Scrollable Chat Stream
        self.prep_chat_scroll = ctk.CTkScrollableFrame(left_chat_card, fg_color="transparent")
        self.prep_chat_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self.prep_chat_scroll.grid_columnconfigure(0, weight=1)

        # Bottom Area: Input Bar + Quick Suggestions
        bottom_chat_area = ctk.CTkFrame(left_chat_card, fg_color="transparent")
        bottom_chat_area.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 12))

        # Input Frame
        input_bar = ctk.CTkFrame(
            bottom_chat_area,
            fg_color="#121b2b",
            corner_radius=12,
            border_width=1,
            border_color="#1f2d44",
            height=48,
        )
        input_bar.pack(fill="x", pady=(0, 10))
        input_bar.pack_propagate(False)

        # Attachment Clip Icon
        clip_lbl = ctk.CTkLabel(
            input_bar,
            text="📎",
            font=ctk.CTkFont(size=16),
            text_color=TEXT_SUBTLE,
            cursor="hand2",
            width=32,
        )
        clip_lbl.pack(side="left", padx=(10, 4))

        # Text Entry
        self.prep_entry = ctk.CTkEntry(
            input_bar,
            placeholder_text="Ask the AI coach anything...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="transparent",
            border_width=0,
            text_color=TEXT_WHITE,
            placeholder_text_color=TEXT_SUBTLE,
        )
        self.prep_entry.pack(side="left", fill="both", expand=True, padx=4)
        self.prep_entry.bind("<Return>", lambda e: self._on_prep_send_click())

        # Blue Send Button (disabled until coach connects)
        self.btn_prep_send = ctk.CTkButton(
            input_bar,
            text="➤",
            width=34,
            height=34,
            corner_radius=17,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
            state="disabled",
            command=self._on_prep_send_click,
        )
        self.btn_prep_send.pack(side="right", padx=8, pady=7)

        # Quick Suggestion Pills Row
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
                font=ctk.CTkFont(family="Segoe UI", size=11),
                fg_color="#111927",
                hover_color="#1c283c",
                border_width=1,
                border_color="#1d2a3e",
                text_color=TEXT_MUTED,
                corner_radius=14,
                height=28,
                command=lambda pt=p_text: self._send_quick_prompt(pt),
            )
            p_btn.pack(side="left", padx=(0, 6), pady=2)

        # --------------------------------------------------------
        # RIGHT COLUMN: Tools, Overview, Goals & Pro Tip
        # --------------------------------------------------------
        right_scroll = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        right_scroll.grid(row=1, column=1, sticky="nsew", padx=(14, 0), pady=(0, 10))
        right_scroll.grid_columnconfigure(0, weight=1)

        # 1. Preparation Time Card
        timer_card = ctk.CTkFrame(
            right_scroll,
            fg_color="#0c1420",
            corner_radius=14,
            border_width=1,
            border_color="#1b2536",
        )
        timer_card.pack(fill="x", pady=(0, 14))

        t_inner = ctk.CTkFrame(timer_card, fg_color="transparent")
        t_inner.pack(fill="both", expand=True, padx=18, pady=16)

        # Header
        t_head = ctk.CTkFrame(t_inner, fg_color="transparent")
        t_head.pack(fill="x", pady=(0, 8))

        t_icon_title = ctk.CTkLabel(
            t_head,
            text="⏱️  Preparation Time (5 Mins)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_WHITE,
        )
        t_icon_title.pack(side="left")

        # Big Clock & Pause Button Row
        clock_row = ctk.CTkFrame(t_inner, fg_color="transparent")
        clock_row.pack(fill="x", pady=(0, 8))

        mins = self.prep_time_remaining // 60
        secs = self.prep_time_remaining % 60
        self.lbl_prep_clock = ctk.CTkLabel(
            clock_row,
            text=f"{mins:02d}:{secs:02d}",
            font=ctk.CTkFont(family="Segoe UI", size=44, weight="bold"),
            text_color=TEXT_WHITE,
        )
        self.lbl_prep_clock.pack(side="left")

        self.btn_prep_pause = ctk.CTkButton(
            clock_row,
            text="⏸",
            width=46,
            height=46,
            corner_radius=23,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            fg_color="#162234",
            hover_color="#1f3048",
            text_color=TEXT_WHITE,
            command=self._toggle_prep_timer,
        )
        self.btn_prep_pause.pack(side="right")

        # Emerald Progress Bar
        self.prep_pbar = ctk.CTkProgressBar(
            t_inner,
            height=6,
            corner_radius=3,
            progress_color=ACCENT_EMERALD,
            fg_color="#172436",
        )
        self.prep_pbar.pack(fill="x", pady=(0, 6))
        self.prep_pbar.set(self.prep_time_remaining / self.prep_time_total)

        # Subtitle
        self.lbl_prep_sub = ctk.CTkLabel(
            t_inner,
            text="⏳ Waiting for AI Coach to connect...",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=ACCENT_CYAN,
        )
        self.lbl_prep_sub.pack(anchor="w")

        # 2. Topic Overview Card
        overview_card = ctk.CTkFrame(
            right_scroll,
            fg_color=CARD_BG,
            corner_radius=14,
            border_width=1,
            border_color=CARD_BORDER,
        )
        overview_card.pack(fill="x", pady=(0, 14))

        o_inner = ctk.CTkFrame(overview_card, fg_color="transparent")
        o_inner.pack(fill="both", expand=True, padx=18, pady=16)

        o_head_row = ctk.CTkFrame(o_inner, fg_color="transparent")
        o_head_row.pack(fill="x", pady=(0, 10))

        o_head_title = ctk.CTkLabel(
            o_head_row,
            text="📄  Topic Overview",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_WHITE,
        )
        o_head_title.pack(side="left")

        btn_chg_topic = ctk.CTkButton(
            o_head_row,
            text="🔄 Change Topic",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent",
            hover_color="#182436",
            border_width=1,
            border_color="#22334c",
            text_color=TEXT_MUTED,
            corner_radius=8,
            height=28,
            command=self._on_back_to_topics,
        )
        btn_chg_topic.pack(side="right")

        # Topic Title
        cur_title = self.current_topic_data.get("title", "The Voynich Manuscript")
        o_title = ctk.CTkLabel(
            o_inner,
            text=cur_title,
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=TEXT_WHITE,
            justify="left",
            wraplength=380,
            anchor="w",
        )
        o_title.pack(anchor="w", pady=(0, 10))

        # Tags Row (Category, Difficulty, Duration)
        tags_row = ctk.CTkFrame(o_inner, fg_color="transparent")
        tags_row.pack(anchor="w", pady=(0, 10))

        cur_cat = self.current_topic_data.get("category", "History")
        cat_badge = ctk.CTkLabel(
            tags_row,
            text=f" 🏛️ {cur_cat} ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#27193b",
            text_color="#c084fc",
            corner_radius=6,
        )
        cat_badge.pack(side="left", padx=(0, 6))

        cur_diff = self.current_topic_data.get("difficulty", "Medium")
        diff_badge = ctk.CTkLabel(
            tags_row,
            text=f" 📊 {cur_diff} ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#172554",
            text_color="#60a5fa",
            corner_radius=6,
        )
        diff_badge.pack(side="left", padx=(0, 6))

        dur_text = self.selected_duration.get("display", "2 Minutes")
        dur_badge = ctk.CTkLabel(
            tags_row,
            text=f" ⏱️ {dur_text} ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#064e3b",
            text_color="#34d399",
            corner_radius=6,
        )
        dur_badge.pack(side="left")

        # Topic Description
        cur_desc = self.current_topic_data.get(
            "description",
            "An unidentified manuscript written in an unknown script, filled with mysterious illustrations. Despite centuries of study, its meaning remains a mystery.",
        )
        o_desc = ctk.CTkLabel(
            o_inner,
            text=cur_desc,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED,
            justify="left",
            wraplength=380,
            anchor="w",
        )
        o_desc.pack(anchor="w")

        # 3. Preparation Goals Card
        goals_card = ctk.CTkFrame(
            right_scroll,
            fg_color=CARD_BG,
            corner_radius=14,
            border_width=1,
            border_color=CARD_BORDER,
        )
        goals_card.pack(fill="x", pady=(0, 14))

        g_inner = ctk.CTkFrame(goals_card, fg_color="transparent")
        g_inner.pack(fill="both", expand=True, padx=18, pady=16)

        g_title = ctk.CTkLabel(
            g_inner,
            text="🎯  Preparation Goals",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_WHITE,
        )
        g_title.pack(anchor="w", pady=(0, 10))

        # Goals List items
        for g_idx, goal in enumerate(self.prep_goals):
            g_row = ctk.CTkFrame(g_inner, fg_color="transparent", cursor="hand2")
            g_row.pack(fill="x", pady=4)

            # Circular Check Icon
            check_circle = ctk.CTkLabel(
                g_row,
                text="◯",
                font=ctk.CTkFont(size=13),
                text_color=TEXT_SUBTLE,
                width=20,
            )
            check_circle.pack(side="left", padx=(0, 8))

            g_lbl = ctk.CTkLabel(
                g_row,
                text=goal["text"],
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=TEXT_MUTED,
                justify="left",
                wraplength=340,
                anchor="w",
            )
            g_lbl.pack(side="left", fill="x", expand=True)

            # Bind click toggle
            for w in (g_row, check_circle, g_lbl):
                w.bind("<Button-1>", lambda e, idx=g_idx: self._toggle_prep_goal(idx))

            self.prep_goal_widgets.append((check_circle, g_lbl))

        # 4. Pro Tip Card
        tip_card = ctk.CTkFrame(
            right_scroll,
            fg_color="#121720",
            corner_radius=12,
            border_width=1,
            border_color="#92400e",
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
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f59e0b",
        )
        tip_title.pack(anchor="w", pady=(0, 2))

        tip_text = ctk.CTkLabel(
            tip_content,
            text="Don't try to memorize a full speech. Focus on understanding the topic and organizing your ideas. Speak naturally!",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cbd5e1",
            justify="left",
            wraplength=330,
            anchor="w",
        )
        tip_text.pack(anchor="w")

        # 5. Ready to Speak CTA Button
        btn_start_speaking = ctk.CTkButton(
            right_scroll,
            text="Start Speaking Now 🎙️",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
            corner_radius=10,
            height=48,
            command=self._advance_to_step3_speak,
        )
        btn_start_speaking.pack(fill="x", pady=(4, 16))

        # Show coach loading waiting state in chat & launch async initialization
        self._render_coach_loading()
        self._init_coach_session_async()

    # ------------------------------------------------------------
    # STEP 2 HELPER METHODS: CHAT, TIMER & GOALS
    # ------------------------------------------------------------

    def _render_coach_loading(self):
        """Show animated waiting screen in chat while Gemini Flash initializes."""
        if not hasattr(self, "prep_chat_scroll") or not self.prep_chat_scroll.winfo_exists():
            return
        for w in self.prep_chat_scroll.winfo_children():
            w.destroy()

        row = ctk.CTkFrame(self.prep_chat_scroll, fg_color="transparent")
        row.pack(fill="x", pady=16, padx=8, anchor="w")

        # Bot Avatar Icon
        avatar = ctk.CTkFrame(row, width=36, height=36, corner_radius=18, fg_color="#1e3a5f")
        avatar.pack(side="left", anchor="n", padx=(0, 10), pady=2)
        avatar.pack_propagate(False)

        a_lbl = ctk.CTkLabel(avatar, text="🤖", font=ctk.CTkFont(size=18))
        a_lbl.pack(expand=True)

        bubble = ctk.CTkFrame(
            row,
            fg_color="#0f1a2e",
            corner_radius=14,
            border_width=1,
            border_color="#1d3455",
        )
        bubble.pack(side="left")

        msg_lbl = ctk.CTkLabel(
            bubble,
            text="⌛ Connecting to SpeakWise Coach via Gemini Flash...\nPreparing your speaking insights & talking points...",
            font=ctk.CTkFont(family="Segoe UI", size=13, slant="italic"),
            text_color=ACCENT_CYAN,
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
            except Exception as e:
                print(f"[Coach Async Notice] {e}")

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
                        text_color=ACCENT_EMERALD,
                    )
                # Start the 5-minute prep timer ONLY when Gemini is connected and ready to chat
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
            fg_color="#1e1b4b",
            text_color="#a78bfa",
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
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=TEXT_WHITE,
        )
        n_lbl.pack(side="left")

        t_lbl = ctk.CTkLabel(
            meta,
            text=ts,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_SUBTLE,
        )
        t_lbl.pack(side="left", padx=(8, 0))

        bubble = ctk.CTkFrame(
            content_col,
            fg_color="#101725",
            corner_radius=12,
            border_width=1,
            border_color="#192638",
        )
        bubble.pack(fill="x", anchor="w")

        msg_lbl = ctk.CTkLabel(
            bubble,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cbd5e1",
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
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_SUBTLE,
        )
        t_lbl.pack(side="right", padx=(0, 8))

        n_lbl = ctk.CTkLabel(
            meta,
            text=first_name,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=TEXT_WHITE,
        )
        n_lbl.pack(side="right")

        bubble = ctk.CTkFrame(
            content_col,
            fg_color="#1d3557",
            corner_radius=12,
            border_width=1,
            border_color="#2a4a75",
        )
        bubble.pack(fill="x", anchor="e")

        msg_lbl = ctk.CTkLabel(
            bubble,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=12),
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
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
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
            except Exception as e:
                print(f"[PrepChat Error] {e}")

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

    def _toggle_prep_goal(self, idx):
        """Toggle checklist state for a preparation goal."""
        if idx >= len(self.prep_goals) or idx >= len(self.prep_goal_widgets):
            return

        self.prep_goals[idx]["done"] = not self.prep_goals[idx]["done"]
        is_done = self.prep_goals[idx]["done"]
        circle_lbl, text_lbl = self.prep_goal_widgets[idx]

        if is_done:
            circle_lbl.configure(text="✓", text_color=ACCENT_EMERALD)
            text_lbl.configure(text_color=TEXT_WHITE)
        else:
            circle_lbl.configure(text="◯", text_color=TEXT_SUBTLE)
            text_lbl.configure(text_color=TEXT_MUTED)

    # ------------------------------------------------------------
    # PREPARATION COUNTDOWN TIMER
    # ------------------------------------------------------------

    def _start_prep_timer(self):
        self.prep_timer_running = True
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

    # ============================================================
    # STEP 3: LIVE RECORDING STAGE
    # ============================================================

    # ============================================================
    # STEP 3: LIVE RECORDING STAGE (EMBEDDED IN-APP CAMERA)
    # ============================================================

    def _advance_to_step3_speak(self):
        """Construct Step 3: Live Speech Recording with embedded camera and circular timer."""
        self._cancel_prep_timer()
        self.update_stepper(3)

        for w in self.practice_container.winfo_children():
            w.destroy()

        dur = self.selected_duration["seconds"]
        self.stop_recording_event = threading.Event()

        # Main Step 3 Container
        main_frame = ctk.CTkFrame(self.practice_container, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=64, uniform="step3_grid")  # Left Video (~64%)
        main_frame.grid_columnconfigure(1, weight=36, uniform="step3_grid")  # Right Panel (~36%)

        # --------------------------------------------------------
        # TOP HEADER: Title + Subtitle
        # --------------------------------------------------------
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="It's Time to Speak!",
            font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
            text_color=TEXT_WHITE,
        )
        title_lbl.pack(anchor="w", pady=(0, 2))

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Speak on the given topic. Be yourself, speak clearly, and do your best!",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_MUTED,
        )
        sub_lbl.pack(anchor="w")

        # --------------------------------------------------------
        # LEFT COLUMN: Embedded Camera Card + Device Badges
        # --------------------------------------------------------
        left_col = ctk.CTkFrame(
            main_frame,
            fg_color="#0c131f",
            corner_radius=16,
            border_width=1,
            border_color="#1a2538",
        )
        left_col.grid(row=1, column=0, sticky="nsew", padx=(0, 14), pady=(0, 10))
        left_col.grid_rowconfigure(1, weight=1)
        left_col.grid_columnconfigure(0, weight=1)

        # 1. Top Card Header (Your Topic + Speaking Time)
        top_info_bar = ctk.CTkFrame(left_col, fg_color="transparent", height=54)
        top_info_bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))

        t_left = ctk.CTkFrame(top_info_bar, fg_color="transparent")
        t_left.pack(side="left")

        doc_icon_box = ctk.CTkFrame(t_left, width=36, height=36, corner_radius=10, fg_color="#1e2d46")
        doc_icon_box.pack(side="left", padx=(0, 10))
        doc_icon_box.pack_propagate(False)

        doc_icon = ctk.CTkLabel(doc_icon_box, text="📄", font=ctk.CTkFont(size=16))
        doc_icon.pack(expand=True)

        t_text_box = ctk.CTkFrame(t_left, fg_color="transparent")
        t_text_box.pack(side="left")

        t_caption = ctk.CTkLabel(
            t_text_box,
            text="Your Topic",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_SUBTLE,
        )
        t_caption.pack(anchor="w")

        t_title = ctk.CTkLabel(
            t_text_box,
            text=self.current_topic_data.get("title", "The Voynich Manuscript"),
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=TEXT_WHITE,
            justify="left",
            wraplength=480,
            anchor="w",
        )
        t_title.pack(anchor="w")

        # Speaking Time (Right aligned)
        t_right = ctk.CTkFrame(top_info_bar, fg_color="transparent")
        t_right.pack(side="right")

        dur_caption = ctk.CTkLabel(
            t_right,
            text="Speaking Time",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_SUBTLE,
        )
        dur_caption.pack(anchor="e")

        dur_val = ctk.CTkLabel(
            t_right,
            text=f"⏱️  {self.selected_duration.get('display', '2 Minutes')}",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=TEXT_WHITE,
        )
        dur_val.pack(anchor="e")

        # 2. Camera Window Active Status Box
        cam_status_card = ctk.CTkFrame(
            left_col,
            fg_color="#070a10",
            corner_radius=14,
            border_width=1,
            border_color="#151e2c",
        )
        cam_status_card.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 14))
        cam_status_card.grid_rowconfigure(0, weight=1)
        cam_status_card.grid_columnconfigure(0, weight=1)

        cam_center = ctk.CTkFrame(cam_status_card, fg_color="transparent")
        cam_center.grid(row=0, column=0)

        icon_box = ctk.CTkFrame(cam_center, width=80, height=80, corner_radius=40, fg_color="#0e1f38")
        icon_box.pack(pady=(0, 16))
        icon_box.pack_propagate(False)

        cam_icon = ctk.CTkLabel(icon_box, text="🎥", font=ctk.CTkFont(size=36))
        cam_icon.pack(expand=True)

        cam_title = ctk.CTkLabel(
            cam_center,
            text="Camera Active in Dedicated Window",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_WHITE,
        )
        cam_title.pack(pady=(0, 6))

        cam_desc = ctk.CTkLabel(
            cam_center,
            text="Your camera feed is live in the 'SpeakWise Camera' window.\nLook naturally at the camera while delivering your speech.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_MUTED,
            justify="center",
        )
        cam_desc.pack(pady=(0, 16))

        pill_box = ctk.CTkLabel(
            cam_center,
            text="  💡 Press 'q' in the camera window or click 'Stop Recording' below to finish early.  ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#17253b",
            text_color=ACCENT_CYAN,
            corner_radius=8,
            height=30,
        )
        pill_box.pack()

        # 3. Bottom Device Badges Row
        dev_row = ctk.CTkFrame(left_col, fg_color="transparent")
        dev_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))

        badges = [
            ("camera", "🎥", "Camera Window\nLive (Active)", "#064e3b", "#34d399"),
            ("mic", "🎙️", "Microphone\nRecording", "#064e3b", "#34d399"),
            ("preview", "👁️", "Eye Contact\nTracking On", "#1e293b", "#94a3b8"),
        ]

        for _, icon, txt, bg_circle, text_col in badges:
            card = ctk.CTkFrame(
                dev_row,
                fg_color="#101726",
                corner_radius=10,
                border_width=1,
                border_color="#1a2538",
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
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=TEXT_WHITE,
                justify="left",
            )
            t_lbl.pack(side="left", pady=6)

        # --------------------------------------------------------
        # RIGHT COLUMN: Circular Timer + Tips + Stop Button
        # --------------------------------------------------------
        right_col = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_col.grid(row=1, column=1, sticky="nsew", padx=(14, 0), pady=(0, 10))
        right_col.grid_columnconfigure(0, weight=1)

        # 1. Circular Countdown Timer Card
        timer_card = ctk.CTkFrame(
            right_col,
            fg_color="#0c131f",
            corner_radius=16,
            border_width=1,
            border_color="#1a2538",
        )
        timer_card.pack(fill="x", pady=(0, 14))

        t_inner = ctk.CTkFrame(timer_card, fg_color="transparent")
        t_inner.pack(fill="both", expand=True, padx=18, pady=16)

        t_h_lbl = ctk.CTkLabel(
            t_inner,
            text="⏱️  Time Remaining",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_WHITE,
        )
        t_h_lbl.pack(anchor="w", pady=(0, 6))

        # Circular Ring Canvas
        self.ring_canvas = tk.Canvas(
            t_inner,
            width=180,
            height=180,
            bg="#0c131f",
            highlightthickness=0,
        )
        self.ring_canvas.pack(pady=(4, 8))
        self._draw_timer_ring(dur, dur)

        sub_encourage = ctk.CTkLabel(
            t_inner,
            text="Keep going! You're doing great!",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT_CYAN,
        )
        sub_encourage.pack()

        # 2. Speaking Tips Card
        tips_card = ctk.CTkFrame(
            right_col,
            fg_color="#0c131f",
            corner_radius=16,
            border_width=1,
            border_color="#1a2538",
        )
        tips_card.pack(fill="x", pady=(0, 14))

        tips_inner = ctk.CTkFrame(tips_card, fg_color="transparent")
        tips_inner.pack(fill="both", expand=True, padx=18, pady=16)

        tips_h = ctk.CTkLabel(
            tips_inner,
            text="💡  Speaking Tips",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_WHITE,
        )
        tips_h.pack(anchor="w", pady=(0, 10))

        speaking_tips = [
            "Look naturally at the camera window",
            "Speak clearly and at a comfortable pace",
            "Stay on topic",
            "Avoid too many filler words (um, uh, like)",
            "Be yourself!",
        ]

        for tip in speaking_tips:
            tip_row = ctk.CTkFrame(tips_inner, fg_color="transparent")
            tip_row.pack(fill="x", pady=3)

            chk = ctk.CTkLabel(
                tip_row,
                text="✓",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=ACCENT_BLUE,
                text_color=TEXT_WHITE,
                width=18,
                height=18,
                corner_radius=9,
            )
            chk.pack(side="left", padx=(0, 8))

            tl = ctk.CTkLabel(
                tip_row,
                text=tip,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#cbd5e1",
                justify="left",
                wraplength=310,
                anchor="w",
            )
            tl.pack(side="left", fill="x", expand=True)

        # 3. Inspirational Quote Card
        quote_card = ctk.CTkFrame(
            right_col,
            fg_color="#090e17",
            corner_radius=12,
            border_width=1,
            border_color="#152030",
        )
        quote_card.pack(fill="x", pady=(0, 14))

        q_inner = ctk.CTkFrame(quote_card, fg_color="transparent")
        q_inner.pack(fill="both", expand=True, padx=14, pady=12)

        q_txt = ctk.CTkLabel(
            q_inner,
            text='“It\'s not about being perfect,\nit\'s about making progress.”',
            font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"),
            text_color=TEXT_SUBTLE,
            justify="center",
        )
        q_txt.pack(expand=True)

        # 4. Stop Recording CTA Button
        self.btn_stop_rec = ctk.CTkButton(
            right_col,
            text="⏹   Stop Recording",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#2b1417",
            hover_color="#3d181c",
            border_width=1,
            border_color="#991b1b",
            text_color=TEXT_WHITE,
            corner_radius=10,
            height=48,
            command=self._stop_recording_early,
        )
        self.btn_stop_rec.pack(fill="x", pady=(2, 10))

        # Launch Audio & Video Recording in Background Threads
        audio_path, video_path = generate_recording_paths()
        self.audio_path = audio_path
        self.video_path = video_path

        def _rec_thread():
            start_event = threading.Event()
            audio_ready = threading.Event()
            video_ready = threading.Event()
            recording_status = {}
            timing = {}

            audio_th = threading.Thread(
                target=audio.record_audio,
                args=(dur, start_event, audio_ready, recording_status, audio_path, self.stop_recording_event),
            )
            video_th = threading.Thread(
                target=video_capture.record_video,
                args=(
                    dur,
                    start_event,
                    video_ready,
                    recording_status,
                    timing,
                    video_path,
                    None,
                    True,  # Opens in separate high-performance OpenCV window as requested!
                    self.stop_recording_event,
                ),
            )

            audio_th.start()
            video_th.start()

            # Wait for ready signals with safety timeouts
            audio_ready.wait(timeout=5.0)
            video_ready.wait(timeout=5.0)

            timing["start_time"] = time.perf_counter()
            timing["deadline"] = timing["start_time"] + dur
            start_event.set()

            # Countdown UI loop
            deadline = timing["deadline"]
            while not self.stop_recording_event.is_set():
                rem = deadline - time.perf_counter()
                if rem <= 0:
                    break
                self.safe_after(0, lambda r=rem, d=dur: self._draw_timer_ring(r, d))
                time.sleep(0.08)

            # Signal stop to background threads
            self.stop_recording_event.set()
            video_th.join(timeout=3.0)
            audio_th.join(timeout=3.0)

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

            # 1. Background Ring
            self.ring_canvas.create_arc(
                x0, y0, x1, y1,
                start=0, extent=359.9,
                style="arc",
                outline="#162234",
                width=8,
            )

            # 2. Glowing Blue Active Progress Arc
            extent_angle = -(359.9 * prog)
            if abs(extent_angle) > 0.5:
                self.ring_canvas.create_arc(
                    x0, y0, x1, y1,
                    start=90, extent=extent_angle,
                    style="arc",
                    outline="#38bdf8",
                    width=8,
                )

            # 3. Center Digital Countdown Text
            self.ring_canvas.create_text(
                cx, cy,
                text=f"{mins:02d}:{secs:02d}",
                fill="#ffffff",
                font=("Segoe UI", 30, "bold"),
            )
        except Exception:
            pass

    def _stop_recording_early(self):
        """Signal recording threads to stop immediately and advance to results."""
        if hasattr(self, "stop_recording_event"):
            self.stop_recording_event.set()
        if hasattr(self, "btn_stop_rec") and self.btn_stop_rec.winfo_exists():
            self.btn_stop_rec.configure(text="⏳ Stopping...", state="disabled")

    # ============================================================
    # STEP 4: RESULTS & EVALUATION REPORT
    # ============================================================

    def _advance_to_step4_results(self):
        self.update_stepper(4)

        for w in self.practice_container.winfo_children():
            w.destroy()

        loading_box = ctk.CTkFrame(self.practice_container, fg_color="transparent")
        loading_box.pack(pady=100)

        l_title = ctk.CTkLabel(
            loading_box,
            text="⚙️ Analyzing Speech, Video & Audio...",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=ACCENT_CYAN,
        )
        l_title.pack(pady=(0, 10))

        l_sub = ctk.CTkLabel(
            loading_box,
            text="Transcribing audio with CrisperWhisper, measuring eye contact, and diagnosing 'What Went Wrong'...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_MUTED,
        )
        l_sub.pack()

        def _analysis_job():
            # 1. Video Analysis
            video_report = None
            try:
                video_report = analyze_video(self.video_path)
            except Exception as e:
                print(f"[Video Analysis] {e}")

            # 2. Transcription
            transcription = transcribe_audio(self.audio_path) or ""
            words = transcription.split()
            total_words = len(words)

            # 3. Fillers & Pauses
            fillers = detect_fillers(transcription)
            total_fillers = sum(fillers.values())
            pauses = detect_pauses(self.audio_path)

            # 4. Relevance
            relevance_res = None
            try:
                relevance_res = analyze_relevance(self.current_topic_data["title"], transcription)
            except Exception:
                pass

            dur = self.selected_duration["seconds"]

            # 5. Full Report
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
            )

            # 6. Save in MySQL dynamically in real-time
            if self.current_user:
                try:
                    save_speech_session(
                        user_id=self.current_user["user_id"],
                        category=self.selected_category["name"],
                        topic_name=self.current_topic_data["title"],
                        speaking_time=dur,
                        audio_path=self.audio_path,
                        video_path=self.video_path,
                        transcription=transcription,
                        report=report_data,
                    )
                except Exception as e:
                    print(f"[Save Error] {e}")
            else:
                self.last_unsaved_session = {
                    "category": self.selected_category["name"],
                    "topic_name": self.current_topic_data["title"],
                    "speaking_time": dur,
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

    # ============================================================
    # ============================================================
    # SPEECH REPORT PAGE (MODERN HIGH-FIDELITY DASHBOARD)
    # ============================================================

    def _render_speech_report(self, container, rep=None, transcription=None, session_date=None, back_callback=None, video_path=None, audio_path=None):
        """Render a modern, high-fidelity Speech Report dashboard using actual recorded metrics."""
        for w in container.winfo_children():
            w.destroy()

        # Stop any active audio playback when navigating to or re-rendering a report
        self._stop_report_audio()

        # Check if we have session data
        if rep is None:
            rep = getattr(self, "latest_report_data", None)

        # If still no session has been practiced yet, render an inviting Empty State
        if rep is None:
            empty_box = ctk.CTkFrame(container, fg_color="transparent")
            empty_box.pack(expand=True, fill="both", padx=40, pady=60)

            icon_lbl = ctk.CTkLabel(empty_box, text="🎙️", font=ctk.CTkFont(size=64))
            icon_lbl.pack(pady=(40, 16))

            empty_title = ctk.CTkLabel(
                empty_box,
                text="No Speech Sessions Yet",
                font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                text_color=TEXT_WHITE,
            )
            empty_title.pack(pady=(0, 8))

            empty_sub = ctk.CTkLabel(
                empty_box,
                text="Start an extempore practice session to analyze your speech pacing, filler words, eye contact, and get instant AI diagnostics.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=TEXT_MUTED,
                wraplength=460,
                justify="center",
            )
            empty_sub.pack(pady=(0, 24))

            btn_start = ctk.CTkButton(
                empty_box,
                text="Start Practice Session  ➔",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color=ACCENT_BLUE,
                hover_color="#2563eb",
                height=46,
                corner_radius=10,
                command=self.start_new_practice_session,
            )
            btn_start.pack()
            return

        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        scroll.grid_columnconfigure(0, weight=6, uniform="report_col")  # Left Column (~60%)
        scroll.grid_columnconfigure(1, weight=4, uniform="report_col")  # Right Column (~40%)

        # Extract real data with safe defaults
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

        eye_pct = rep.get("eye_contact_pct", 0.0)
        head_pct = rep.get("head_centering_pct", 0.0)
        overall_val = float(rep.get("overall", 0.0))
        is_silent = rep.get("is_silent", total_words == 0)

        # Media paths
        actual_video_path = video_path if video_path is not None else getattr(self, "video_path", None)
        actual_audio_path = audio_path if audio_path is not None else getattr(self, "audio_path", None)

        if not session_date:
            session_date = getattr(self, "latest_session_date", time.strftime("%d %b %Y, %I:%M %p"))

        final_transcript = transcription if transcription is not None else rep.get("transcription", "")
        if final_transcript is None:
            final_transcript = ""

        # --------------------------------------------------------
        # 1. TOP HEADER & ACTIONS
        # --------------------------------------------------------
        top_header = ctk.CTkFrame(scroll, fg_color="transparent")
        top_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        h_left = ctk.CTkFrame(top_header, fg_color="transparent")
        h_left.pack(side="left")

        back_cmd = back_callback if back_callback else self._end_session
        is_from_history = (back_callback is not None and back_callback != self._end_session)
        back_btn_text = "←  Back to History" if is_from_history else "←  Back to Home"

        btn_back_hist = ctk.CTkButton(
            h_left,
            text=back_btn_text,
            font=ctk.CTkFont(family="Segoe UI", size=13),
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
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=TEXT_WHITE,
        )
        rep_title.pack(side="left", padx=(0, 12))

        badge_txt = "⚠️ No Speech Detected" if is_silent else ("🌟 Outstanding" if overall_val >= 8.0 else ("🎯 Solid Effort" if overall_val >= 5.5 else "📈 Practice Needed"))
        badge_fg = "#2d161a" if is_silent else ("#052e24" if overall_val >= 8.0 else ("#182a4a" if overall_val >= 5.5 else "#2e2412"))
        badge_tc = "#f87171" if is_silent else (ACCENT_EMERALD if overall_val >= 8.0 else ("#93c5fd" if overall_val >= 5.5 else ACCENT_ORANGE))

        stat_badge = ctk.CTkLabel(
            title_row,
            text=f"  {badge_txt}  ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=badge_fg,
            text_color=badge_tc,
            corner_radius=8,
            height=24,
        )
        stat_badge.pack(side="left")

        rep_sub = ctk.CTkLabel(
            h_left,
            text=f"Comprehensive AI speech delivery & visual presence diagnostics for \"{topic_title}\".",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED,
        )
        rep_sub.pack(anchor="w")

        # Header Right Actions
        h_right = ctk.CTkFrame(top_header, fg_color="transparent")
        h_right.pack(side="right")

        date_box = ctk.CTkFrame(h_right, fg_color="transparent")
        date_box.pack(side="left", padx=(0, 16))

        d_cap = ctk.CTkLabel(
            date_box,
            text="Session Date",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_SUBTLE,
        )
        d_cap.pack(anchor="e")

        d_val = ctk.CTkLabel(
            date_box,
            text=f"📅 {session_date}",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=TEXT_WHITE,
        )
        d_val.pack(anchor="e")

        btn_pdf = ctk.CTkButton(
            h_right,
            text="📥  Export Summary",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#101726",
            hover_color=CARD_HOVER,
            border_width=1,
            border_color="#22334c",
            text_color=TEXT_WHITE,
            corner_radius=8,
            height=36,
            command=lambda: messagebox.showinfo(
                "Export Summary",
                f"Speech Report for '{topic_title}' exported successfully!\n\n"
                f"• Overall Score: {overall_val:.1f}/10\n"
                f"• Words Spoken: {total_words}\n"
                f"• Speaking Pace: {pace_wpm} WPM\n"
                f"• Fillers Detected: {total_fillers}"
            ),
        )
        btn_pdf.pack(side="left", padx=(0, 8))

        btn_again_top = ctk.CTkButton(
            h_right,
            text="🔄  Practice Again",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
            text_color=TEXT_WHITE,
            corner_radius=8,
            height=36,
            command=self.start_new_practice_session,
        )
        btn_again_top.pack(side="left")

        # --------------------------------------------------------
        # 2. TOP 4 METRIC OVERVIEW CARDS ROW
        # --------------------------------------------------------
        metrics_row = ctk.CTkFrame(scroll, fg_color="transparent")
        metrics_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        for i in range(4):
            metrics_row.grid_columnconfigure(i, weight=1, uniform="m_card")

        # Card 1: Topic & Category
        c1 = ctk.CTkFrame(metrics_row, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        c1.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        c1_in = ctk.CTkFrame(c1, fg_color="transparent")
        c1_in.pack(fill="both", expand=True, padx=14, pady=12)

        icon1 = ctk.CTkLabel(c1_in, text="📄", font=ctk.CTkFont(size=18), width=34, height=34, corner_radius=10, fg_color="#1e2c44")
        icon1.pack(side="left", padx=(0, 10))

        c1_text = ctk.CTkFrame(c1_in, fg_color="transparent")
        c1_text.pack(side="left", fill="x", expand=True)

        ct1 = ctk.CTkLabel(c1_text, text="Speech Topic", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SUBTLE)
        ct1.pack(anchor="w")
        cv1 = ctk.CTkLabel(c1_text, text=topic_title, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_WHITE, justify="left", wraplength=170)
        cv1.pack(anchor="w", pady=(0, 3))
        tag1 = ctk.CTkLabel(c1_text, text=f" 🟣 {category_name} ", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#27193b", text_color="#c084fc", corner_radius=6)
        tag1.pack(anchor="w")

        # Card 2: Speaking Time & Progress
        c2 = ctk.CTkFrame(metrics_row, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        c2.grid(row=0, column=1, padx=4, sticky="nsew")
        c2_in = ctk.CTkFrame(c2, fg_color="transparent")
        c2_in.pack(fill="both", expand=True, padx=14, pady=12)

        icon2 = ctk.CTkLabel(c2_in, text="⏱️", font=ctk.CTkFont(size=18), width=34, height=34, corner_radius=10, fg_color="#2d2212")
        icon2.pack(side="left", padx=(0, 10))

        c2_text = ctk.CTkFrame(c2_in, fg_color="transparent")
        c2_text.pack(side="left", fill="x", expand=True)

        ct2 = ctk.CTkLabel(c2_text, text="Speaking Duration", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SUBTLE)
        ct2.pack(anchor="w")
        time_m = spk_time_sec // 60
        time_s = spk_time_sec % 60
        cv2 = ctk.CTkLabel(c2_text, text=f"{time_m}:{time_s:02d}", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=TEXT_WHITE)
        cv2.pack(anchor="w", pady=(0, 2))
        tgt_m = target_time_sec // 60
        tgt_s = target_time_sec % 60
        cs2 = ctk.CTkLabel(c2_text, text=f"Target: {tgt_m}:{tgt_s:02d} | Words: {total_words}", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE)
        cs2.pack(anchor="w")

        # Card 3: Visual & Audio Status
        c3 = ctk.CTkFrame(metrics_row, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        c3.grid(row=0, column=2, padx=4, sticky="nsew")
        c3_in = ctk.CTkFrame(c3, fg_color="transparent")
        c3_in.pack(fill="both", expand=True, padx=14, pady=12)

        icon3 = ctk.CTkLabel(c3_in, text="👁️", font=ctk.CTkFont(size=18), width=34, height=34, corner_radius=10, fg_color="#26173b")
        icon3.pack(side="left", padx=(0, 10))

        c3_text = ctk.CTkFrame(c3_in, fg_color="transparent")
        c3_text.pack(side="left", fill="x", expand=True)

        ct3 = ctk.CTkLabel(c3_text, text="Eye Contact & Presence", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SUBTLE)
        ct3.pack(anchor="w")
        cv3 = ctk.CTkLabel(c3_text, text=f"{eye_pct:.0f}% Contact", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=TEXT_WHITE)
        cv3.pack(anchor="w", pady=(0, 2))
        cs3 = ctk.CTkLabel(c3_text, text=f"Head Steady: {head_pct:.0f}%", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE)
        cs3.pack(anchor="w")

        # Card 4: Overall Rating Score Dial
        c4 = ctk.CTkFrame(metrics_row, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        c4.grid(row=0, column=3, padx=(8, 0), sticky="nsew")
        c4_in = ctk.CTkFrame(c4, fg_color="transparent")
        c4_in.pack(fill="both", expand=True, padx=14, pady=12)

        icon4 = ctk.CTkLabel(c4_in, text="🏆", font=ctk.CTkFont(size=18), width=34, height=34, corner_radius=10, fg_color="#2e2412")
        icon4.pack(side="left", padx=(0, 10))

        c4_text = ctk.CTkFrame(c4_in, fg_color="transparent")
        c4_text.pack(side="left", fill="x", expand=True)

        ct4 = ctk.CTkLabel(c4_text, text="Overall Score", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SUBTLE)
        ct4.pack(anchor="w")

        score_box = ctk.CTkFrame(c4_text, fg_color="transparent")
        score_box.pack(anchor="w", pady=(0, 2))

        cv4_big = ctk.CTkLabel(score_box, text=f"{overall_val:.1f}", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=TEXT_WHITE)
        cv4_big.pack(side="left")
        cv4_sub = ctk.CTkLabel(score_box, text=" / 10", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=TEXT_MUTED)
        cv4_sub.pack(side="left", padx=(2, 0))

        rating_color = "#f87171" if is_silent else (ACCENT_EMERALD if overall_val >= 7.0 else (ACCENT_ORANGE if overall_val >= 5.0 else "#f87171"))
        rating_msg = "No speech detected" if is_silent else ("Great performance!" if overall_val >= 7.0 else ("Room to improve" if overall_val >= 5.0 else "Needs practice"))
        cs4 = ctk.CTkLabel(c4_text, text=rating_msg, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=rating_color)
        cs4.pack(anchor="w")

        # --------------------------------------------------------
        # 3. LEFT COLUMN: Analytics Gauges, Transcript & Audio Player
        # --------------------------------------------------------
        left_col = ctk.CTkFrame(scroll, fg_color="transparent")
        left_col.grid(row=2, column=0, sticky="nsew", padx=(0, 12))

        # 3 Mini-Gauges Row (Pace WPM, Filler Breakdown, Speaking Time)
        row_3 = ctk.CTkFrame(left_col, fg_color="transparent")
        row_3.pack(fill="x", pady=(0, 14))
        for c_idx in range(3):
            row_3.grid_columnconfigure(c_idx, weight=1, uniform="sub3")

        # Mini-Gauge 1: Speaking Pace Speedometer
        mc1 = ctk.CTkFrame(row_3, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        mc1.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        mc1_in = ctk.CTkFrame(mc1, fg_color="transparent")
        mc1_in.pack(fill="both", expand=True, padx=12, pady=12)

        mc1_h = ctk.CTkLabel(mc1_in, text="🗣️  Speaking Pace", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_WHITE)
        mc1_h.pack(anchor="w", pady=(0, 4))

        pace_cv = tk.Canvas(mc1_in, width=140, height=72, bg="#101622", highlightthickness=0)
        pace_cv.pack(pady=(2, 6))
        self._draw_pace_gauge(pace_cv, pace_wpm if not is_silent else 0)

        if is_silent:
            pace_badge_text = " 0 WPM (Silent) "
            pace_badge_bg = "#2b1417"
            pace_badge_tc = "#f87171"
        elif 120 <= pace_wpm <= 160:
            pace_badge_text = " Ideal (120–160 wpm) "
            pace_badge_bg = "#052e24"
            pace_badge_tc = ACCENT_EMERALD
        elif pace_wpm < 120:
            pace_badge_text = f" Slow ({pace_wpm} wpm) "
            pace_badge_bg = "#2e2412"
            pace_badge_tc = ACCENT_ORANGE
        else:
            pace_badge_text = f" Fast ({pace_wpm} wpm) "
            pace_badge_bg = "#2e2412"
            pace_badge_tc = ACCENT_ORANGE

        mc1_badge = ctk.CTkLabel(mc1_in, text=pace_badge_text, font=ctk.CTkFont(size=10, weight="bold"), fg_color=pace_badge_bg, text_color=pace_badge_tc, corner_radius=6)
        mc1_badge.pack()

        # Mini-Gauge 2: Filler Words Donut
        mc2 = ctk.CTkFrame(row_3, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        mc2.grid(row=0, column=1, padx=4, sticky="nsew")
        mc2_in = ctk.CTkFrame(mc2, fg_color="transparent")
        mc2_in.pack(fill="both", expand=True, padx=12, pady=12)

        mc2_h = ctk.CTkLabel(mc2_in, text="💬  Filler Words", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_WHITE)
        mc2_h.pack(anchor="w", pady=(0, 4))

        donut_row = ctk.CTkFrame(mc2_in, fg_color="transparent")
        donut_row.pack(fill="x", pady=(2, 4))

        donut_cv = tk.Canvas(donut_row, width=64, height=64, bg="#101622", highlightthickness=0)
        donut_cv.pack(side="left", padx=(0, 6))
        self._draw_donut(donut_cv, total_fillers)

        f_list_box = ctk.CTkFrame(donut_row, fg_color="transparent")
        f_list_box.pack(side="left", fill="x", expand=True)

        if filler_breakdown:
            for f_word, f_num in list(filler_breakdown.items())[:3]:
                fl = ctk.CTkLabel(f_list_box, text=f"• {f_word} ({f_num})", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_MUTED)
                fl.pack(anchor="w")
        else:
            fl_none = ctk.CTkLabel(f_list_box, text="No fillers detected", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE)
            fl_none.pack(anchor="w")

        f_badge_txt = " 0% fillers (Clean) " if total_fillers == 0 else f" {total_fillers} fillers ({filler_pct:.1f}%) "
        f_badge_bg = "#052e24" if total_fillers <= 2 else "#2b1417"
        f_badge_tc = ACCENT_EMERALD if total_fillers <= 2 else "#f87171"
        mc2_badge = ctk.CTkLabel(mc2_in, text=f_badge_txt, font=ctk.CTkFont(size=9, weight="bold"), fg_color=f_badge_bg, text_color=f_badge_tc, corner_radius=6)
        mc2_badge.pack()

        # Mini-Gauge 3: Pause & Rhythm Ring
        mc3 = ctk.CTkFrame(row_3, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
        mc3.grid(row=0, column=2, padx=(6, 0), sticky="nsew")
        mc3_in = ctk.CTkFrame(mc3, fg_color="transparent")
        mc3_in.pack(fill="both", expand=True, padx=12, pady=12)

        mc3_h = ctk.CTkLabel(mc3_in, text="⏸️  Pauses & Rhythm", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_WHITE)
        mc3_h.pack(anchor="w", pady=(0, 4))

        ring_time_cv = tk.Canvas(mc3_in, width=64, height=64, bg="#101622", highlightthickness=0)
        ring_time_cv.pack(pady=(2, 6))
        self._draw_time_ring_mini(ring_time_cv, spk_time_sec, target_time_sec)

        num_p = len(pauses_list)
        p_badge_txt = " Natural flow " if (num_p <= 3 and total_words > 10) else f" {num_p} pauses (>=0.5s) "
        mc3_badge = ctk.CTkLabel(mc3_in, text=p_badge_txt, font=ctk.CTkFont(size=10, weight="bold"), fg_color="#182a4a", text_color="#93c5fd", corner_radius=6)
        mc3_badge.pack()

        # Transcript & Word Analysis Card
        tr_card = ctk.CTkFrame(left_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        tr_card.pack(fill="x", pady=(0, 14))

        tr_in = ctk.CTkFrame(tr_card, fg_color="transparent")
        tr_in.pack(fill="both", expand=True, padx=18, pady=16)

        tr_top = ctk.CTkFrame(tr_in, fg_color="transparent")
        tr_top.pack(fill="x", pady=(0, 8))

        tr_title = ctk.CTkLabel(
            tr_top,
            text="🎙️  Speech Transcript & Audio Review",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=TEXT_WHITE,
        )
        tr_title.pack(side="left")

        w_count_tag = ctk.CTkLabel(
            tr_top,
            text=f" {total_words} words ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#1e2c44",
            text_color=ACCENT_CYAN,
            corner_radius=6,
        )
        w_count_tag.pack(side="right")

        # Audio Player Bar
        audio_bar = ctk.CTkFrame(tr_in, fg_color="#0c121d", corner_radius=10, border_width=1, border_color="#1b273b")
        audio_bar.pack(fill="x", pady=(0, 12))

        ab_inner = ctk.CTkFrame(audio_bar, fg_color="transparent")
        ab_inner.pack(fill="x", padx=12, pady=8)

        self.btn_audio_play = ctk.CTkButton(
            ab_inner,
            text="▶  Play Recording",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
            height=30,
            width=120,
            corner_radius=6,
            command=lambda: self._toggle_report_audio(actual_audio_path),
        )
        self.btn_audio_play.pack(side="left", padx=(0, 12))

        self.report_waveform_cv = tk.Canvas(ab_inner, width=280, height=28, bg="#0c121d", highlightthickness=0)
        self.report_waveform_cv.pack(side="left", fill="x", expand=True)
        self._draw_waveform(self.report_waveform_cv, 0.0)

        self.audio_status_lbl = ctk.CTkLabel(
            ab_inner,
            text=f"{spk_time_sec}s",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED,
            width=40,
        )
        self.audio_status_lbl.pack(side="right", padx=(8, 0))

        # Transcript text display
        if is_silent:
            no_speech_box = ctk.CTkFrame(tr_in, fg_color="#1d1417", corner_radius=8, border_width=1, border_color="#451a22")
            no_speech_box.pack(fill="x", pady=(0, 4))
            ns_lbl = ctk.CTkLabel(
                no_speech_box,
                text="⚠️ No audible speech was captured in this recording.\n"
                     "Make sure your microphone is active and positioned near you for the next practice session.",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#fca5a5",
                justify="left",
                padx=14,
                pady=12,
            )
            ns_lbl.pack(anchor="w")
        else:
            txt_box = ctk.CTkTextbox(
                tr_in,
                height=110,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                fg_color="#0b1019",
                border_width=1,
                border_color="#1b2536",
                text_color="#e2e8f0",
                wrap="word",
                corner_radius=8,
            )
            txt_box.pack(fill="x", pady=(0, 4))
            txt_box.insert("1.0", final_transcript)
            txt_box.configure(state="disabled")

        # --------------------------------------------------------
        # 4. RIGHT COLUMN: Detailed Scores, Flaws & Next Steps
        # --------------------------------------------------------
        right_col = ctk.CTkFrame(scroll, fg_color="transparent")
        right_col.grid(row=2, column=1, sticky="nsew", padx=(12, 0))

        # Detailed Scores Card
        det_card = ctk.CTkFrame(right_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        det_card.pack(fill="x", pady=(0, 14))

        d_inner = ctk.CTkFrame(det_card, fg_color="transparent")
        d_inner.pack(fill="both", expand=True, padx=18, pady=16)

        d_head = ctk.CTkLabel(d_inner, text="🏆  Detailed Score Breakdown", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_WHITE)
        d_head.pack(anchor="w", pady=(0, 10))

        score_rows = [
            ("〰️", "Fluency", rep.get("fluency", 0.0), "#10b981", "Filler word management and flow."),
            ("📄", "Topic Relevance", rep.get("relevance", 0.0), "#3b82f6", "Alignment with assigned topic."),
            ("⏱️", "Speech Pace", rep.get("pace", 0.0), "#f59e0b", f"Delivery speed ({pace_wpm} WPM)."),
            ("⏸️", "Pause Mgmt", rep.get("pauses", 0.0), "#06b6d4", "Hesitation and pause balance."),
            ("👁️", "Eye Contact", rep.get("eye_contact", 0.0), "#a855f7", f"Camera gaze ({eye_pct:.0f}% contact)."),
            ("👤", "Head Stability", rep.get("head_stability", 0.0), "#14b8a6", f"Head posture ({head_pct:.0f}% centered)."),
        ]

        for icon, name, val, bar_color, desc in score_rows:
            if val is None:
                val = 0.0
            val_f = float(val)

            s_row = ctk.CTkFrame(d_inner, fg_color="transparent")
            s_row.pack(fill="x", pady=3)

            top_line = ctk.CTkFrame(s_row, fg_color="transparent")
            top_line.pack(fill="x")

            nl = ctk.CTkLabel(top_line, text=f"{icon}  {name}", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_WHITE, width=120, anchor="w")
            nl.pack(side="left")

            pbar = ctk.CTkProgressBar(top_line, width=110, height=7, corner_radius=4, progress_color=bar_color, fg_color="#182334")
            pbar.pack(side="left", padx=8)
            pbar.set(max(0.0, min(1.0, val_f / 10.0)))

            vl = ctk.CTkLabel(top_line, text=f"{val_f:.1f}/10", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_WHITE)
            vl.pack(side="right")

            dl = ctk.CTkLabel(s_row, text=desc, font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE, justify="left", wraplength=320, anchor="w")
            dl.pack(anchor="w", padx=(22, 0), pady=(1, 0))

        # Diagnostic Flaws / What Went Wrong Card
        flaws_card = ctk.CTkFrame(right_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        flaws_card.pack(fill="x", pady=(0, 14))

        fl_inner = ctk.CTkFrame(flaws_card, fg_color="transparent")
        fl_inner.pack(fill="both", expand=True, padx=18, pady=16)

        fl_head = ctk.CTkLabel(fl_inner, text="🔍  Diagnostic Analysis (What Went Wrong)", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#f87171")
        fl_head.pack(anchor="w", pady=(0, 8))

        flaws = rep.get("what_went_wrong", [])
        if not flaws:
            flaws = ["No major delivery mistakes detected!"]

        for item in flaws[:4]:
            fl_row = ctk.CTkFrame(fl_inner, fg_color="transparent")
            fl_row.pack(fill="x", pady=3)

            is_ok = item.startswith("No major")
            icon_char = "✓" if is_ok else "!"
            icon_bg = "#052e24" if is_ok else "#3b171c"
            icon_tc = ACCENT_EMERALD if is_ok else "#f87171"

            chk = ctk.CTkLabel(fl_row, text=icon_char, font=ctk.CTkFont(size=10, weight="bold"), fg_color=icon_bg, text_color=icon_tc, width=18, height=18, corner_radius=9)
            chk.pack(side="left", padx=(0, 8), anchor="n")

            fl_txt = ctk.CTkLabel(fl_row, text=item, font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#cbd5e1", justify="left", wraplength=310, anchor="w")
            fl_txt.pack(side="left", fill="x", expand=True)

        # Strengths & Actionable Advice Card
        adv_card = ctk.CTkFrame(right_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        adv_card.pack(fill="x", pady=(0, 14))

        adv_inner = ctk.CTkFrame(adv_card, fg_color="transparent")
        adv_inner.pack(fill="both", expand=True, padx=18, pady=16)

        adv_head = ctk.CTkLabel(adv_inner, text="💡  Actionable Advice for Next Take", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#f59e0b")
        adv_head.pack(anchor="w", pady=(0, 8))

        improvements = rep.get("improvements", [])
        if not improvements:
            improvements = ["Keep up the steady pace and natural eye contact!"]

        for item in improvements[:4]:
            adv_row = ctk.CTkFrame(adv_inner, fg_color="transparent")
            adv_row.pack(fill="x", pady=3)

            chk2 = ctk.CTkLabel(adv_row, text="➔", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#182a4a", text_color="#93c5fd", width=18, height=18, corner_radius=9)
            chk2.pack(side="left", padx=(0, 8), anchor="n")

            adv_txt = ctk.CTkLabel(adv_row, text=item, font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#cbd5e1", justify="left", wraplength=310, anchor="w")
            adv_txt.pack(side="left", fill="x", expand=True)

        # Action Buttons Row
        act_row = ctk.CTkFrame(right_col, fg_color="transparent")
        act_row.pack(fill="x", pady=(4, 16))
        act_row.grid_columnconfigure(0, weight=6)
        act_row.grid_columnconfigure(1, weight=4)

        btn_again = ctk.CTkButton(
            act_row,
            text="Practice Again  ➔",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
            height=48,
            corner_radius=10,
            command=self.start_new_practice_session,
        )
        btn_again.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        btn_end_sess = ctk.CTkButton(
            act_row,
            text="⏹️  End Session",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#2b1417",
            hover_color="#3d1b20",
            border_width=1,
            border_color="#7f1d1d",
            text_color="#fca5a5",
            height=48,
            corner_radius=10,
            command=self._end_session,
        )
        btn_end_sess.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    # ------------------------------------------------------------
    # REPORT AUDIO PLAYER & CANVAS DIAGRAM HELPERS
    # ------------------------------------------------------------

    def _stop_report_audio(self):
        """Safely stop any ongoing report audio playback."""
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

        if hasattr(self, "btn_audio_play") and self.btn_audio_play.winfo_exists():
            try:
                self.btn_audio_play.configure(text="▶  Play Recording", fg_color=ACCENT_BLUE)
            except Exception:
                pass

        if hasattr(self, "report_waveform_cv") and self.report_waveform_cv.winfo_exists():
            try:
                self._draw_waveform(self.report_waveform_cv, 0.0)
            except Exception:
                pass

    def _toggle_report_audio(self, audio_path):
        """Toggle playback of recorded session audio."""
        if getattr(self, "_audio_is_playing", False):
            self._stop_report_audio()
            return

        if not audio_path or not os.path.exists(audio_path):
            messagebox.showwarning("Audio Notice", "No audio recording file found for this session.")
            return

        try:
            self._audio_is_playing = True
            if hasattr(self, "btn_audio_play") and self.btn_audio_play.winfo_exists():
                self.btn_audio_play.configure(text="⏹  Stop Audio", fg_color="#dc2626")

            # Play asynchronously
            winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)

            # Animate waveform progress
            start_time = time.perf_counter()
            approx_duration = max(5.0, getattr(self, "latest_report_data", {}).get("duration", 30))

            def _update_progress():
                if not getattr(self, "_audio_is_playing", False):
                    return
                elapsed = time.perf_counter() - start_time
                ratio = min(1.0, elapsed / approx_duration)
                if hasattr(self, "report_waveform_cv") and self.report_waveform_cv.winfo_exists():
                    self._draw_waveform(self.report_waveform_cv, ratio)
                if hasattr(self, "audio_status_lbl") and self.audio_status_lbl.winfo_exists():
                    self.audio_status_lbl.configure(text=f"{int(elapsed)}s")

                if ratio < 1.0:
                    self._audio_play_timer = self.after(100, _update_progress)
                else:
                    self._stop_report_audio()

            self._audio_play_timer = self.after(100, _update_progress)

        except Exception as e:
            print(f"[Audio Playback Error] {e}")
            self._stop_report_audio()

    def _draw_waveform(self, canvas, progress_ratio=0.0):
        """Draw realistic audio waveform visualization bars with playing progress highlight."""
        try:
            canvas.delete("all")
            bars = [8, 12, 16, 22, 14, 18, 26, 20, 15, 24, 28, 18, 14, 22, 25, 20, 16, 24, 19, 12, 16, 22, 27, 21, 15, 18, 24, 20, 14, 10, 16, 22, 18, 12, 8]
            x_start = 8
            spacing = 8
            total_bars = len(bars)
            played_bars = int(total_bars * max(0.0, min(1.0, progress_ratio)))
            for idx, h in enumerate(bars):
                x = x_start + idx * spacing
                y0 = 14 - (h / 2)
                y1 = 14 + (h / 2)
                if progress_ratio > 0:
                    color = "#38bdf8" if idx <= played_bars else "#334155"
                else:
                    color = "#38bdf8" if idx < len(bars) // 2 else "#818cf8"
                canvas.create_line(x, y0, x, y1, fill=color, width=3, capstyle="round")
        except Exception:
            pass

    def _draw_pace_gauge(self, canvas, wpm):
        """Draw semi-circle speedometer gauge for speaking pace."""
        try:
            canvas.delete("all")
            cx, cy, r = 70, 68, 50
            x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r

            # Background arc
            canvas.create_arc(x0, y0, x1, y1, start=180, extent=-180, style="arc", outline="#1c2738", width=7)

            # Active pace arc
            prog = max(0.0, min(1.0, wpm / 200.0))
            active_color = "#38bdf8" if (120 <= wpm <= 160) else ("#f59e0b" if wpm > 0 else "#64748b")
            canvas.create_arc(x0, y0, x1, y1, start=180, extent=-(180 * prog), style="arc", outline=active_color, width=7)

            # Center text
            canvas.create_text(cx, cy - 18, text=f"{int(wpm)}", fill="#ffffff", font=("Segoe UI", 18, "bold"))
            canvas.create_text(cx, cy - 2, text="words / min", fill="#64748b", font=("Segoe UI", 9))
        except Exception:
            pass

    def _draw_donut(self, canvas, total_fillers):
        """Draw donut chart for filler words count."""
        try:
            canvas.delete("all")
            cx, cy, r = 32, 32, 25
            x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r

            if total_fillers == 0:
                canvas.create_arc(x0, y0, x1, y1, start=0, extent=359.9, style="arc", outline="#10b981", width=5)
            else:
                canvas.create_arc(x0, y0, x1, y1, start=0, extent=160, style="arc", outline="#a855f7", width=5)
                canvas.create_arc(x0, y0, x1, y1, start=160, extent=100, style="arc", outline="#38bdf8", width=5)
                canvas.create_arc(x0, y0, x1, y1, start=260, extent=100, style="arc", outline="#f43f5e", width=5)

            canvas.create_text(cx, cy - 6, text=f"{total_fillers}", fill="#ffffff", font=("Segoe UI", 13, "bold"))
            canvas.create_text(cx, cy + 7, text="total", fill="#64748b", font=("Segoe UI", 8))
        except Exception:
            pass

    def _draw_time_ring_mini(self, canvas, spk_sec, target_sec):
        """Draw circular progress ring for speaking time."""
        try:
            canvas.delete("all")
            cx, cy, r = 32, 32, 25
            x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r

            canvas.create_arc(x0, y0, x1, y1, start=0, extent=359.9, style="arc", outline="#1c2738", width=5)

            prog = min(1.0, spk_sec / target_sec) if target_sec > 0 else 1.0
            canvas.create_arc(x0, y0, x1, y1, start=90, extent=-(359.9 * prog), style="arc", outline="#38bdf8", width=5)

            m = spk_sec // 60
            s = spk_sec % 60
            canvas.create_text(cx, cy - 6, text=f"{m}:{s:02d}", fill="#ffffff", font=("Segoe UI", 10, "bold"))
            tm = target_sec // 60
            ts = target_sec % 60
            canvas.create_text(cx, cy + 7, text=f"/ {tm}:{ts:02d}", fill="#64748b", font=("Segoe UI", 8))
        except Exception:
            pass


    # ============================================================
    # OTHER VIEWS (HOME, HISTORY, PROFILE, SETTINGS)
    # ============================================================

    def _create_home_view(self):
        """Construct Home page with welcome hero and direct options to Sign In, Sign Up, or Practice."""
        self.home_scroll = ctk.CTkScrollableFrame(self.pages_container, fg_color="transparent")
        self.home_scroll.grid_columnconfigure(0, weight=1)

        self.home_container = ctk.CTkFrame(self.home_scroll, fg_color="transparent")
        self.home_container.pack(fill="both", expand=True, padx=24, pady=24)

        self._render_home_content()
        return self.home_scroll

    def _render_home_content(self):
        """Render the home page contents based on whether user is logged in or guest."""
        if not hasattr(self, "home_container") or not self.home_container.winfo_exists():
            return

        for w in self.home_container.winfo_children():
            w.destroy()

        # 1. Top Welcome Badge Pill
        badge_row = ctk.CTkFrame(self.home_container, fg_color="transparent")
        badge_row.pack(anchor="w", pady=(0, 14))

        badge = ctk.CTkLabel(
            badge_row,
            text="  ✨ AI-POWERED SPEECH PLATFORM  ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=ACCENT_CYAN,
            fg_color="#182334",
            corner_radius=14,
            height=28,
        )
        badge.pack(side="left")

        # 2. Main Hero Heading
        hero = ctk.CTkLabel(
            self.home_container,
            text="Speak Better.\nThink Faster.\nCommunicate with Confidence.",
            font=ctk.CTkFont(family="Segoe UI", size=42, weight="bold"),
            text_color=TEXT_WHITE,
            justify="left",
            anchor="w",
        )
        hero.pack(anchor="w", pady=(0, 12))

        # 3. Subtitle Description
        sub = ctk.CTkLabel(
            self.home_container,
            text="Master extempore speaking with instant AI coaching, live video analysis, and deep multimodal feedback on body language, pacing, and clarity.",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=TEXT_MUTED,
            justify="left",
            wraplength=760,
            anchor="w",
        )
        sub.pack(anchor="w", pady=(0, 28))

        # 4. Action Cards Area (Sign In / Sign Up / Start Practice)
        action_card = ctk.CTkFrame(
            self.home_container,
            fg_color="#0e1624",
            corner_radius=18,
            border_width=1,
            border_color="#1e2c42",
        )
        action_card.pack(fill="x", pady=(0, 32))

        ac_inner = ctk.CTkFrame(action_card, fg_color="transparent")
        ac_inner.pack(fill="both", expand=True, padx=24, pady=24)

        if not self.current_user:
            # GUEST STATE: Present Sign In and Sign Up options
            g_head = ctk.CTkLabel(
                ac_inner,
                text="🚀  Get Started with Your Speaking Journey",
                font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                text_color=TEXT_WHITE,
            )
            g_head.pack(anchor="w", pady=(0, 6))

            g_desc = ctk.CTkLabel(
                ac_inner,
                text="Sign in to your account or create a new one to save your speech recordings, track metrics over time, and unlock full reports.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=TEXT_MUTED,
            )
            g_desc.pack(anchor="w", pady=(0, 20))

            btn_row = ctk.CTkFrame(ac_inner, fg_color="transparent")
            btn_row.pack(anchor="w")

            btn_signin = ctk.CTkButton(
                btn_row,
                text="🔑  Sign In to Account",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color=ACCENT_BLUE,
                hover_color="#2563eb",
                height=46,
                corner_radius=10,
                command=lambda: self.open_auth_modal("login"),
            )
            btn_signin.pack(side="left", padx=(0, 14))

            btn_signup = ctk.CTkButton(
                btn_row,
                text="✨  Create Free Account",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color=ACCENT_EMERALD,
                hover_color="#059669",
                height=46,
                corner_radius=10,
                command=lambda: self.open_auth_modal("register"),
            )
            btn_signup.pack(side="left", padx=(0, 14))

            btn_guest = ctk.CTkButton(
                btn_row,
                text="🎙️  Practice as Guest  ➔",
                font=ctk.CTkFont(family="Segoe UI", size=14),
                fg_color="#152030",
                hover_color="#1d2d44",
                border_width=1,
                border_color="#22334c",
                text_color=TEXT_WHITE,
                height=46,
                corner_radius=10,
                command=self.start_new_practice_session,
            )
            btn_guest.pack(side="left")

        else:
            # LOGGED IN STATE
            u_name = self.current_user.get("name", "User")
            u_email = self.current_user.get("email", "")

            user_row = ctk.CTkFrame(ac_inner, fg_color="transparent")
            user_row.pack(fill="x", pady=(0, 16))

            u_head = ctk.CTkLabel(
                user_row,
                text=f"👋  Welcome back, {u_name}!",
                font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                text_color=TEXT_WHITE,
            )
            u_head.pack(anchor="w", pady=(0, 4))

            u_sub = ctk.CTkLabel(
                user_row,
                text=f"Signed in as {u_email} • All your practice takes and speech analytics are automatically saved to your profile.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=TEXT_MUTED,
            )
            u_sub.pack(anchor="w")

            btn_row = ctk.CTkFrame(ac_inner, fg_color="transparent")
            btn_row.pack(anchor="w")

            btn_start = ctk.CTkButton(
                btn_row,
                text="🎙️  Start Speech Practice  ➔",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color=ACCENT_BLUE,
                hover_color="#2563eb",
                height=46,
                corner_radius=10,
                command=self.start_new_practice_session,
            )
            btn_start.pack(side="left", padx=(0, 14))

            btn_hist = ctk.CTkButton(
                btn_row,
                text="📜  View History",
                font=ctk.CTkFont(family="Segoe UI", size=14),
                fg_color="#152030",
                hover_color="#1d2d44",
                border_width=1,
                border_color="#22334c",
                text_color=TEXT_WHITE,
                height=46,
                corner_radius=10,
                command=lambda: self.show_page("history"),
            )
            btn_hist.pack(side="left", padx=(0, 14))

            btn_logout = ctk.CTkButton(
                btn_row,
                text="🚪  Sign Out",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="transparent",
                hover_color="#3d1417",
                border_width=1,
                border_color="#451a1e",
                text_color="#f87171",
                height=46,
                corner_radius=10,
                command=self._handle_logout,
            )
            btn_logout.pack(side="left")

        # 5. Feature Highlights Row (3 Cards)
        feat_label = ctk.CTkLabel(
            self.home_container,
            text="✨  Core Capabilities",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=TEXT_WHITE,
        )
        feat_label.pack(anchor="w", pady=(0, 14))

        feat_row = ctk.CTkFrame(self.home_container, fg_color="transparent")
        feat_row.pack(fill="x", pady=(0, 20))
        for col_idx in range(3):
            feat_row.grid_columnconfigure(col_idx, weight=1, uniform="home_feat")

        features = [
            ("🤖", "Interactive AI Coach", "Chat in real-time with Gemini Flash to brainstorm compelling points, structure your speech, and refine introductions."),
            ("🎥", "Computer Vision Tracking", "Monitor gaze stability, camera alignment, eye contact percentage, and confident body posture during live recording."),
            ("📊", "Multimodal Evaluation", "Analyze words-per-minute pacing, filler word count, full speech transcription, and playable synchronized audio."),
        ]

        for idx, (f_icon, f_title, f_desc) in enumerate(features):
            fc = ctk.CTkFrame(feat_row, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color=CARD_BORDER)
            fc.grid(row=0, column=idx, padx=(0 if idx == 0 else 8, 0 if idx == 2 else 8), sticky="nsew")

            fc_inner = ctk.CTkFrame(fc, fg_color="transparent")
            fc_inner.pack(fill="both", expand=True, padx=18, pady=18)

            ic = ctk.CTkLabel(fc_inner, text=f_icon, font=ctk.CTkFont(size=26))
            ic.pack(anchor="w", pady=(0, 10))

            t = ctk.CTkLabel(fc_inner, text=f_title, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=TEXT_WHITE)
            t.pack(anchor="w", pady=(0, 6))

            d = ctk.CTkLabel(fc_inner, text=f_desc, font=ctk.CTkFont(family="Segoe UI", size=12), text_color=TEXT_MUTED, justify="left", wraplength=260)
            d.pack(anchor="w")

    # ============================================================
    # HISTORY VIEW (100% DYNAMIC FROM DATABASE & EMPTY STATE)
    # ============================================================

    def _create_history_view(self):
        """Construct History page with dynamic MySQL sessions and empty state."""
        frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.history_main_scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.history_main_scroll.grid(row=0, column=0, sticky="nsew")
        self.history_main_scroll.grid_columnconfigure(0, weight=7, uniform="hist_col")  # Left sessions list (~70%)
        self.history_main_scroll.grid_columnconfigure(1, weight=3, uniform="hist_col")  # Right stats & filters (~30%)

        # State for filters & tabs
        self.history_active_tab = "All Sessions"
        self.history_selected_topic_filter = "All Topics"
        self.history_selected_perf_filter = "All Scores"
        self.history_sort_order = "Newest First"

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
                "technology": "#172338",
                "science": "#2b1828",
                "history": "#282012",
                "business": "#201736",
                "society": "#331628",
                "environment": "#122a22",
                "entertainment": "#331520",
                "mystery": "#152238",
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
                icon_bg = cat_bgs.get(cat_lower, "#172338")

                score = float(rep_dict.get("overall", 7.5)) if rep_dict.get("overall") is not None else 7.5
                fluency = float(rep_dict.get("fluency", score)) if rep_dict.get("fluency") is not None else score

                if score >= 8.0:
                    score_label = "Great job!"
                    score_color = ACCENT_EMERALD
                elif score >= 7.0:
                    score_label = "Good job!"
                    score_color = "#34d399"
                elif score >= 6.0:
                    score_label = "Keep going!"
                    score_color = "#f59e0b"
                else:
                    score_label = "Needs work"
                    score_color = "#f87171"

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

        except Exception as e:
            print(f"[History DB Load Notice] {e}")

        return sessions

    def _render_history_page(self):
        """Render top badges, sessions stream, quick stats, and filter sidebar with dynamic DB data."""
        for w in self.history_main_scroll.winfo_children():
            w.destroy()

        self.cached_history_sessions = self._load_user_history_from_db()
        total_count = len(self.cached_history_sessions)

        if total_count > 0:
            avg_score_val = sum(s["score"] for s in self.cached_history_sessions) / total_count
            avg_score_text = f"{avg_score_val:.1f}/10"
            avg_fluency_val = (sum(s["fluency"] for s in self.cached_history_sessions) / total_count) * 10
            avg_fluency_text = f"{avg_fluency_val:.0f}%"
            best_score_val = max(s["score"] for s in self.cached_history_sessions)
            best_score_text = f"{best_score_val:.1f}"
            total_sessions_text = str(total_count)
        else:
            avg_score_text = "--"
            avg_fluency_text = "--"
            best_score_text = "--"
            total_sessions_text = "0"

        # --------------------------------------------------------
        # 1. TOP HEADER & METRIC BADGES
        # --------------------------------------------------------
        h_frame = ctk.CTkFrame(self.history_main_scroll, fg_color="transparent")
        h_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))

        # Header Title & Subtitle
        h_left = ctk.CTkFrame(h_frame, fg_color="transparent")
        h_left.pack(side="left")

        h_icon_row = ctk.CTkFrame(h_left, fg_color="transparent")
        h_icon_row.pack(anchor="w")

        clk_icon = ctk.CTkLabel(
            h_icon_row,
            text="🕒",
            font=ctk.CTkFont(size=22),
            width=36,
            height=36,
            corner_radius=18,
            fg_color="#141d2e",
        )
        clk_icon.pack(side="left", padx=(0, 10))

        title_lbl = ctk.CTkLabel(
            h_icon_row,
            text="History",
            font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
            text_color=TEXT_WHITE,
        )
        title_lbl.pack(side="left")

        sub_lbl = ctk.CTkLabel(
            h_left,
            text="Your past practice sessions, performance and progress — all in one place.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_MUTED,
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Right Header Metric Badges (Total Sessions & Avg Score)
        h_right = ctk.CTkFrame(h_frame, fg_color="transparent")
        h_right.pack(side="right")

        # Total Sessions Badge
        badge_tot = ctk.CTkFrame(
            h_right,
            fg_color="#0c1524",
            corner_radius=12,
            border_width=1,
            border_color="#1b283d",
            width=140,
            height=58,
        )
        badge_tot.pack(side="left", padx=(0, 12))
        badge_tot.pack_propagate(False)

        b_tot_in = ctk.CTkFrame(badge_tot, fg_color="transparent")
        b_tot_in.pack(expand=True, padx=12)

        icon_cal = ctk.CTkLabel(b_tot_in, text="📅", font=ctk.CTkFont(size=16), text_color=ACCENT_CYAN)
        icon_cal.pack(side="left", padx=(0, 8))

        b_tot_txt = ctk.CTkFrame(b_tot_in, fg_color="transparent")
        b_tot_txt.pack(side="left")

        b_tot_cap = ctk.CTkLabel(b_tot_txt, text="Total Sessions", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE)
        b_tot_cap.pack(anchor="w")
        b_tot_val = ctk.CTkLabel(b_tot_txt, text=total_sessions_text, font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=TEXT_WHITE)
        b_tot_val.pack(anchor="w")

        # Avg Score Badge
        badge_avg = ctk.CTkFrame(
            h_right,
            fg_color="#181228",
            corner_radius=12,
            border_width=1,
            border_color="#6b21a8",
            width=140,
            height=58,
        )
        badge_avg.pack(side="left")
        badge_avg.pack_propagate(False)

        b_avg_in = ctk.CTkFrame(badge_avg, fg_color="transparent")
        b_avg_in.pack(expand=True, padx=12)

        icon_chart = ctk.CTkLabel(b_avg_in, text="📈", font=ctk.CTkFont(size=16))
        icon_chart.pack(side="left", padx=(0, 8))

        b_avg_txt = ctk.CTkFrame(b_avg_in, fg_color="transparent")
        b_avg_txt.pack(side="left")

        b_avg_cap = ctk.CTkLabel(b_avg_txt, text="Avg. Score", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE)
        b_avg_cap.pack(anchor="w")
        b_avg_val = ctk.CTkLabel(b_avg_txt, text=avg_score_text, font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color="#c084fc")
        b_avg_val.pack(anchor="w")

        # --------------------------------------------------------
        # 2. LEFT COLUMN: Tabs & Session Cards List (~70%)
        # --------------------------------------------------------
        left_sessions_col = ctk.CTkFrame(self.history_main_scroll, fg_color="transparent")
        left_sessions_col.grid(row=1, column=0, sticky="nsew", padx=(0, 16))

        # Tabs & Sort Row
        tabs_row = ctk.CTkFrame(left_sessions_col, fg_color="transparent")
        tabs_row.pack(fill="x", pady=(0, 14))

        # Tabs buttons
        tabs_box = ctk.CTkFrame(tabs_row, fg_color="transparent")
        tabs_box.pack(side="left")

        self.hist_tab_buttons = {}
        tab_names = ["All Sessions", "Speaking", "Topics", "Date"]
        for t_name in tab_names:
            is_act = (t_name == self.history_active_tab)
            t_btn = ctk.CTkButton(
                tabs_box,
                text=t_name,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold" if is_act else "normal"),
                fg_color="#182335" if is_act else "transparent",
                hover_color="#1e2c40",
                text_color=TEXT_WHITE if is_act else TEXT_MUTED,
                corner_radius=8,
                height=34,
                command=lambda tn=t_name: self._on_hist_tab_click(tn),
            )
            t_btn.pack(side="left", padx=(0, 6))
            self.hist_tab_buttons[t_name] = t_btn

        # Sort Dropdown
        sort_box = ctk.CTkFrame(tabs_row, fg_color="transparent")
        sort_box.pack(side="right")

        self.sort_menu = ctk.CTkOptionMenu(
            sort_box,
            values=["⇅ Newest First", "⇅ Oldest First", "⇅ Highest Score", "⇅ Lowest Score"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#101726",
            button_color="#1a2538",
            button_hover_color="#24334c",
            dropdown_fg_color="#101726",
            text_color=TEXT_WHITE,
            corner_radius=8,
            height=34,
            command=self._on_sort_change,
        )
        self.sort_menu.set(self.history_sort_order)
        self.sort_menu.pack(side="right")

        # Session Cards Stream
        self.history_items_container = ctk.CTkFrame(left_sessions_col, fg_color="transparent")
        self.history_items_container.pack(fill="both", expand=True)

        self._render_session_cards()

        # --------------------------------------------------------
        # 3. RIGHT COLUMN: Quick Stats + Filters + Recent Topics
        # --------------------------------------------------------
        right_sidebar_col = ctk.CTkFrame(self.history_main_scroll, fg_color="transparent")
        right_sidebar_col.grid(row=1, column=1, sticky="nsew")

        # Card 1: Quick Stats (2x2 Grid)
        stats_card = ctk.CTkFrame(right_sidebar_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        stats_card.pack(fill="x", pady=(0, 14))

        st_in = ctk.CTkFrame(stats_card, fg_color="transparent")
        st_in.pack(fill="both", expand=True, padx=16, pady=16)

        st_h = ctk.CTkLabel(st_in, text="📈  Quick Stats", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_WHITE)
        st_h.pack(anchor="w", pady=(0, 12))

        # 2x2 Grid
        grid_2x2 = ctk.CTkFrame(st_in, fg_color="transparent")
        grid_2x2.pack(fill="x")
        grid_2x2.grid_columnconfigure(0, weight=1, uniform="stat_cell")
        grid_2x2.grid_columnconfigure(1, weight=1, uniform="stat_cell")

        stat_items = [
            ("📅", total_sessions_text, "Total Sessions", 0, 0, "#38bdf8"),
            ("🏆", avg_score_text.replace("/10", ""), "Average Score", 0, 1, "#f59e0b"),
            ("〰️", avg_fluency_text, "Avg. Fluency", 1, 0, "#10b981"),
            ("⭐", best_score_text, "Best Score", 1, 1, "#c084fc"),
        ]

        for icon, val, lbl, r_idx, c_idx, color in stat_items:
            cell = ctk.CTkFrame(grid_2x2, fg_color="#090e18", corner_radius=10, border_width=1, border_color="#152030", height=66)
            cell.grid(row=r_idx, column=c_idx, padx=4, pady=4, sticky="nsew")
            cell.pack_propagate(False)

            c_in = ctk.CTkFrame(cell, fg_color="transparent")
            c_in.pack(expand=True, padx=8)

            c_row = ctk.CTkFrame(c_in, fg_color="transparent")
            c_row.pack(anchor="w")

            i_l = ctk.CTkLabel(c_row, text=icon, font=ctk.CTkFont(size=14))
            i_l.pack(side="left", padx=(0, 6))

            v_l = ctk.CTkLabel(c_row, text=val, font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=TEXT_WHITE)
            v_l.pack(side="left")

            l_l = ctk.CTkLabel(c_in, text=lbl, font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE)
            l_l.pack(anchor="w")

        # Card 2: Filters Card
        filter_card = ctk.CTkFrame(right_sidebar_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        filter_card.pack(fill="x", pady=(0, 14))

        f_in = ctk.CTkFrame(filter_card, fg_color="transparent")
        f_in.pack(fill="both", expand=True, padx=16, pady=16)

        f_head_row = ctk.CTkFrame(f_in, fg_color="transparent")
        f_head_row.pack(fill="x", pady=(0, 12))

        f_h = ctk.CTkLabel(f_head_row, text="🌪️  Filters", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_WHITE)
        f_h.pack(side="left")

        btn_clear_f = ctk.CTkButton(
            f_head_row,
            text="Clear All",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent",
            hover_color=CARD_HOVER,
            text_color=ACCENT_CYAN,
            width=60,
            height=24,
            command=self._clear_filters,
        )
        btn_clear_f.pack(side="right")

        # Date Range Filter
        f_d_lbl = ctk.CTkLabel(f_in, text="📅  Date Range", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SUBTLE)
        f_d_lbl.pack(anchor="w", pady=(0, 4))
        self.f_date_menu = ctk.CTkOptionMenu(
            f_in,
            values=["Last 30 days", "Last 7 days", "All time"],
            fg_color="#090e18",
            button_color="#182334",
            dropdown_fg_color="#090e18",
            corner_radius=8,
            height=34,
        )
        self.f_date_menu.pack(fill="x", pady=(0, 10))

        # Topic Filter
        f_t_lbl = ctk.CTkLabel(f_in, text="📑  Topic", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SUBTLE)
        f_t_lbl.pack(anchor="w", pady=(0, 4))
        self.f_topic_menu = ctk.CTkOptionMenu(
            f_in,
            values=["All Topics", "Technology", "Science", "History", "Business", "Society", "Environment", "Entertainment"],
            fg_color="#090e18",
            button_color="#182334",
            dropdown_fg_color="#090e18",
            corner_radius=8,
            height=34,
        )
        self.f_topic_menu.set(self.history_selected_topic_filter)
        self.f_topic_menu.pack(fill="x", pady=(0, 10))

        # Performance Filter
        f_p_lbl = ctk.CTkLabel(f_in, text="📊  Performance", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SUBTLE)
        f_p_lbl.pack(anchor="w", pady=(0, 4))
        self.f_perf_menu = ctk.CTkOptionMenu(
            f_in,
            values=["All Scores", "High (8+)", "Medium (6–8)", "Low (<6)"],
            fg_color="#090e18",
            button_color="#182334",
            dropdown_fg_color="#090e18",
            corner_radius=8,
            height=34,
        )
        self.f_perf_menu.set(self.history_selected_perf_filter)
        self.f_perf_menu.pack(fill="x", pady=(0, 14))

        # Apply Filters Button
        btn_apply_f = ctk.CTkButton(
            f_in,
            text="Apply Filters",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            corner_radius=10,
            height=40,
            command=self._apply_history_filters,
        )
        btn_apply_f.pack(fill="x")

        # Card 3: Recent Topics Breakdown
        recent_card = ctk.CTkFrame(right_sidebar_col, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        recent_card.pack(fill="x", pady=(0, 14))

        rc_in = ctk.CTkFrame(recent_card, fg_color="transparent")
        rc_in.pack(fill="both", expand=True, padx=16, pady=16)

        rc_h = ctk.CTkLabel(rc_in, text="💡  Recent Topics", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#f59e0b")
        rc_h.pack(anchor="w", pady=(0, 10))

        # Calculate category breakdown dynamically
        cat_counts = {}
        for s in self.cached_history_sessions:
            c_name = s.get("category", "General")
            cat_counts[c_name] = cat_counts.get(c_name, 0) + 1

        dot_colors = ["🔵", "🟣", "🟢", "🔴", "🟡", "🟠"]
        if cat_counts:
            recent_items = [
                (dot_colors[i % len(dot_colors)], cat_name, str(count))
                for i, (cat_name, count) in enumerate(cat_counts.items())
            ]
        else:
            recent_items = [("⚪", "No practice topics yet", "0")]

        for dot, name, cnt in recent_items:
            r_row = ctk.CTkFrame(rc_in, fg_color="transparent")
            r_row.pack(fill="x", pady=3)

            r_left = ctk.CTkFrame(r_row, fg_color="transparent")
            r_left.pack(side="left")

            d_lbl = ctk.CTkLabel(r_left, text=dot, font=ctk.CTkFont(size=10))
            d_lbl.pack(side="left", padx=(0, 6))

            n_lbl = ctk.CTkLabel(r_left, text=name, font=ctk.CTkFont(family="Segoe UI", size=12), text_color=TEXT_MUTED)
            n_lbl.pack(side="left")

            c_lbl = ctk.CTkLabel(r_row, text=cnt, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_WHITE)
            c_lbl.pack(side="right")

    def _render_session_cards(self):
        """Populate the sessions list from dynamic MySQL records with empty state handling."""
        for w in self.history_items_container.winfo_children():
            w.destroy()

        sessions = getattr(self, "cached_history_sessions", None)
        if sessions is None:
            sessions = self._load_user_history_from_db()
            self.cached_history_sessions = sessions

        # Apply category filter if active
        if self.history_selected_topic_filter != "All Topics":
            sessions = [s for s in sessions if s["category"].lower() == self.history_selected_topic_filter.lower()]

        # Apply score filter
        if self.history_selected_perf_filter == "High (8+)":
            sessions = [s for s in sessions if s["score"] >= 8.0]
        elif self.history_selected_perf_filter == "Medium (6–8)":
            sessions = [s for s in sessions if 6.0 <= s["score"] < 8.0]
        elif self.history_selected_perf_filter == "Low (<6)":
            sessions = [s for s in sessions if s["score"] < 6.0]

        # Apply sorting
        if self.history_sort_order == "Newest First":
            pass  # Already descending from SQL query
        elif self.history_sort_order == "Oldest First":
            sessions = list(reversed(sessions))
        elif self.history_sort_order == "Highest Score":
            sessions = sorted(sessions, key=lambda x: x["score"], reverse=True)
        elif self.history_sort_order == "Lowest Score":
            sessions = sorted(sessions, key=lambda x: x["score"], reverse=False)

        # Empty state when no sessions found
        if not sessions:
            empty_card = ctk.CTkFrame(
                self.history_items_container,
                fg_color="#0c1320",
                corner_radius=16,
                border_width=1,
                border_color="#182334",
            )
            empty_card.pack(fill="x", pady=20)

            e_inner = ctk.CTkFrame(empty_card, fg_color="transparent")
            e_inner.pack(fill="both", expand=True, padx=24, pady=40)

            e_icon = ctk.CTkLabel(e_inner, text="🕒", font=ctk.CTkFont(size=44))
            e_icon.pack(pady=(0, 12))

            has_any = bool(getattr(self, "cached_history_sessions", []))
            title_text = "No Filtered Sessions Found" if has_any else "No Practice Sessions Yet"
            sub_text = (
                "Try adjusting your topic or performance filter to see your past sessions."
                if has_any
                else "You haven't completed any speech practice sessions yet.\nStart your first session in Practice mode to track your speaking progress, fluency, and analytics here!"
            )

            e_title = ctk.CTkLabel(
                e_inner,
                text=title_text,
                font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                text_color=TEXT_WHITE,
            )
            e_title.pack(pady=(0, 6))

            e_desc = ctk.CTkLabel(
                e_inner,
                text=sub_text,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=TEXT_MUTED,
                justify="center",
            )
            e_desc.pack(pady=(0, 20))

            if not has_any:
                btn_start_now = ctk.CTkButton(
                    e_inner,
                    text="Start Practice Now  ➔",
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    fg_color=ACCENT_BLUE,
                    hover_color="#2563eb",
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
            fg_color="#0c1320",
            corner_radius=14,
            border_width=1,
            border_color="#182334",
            height=90,
            cursor="hand2",
        )
        card.pack(fill="x", pady=6)

        inner = ctk.CTkFrame(card, fg_color="transparent", cursor="hand2")
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        # 1. Left Thumbnail Box with checkmark
        thumb_box = ctk.CTkFrame(inner, width=48, height=48, corner_radius=10, fg_color=sess.get("icon_bg", "#172338"), cursor="hand2")
        thumb_box.pack(side="left", padx=(0, 14))
        thumb_box.pack_propagate(False)

        icon_lbl = ctk.CTkLabel(thumb_box, text=sess.get("icon", "🎙️"), font=ctk.CTkFont(size=20), cursor="hand2")
        icon_lbl.pack(expand=True)

        chk_badge = ctk.CTkLabel(
            thumb_box,
            text="✓",
            font=ctk.CTkFont(size=8, weight="bold"),
            fg_color="#10b981",
            text_color=TEXT_WHITE,
            width=14,
            height=14,
            corner_radius=7,
            cursor="hand2",
        )
        chk_badge.place(relx=1.0, rely=0.0, x=-2, y=2, anchor="ne")

        # 2. Topic & Category & Date
        info_col = ctk.CTkFrame(inner, fg_color="transparent", width=240, cursor="hand2")
        info_col.pack(side="left", fill="y", padx=(0, 10))

        t_lbl = ctk.CTkLabel(
            info_col,
            text=sess.get("topic", "Speech Practice"),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
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
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#27193b",
            text_color="#c084fc",
            corner_radius=4,
            cursor="hand2",
        )
        cat_lbl.pack(side="left", padx=(0, 8))

        date_lbl = ctk.CTkLabel(
            sub_row,
            text=f"📅 {sess.get('date', '')}",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_SUBTLE,
            cursor="hand2",
        )
        date_lbl.pack(side="left")

        # 3. Speaking Time Section
        time_col = ctk.CTkFrame(inner, fg_color="transparent", width=110, cursor="hand2")
        time_col.pack(side="left", fill="y", padx=(0, 10))

        time_cap = ctk.CTkLabel(time_col, text="⏱️  Speaking Time", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE, anchor="w", cursor="hand2")
        time_cap.pack(anchor="w")

        time_val = ctk.CTkLabel(time_col, text=sess.get("duration", "1:00"), font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_WHITE, anchor="w", cursor="hand2")
        time_val.pack(anchor="w")

        time_tgt = ctk.CTkLabel(time_col, text=f"Target: {sess.get('target', '1:00')}", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE, anchor="w", cursor="hand2")
        time_tgt.pack(anchor="w")

        # 4. Score Section
        score_col = ctk.CTkFrame(inner, fg_color="transparent", width=100, cursor="hand2")
        score_col.pack(side="left", fill="y", padx=(0, 10))

        s_cap = ctk.CTkLabel(score_col, text="Score", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE, anchor="w", cursor="hand2")
        s_cap.pack(anchor="w")

        s_val = ctk.CTkLabel(score_col, text=f"🏆 {sess.get('score', 7.5):.1f}/10", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_WHITE, anchor="w", cursor="hand2")
        s_val.pack(anchor="w")

        s_note = ctk.CTkLabel(score_col, text=sess.get("score_label", "Good job!"), font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=sess.get("score_color", ACCENT_EMERALD), anchor="w", cursor="hand2")
        s_note.pack(anchor="w")

        # 5. Filler Words Section
        fill_col = ctk.CTkFrame(inner, fg_color="transparent", width=100, cursor="hand2")
        fill_col.pack(side="left", fill="y", padx=(0, 14))

        f_cap = ctk.CTkLabel(fill_col, text="💬  Filler Words", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SUBTLE, anchor="w", cursor="hand2")
        f_cap.pack(anchor="w")

        f_val = ctk.CTkLabel(fill_col, text=f"💬 {sess.get('fillers', '0')}", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_WHITE, anchor="w", cursor="hand2")
        f_val.pack(anchor="w")

        # 6. Action Buttons (View Details + More ⋮)
        btn_details = ctk.CTkButton(
            inner,
            text="View Details  ➔",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="transparent",
            hover_color="#182436",
            border_width=1,
            border_color="#1e2c40",
            text_color=TEXT_WHITE,
            corner_radius=8,
            height=32,
            width=100,
            command=lambda s=sess: self._open_session_report_from_history(s),
        )
        btn_details.pack(side="right", padx=(6, 0))

        btn_more = ctk.CTkLabel(inner, text=" ⋮ ", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_MUTED, cursor="hand2")
        btn_more.pack(side="right")

        # Bind click on entire card and sub-elements to open report
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

        # Hover effects
        def _on_hover_enter(event=None):
            card.configure(fg_color="#121b2c", border_color="#3b82f6")
        def _on_hover_leave(event=None):
            card.configure(fg_color="#0c1320", border_color="#182334")

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


    def _on_hist_tab_click(self, tab_name):
        self.history_active_tab = tab_name
        for tn, btn in self.hist_tab_buttons.items():
            if tn == tab_name:
                btn.configure(fg_color="#182335", text_color=TEXT_WHITE, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED, font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal"))
        self._render_session_cards()

    def _on_sort_change(self, val):
        self.history_sort_order = val
        self._render_session_cards()

    def _apply_history_filters(self):
        self.history_selected_topic_filter = self.f_topic_menu.get()
        self.history_selected_perf_filter = self.f_perf_menu.get()
        self._render_session_cards()

    def _clear_filters(self):
        self.f_date_menu.set("Last 30 days")
        self.f_topic_menu.set("All Topics")
        self.f_perf_menu.set("All Scores")
        self.history_selected_topic_filter = "All Topics"
        self.history_selected_perf_filter = "All Scores"
        self._render_session_cards()

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
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=TEXT_WHITE,
        )
        title.pack(anchor="w", pady=(0, 20))

        if not self.current_user:
            # GUEST VIEW
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
                fg_color="#1e293b",
                text_color=TEXT_WHITE,
                font=ctk.CTkFont(size=24),
            )
            av.pack(side="left", padx=(0, 16))

            info = ctk.CTkFrame(p_row, fg_color="transparent")
            info.pack(side="left")

            n_lbl = ctk.CTkLabel(info, text="Guest Account", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=TEXT_WHITE)
            n_lbl.pack(anchor="w")

            e_lbl = ctk.CTkLabel(info, text="Not signed in • Browse & guest practice mode", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=TEXT_MUTED)
            e_lbl.pack(anchor="w", pady=(2, 0))

            g_desc = ctk.CTkLabel(
                inner,
                text="You are currently practicing as a Guest. Sign in or register for free to save speech recordings, monitor progress, and access detailed analytics.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=TEXT_MUTED,
                justify="left",
            )
            g_desc.pack(anchor="w", pady=(0, 20))

            btn_bar = ctk.CTkFrame(inner, fg_color="transparent")
            btn_bar.pack(anchor="w")

            btn_login = ctk.CTkButton(
                btn_bar,
                text="🔑 Sign In",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color=ACCENT_BLUE,
                hover_color="#2563eb",
                corner_radius=10,
                height=44,
                command=lambda: self.open_auth_modal("login"),
            )
            btn_login.pack(side="left", padx=(0, 12))

            btn_register = ctk.CTkButton(
                btn_bar,
                text="✨ Create New Account",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color=ACCENT_EMERALD,
                hover_color="#059669",
                corner_radius=10,
                height=44,
                command=lambda: self.open_auth_modal("register"),
            )
            btn_register.pack(side="left")

        else:
            # LOGGED IN VIEW
            card = ctk.CTkFrame(self.profile_content, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
            card.pack(fill="x", pady=(0, 20))

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=24, pady=24)

            name = self.current_user.get("name", "User")
            email = self.current_user.get("email", "")
            user_id = self.current_user.get("user_id", 1)
            initials = "".join([part[0].upper() for part in name.split()[:2]]) or "U"

            # Avatar + Details Row
            p_row = ctk.CTkFrame(inner, fg_color="transparent")
            p_row.pack(fill="x")

            av = ctk.CTkLabel(
                p_row,
                text=initials,
                width=56,
                height=56,
                corner_radius=28,
                fg_color=ACCENT_BLUE,
                text_color=TEXT_WHITE,
                font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            )
            av.pack(side="left", padx=(0, 16))

            info = ctk.CTkFrame(p_row, fg_color="transparent")
            info.pack(side="left")

            n_lbl = ctk.CTkLabel(info, text=name, font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=TEXT_WHITE)
            n_lbl.pack(anchor="w")

            e_lbl = ctk.CTkLabel(info, text=f"{email}   •   User ID: #{user_id}", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=TEXT_MUTED)
            e_lbl.pack(anchor="w", pady=(2, 0))

            # Stats Counters
            total_speeches = 0
            try:
                db = get_connection()
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT COUNT(*) AS total FROM sessions WHERE user_id = %s", (user_id,))
                total_speeches = cursor.fetchone()["total"]
                cursor.close()
                db.close()
            except Exception:
                pass

            stats_row = ctk.CTkFrame(self.profile_content, fg_color="transparent")
            stats_row.pack(fill="x", pady=(0, 24))
            for col in range(3):
                stats_row.grid_columnconfigure(col, weight=1, uniform="prof_stat")

            p_stats = [
                ("Total Speeches Practiced", str(total_speeches), "🎙️"),
                ("Available Domains", "16 Categories", "📚"),
                ("Membership Tier", "Pro Student", "⭐"),
            ]

            for c_idx, (s_label, s_val, s_icon) in enumerate(p_stats):
                scard = ctk.CTkFrame(stats_row, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color=CARD_BORDER)
                scard.grid(row=0, column=c_idx, padx=8, sticky="nsew", ipady=8)

                ic = ctk.CTkLabel(scard, text=s_icon, font=ctk.CTkFont(size=22))
                ic.pack(pady=(12, 2))

                v = ctk.CTkLabel(scard, text=s_val, font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=TEXT_WHITE)
                v.pack()

                l = ctk.CTkLabel(scard, text=s_label, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED)
                l.pack(pady=(0, 12))

            # Action Buttons: Sign In / Create Account / Log Out / Delete Account
            btn_bar = ctk.CTkFrame(self.profile_content, fg_color="transparent")
            btn_bar.pack(fill="x", pady=(8, 0))

            btn_login = ctk.CTkButton(
                btn_bar,
                text="🔑 Switch User / Log In",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="#182334",
                hover_color=CARD_HOVER,
                border_width=1,
                border_color=CARD_BORDER,
                corner_radius=10,
                height=44,
                command=lambda: self.open_auth_modal("login"),
            )
            btn_login.pack(side="left", padx=(0, 10))

            btn_register = ctk.CTkButton(
                btn_bar,
                text="➕ Register New User",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                fg_color=ACCENT_BLUE,
                hover_color="#2563eb",
                corner_radius=10,
                height=44,
                command=lambda: self.open_auth_modal("register"),
            )
            btn_register.pack(side="left", padx=(0, 10))

            btn_logout = ctk.CTkButton(
                btn_bar,
                text="🚪 Sign Out",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="#1c1917",
                hover_color="#292524",
                border_width=1,
                border_color="#44403c",
                text_color=TEXT_WHITE,
                corner_radius=10,
                height=44,
                command=self._handle_logout,
            )
            btn_logout.pack(side="left", padx=(0, 10))

            btn_delete = ctk.CTkButton(
                btn_bar,
                text="🗑️ Delete Account",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                corner_radius=10,
                height=44,
                command=self._handle_delete_user_account,
            )
            btn_delete.pack(side="left")

    def _handle_logout(self):
        """Log out current user and return to guest state."""
        self.current_user = None
        self._update_current_user_ui()
        self._refresh_profile_content()
        self.show_page("home")
        messagebox.showinfo("Signed Out", "You have been signed out.")

    def _handle_delete_user_account(self):
        if not self.current_user:
            return

        confirm = messagebox.askyesno(
            "Confirm Account Deletion",
            f"Are you sure you want to permanently delete account '{self.current_user['name']}' ({self.current_user['email']}) from MySQL?",
        )
        if not confirm:
            return

        success, msg = delete_user(self.current_user["user_id"])
        if success:
            messagebox.showinfo("Account Deleted", "Your account and all speech takes were deleted from MySQL.")
            self.current_user = None
            self._update_current_user_ui()
            self._refresh_profile_content()
            self.show_page("home")
        else:
            messagebox.showerror("Error", f"Failed to delete account: {msg}")

    # ============================================================
    # AUTH MODAL (LOGIN & REGISTER TABS - REAL-TIME MYSQL)
    # ============================================================

    def open_auth_modal(self, initial_tab="login"):
        """Open modern modal dialog supporting both Login and New User Registration with real-time MySQL persistence."""
        modal = ctk.CTkToplevel(self)
        modal.title("Account Authentication — SpeakWise AI")
        modal.geometry("520x640")
        modal.resizable(False, False)
        modal.configure(fg_color=BG_DARK)
        modal.grab_set()

        # Center on parent
        modal.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 260
        y = self.winfo_y() + (self.winfo_height() // 2) - 320
        modal.geometry(f"+{x}+{y}")

        container = ctk.CTkFrame(modal, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Tabview for Login & Register
        tabview = ctk.CTkTabview(
            container,
            fg_color="transparent",
            segmented_button_fg_color="#182334",
            segmented_button_selected_color=ACCENT_BLUE,
            segmented_button_selected_hover_color="#2563eb",
            segmented_button_unselected_color="#182334",
            segmented_button_unselected_hover_color=CARD_HOVER,
        )
        tabview.pack(fill="both", expand=True, padx=16, pady=12)

        tab_login = tabview.add("Log In")
        tab_register = tabview.add("Create Account")

        if initial_tab == "register":
            tabview.set("Create Account")
        else:
            tabview.set("Log In")

        # --------------------------------------------------------
        # TAB 1: LOG IN
        # --------------------------------------------------------
        l_head = ctk.CTkLabel(
            tab_login,
            text="Welcome Back!",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT_WHITE,
        )
        l_head.pack(pady=(16, 4))

        l_sub = ctk.CTkLabel(
            tab_login,
            text="Sign in to track your speech sessions and progress.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED,
        )
        l_sub.pack(pady=(0, 16))

        l_email = ctk.CTkEntry(tab_login, placeholder_text="Email Address or Name", height=44, corner_radius=8, font=ctk.CTkFont(size=13))
        l_email.pack(fill="x", padx=16, pady=8)

        l_pw = ctk.CTkEntry(tab_login, placeholder_text="Password", show="•", height=44, corner_radius=8, font=ctk.CTkFont(size=13))
        l_pw.pack(fill="x", padx=16, pady=8)

        l_status = ctk.CTkLabel(tab_login, text="", font=ctk.CTkFont(size=12), text_color="#f87171")
        l_status.pack(pady=4)

        def do_login():
            ident = l_email.get().strip()
            pw = l_pw.get().strip()
            if not ident or not pw:
                if l_status.winfo_exists():
                    l_status.configure(text="Please enter both email/name and password.", text_color="#f87171")
                return

            success, result = authenticate_user(ident, pw)
            if success:
                self.current_user = result
                self._update_current_user_ui()
                self._refresh_profile_content()
                try:
                    modal.grab_release()
                    modal.destroy()
                except Exception:
                    pass
                messagebox.showinfo("Login Successful", f"Welcome back, {result['name']}!")
            else:
                if l_status.winfo_exists():
                    l_status.configure(text=str(result), text_color="#f87171")

        btn_l_submit = ctk.CTkButton(
            tab_login,
            text="Sign In",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
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
            text_color=ACCENT_CYAN,
            hover=False,
            command=lambda: tabview.set("Create Account"),
        )
        btn_switch_reg.pack()

        # --------------------------------------------------------
        # TAB 2: REGISTER NEW USER (REAL-TIME DYNAMIC MYSQL)
        # --------------------------------------------------------
        r_head = ctk.CTkLabel(
            tab_register,
            text="Create New Account",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT_WHITE,
        )
        r_head.pack(pady=(12, 4))

        r_sub = ctk.CTkLabel(
            tab_register,
            text="Join SpeakWise AI to practice and improve your speaking.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED,
        )
        r_sub.pack(pady=(0, 14))

        r_name = ctk.CTkEntry(tab_register, placeholder_text="Full Name (e.g. Rahul Kulkarni)", height=40, corner_radius=8, font=ctk.CTkFont(size=13))
        r_name.pack(fill="x", padx=16, pady=6)

        r_email = ctk.CTkEntry(tab_register, placeholder_text="Email Address (e.g. rahul@example.com)", height=40, corner_radius=8, font=ctk.CTkFont(size=13))
        r_email.pack(fill="x", padx=16, pady=6)

        r_pw = ctk.CTkEntry(tab_register, placeholder_text="Password (min 6 characters)", show="•", height=40, corner_radius=8, font=ctk.CTkFont(size=13))
        r_pw.pack(fill="x", padx=16, pady=6)

        r_confirm = ctk.CTkEntry(tab_register, placeholder_text="Confirm Password", show="•", height=40, corner_radius=8, font=ctk.CTkFont(size=13))
        r_confirm.pack(fill="x", padx=16, pady=6)

        r_status = ctk.CTkLabel(tab_register, text="", font=ctk.CTkFont(size=12), text_color="#f87171")
        r_status.pack(pady=2)

        def do_register():
            name_val = r_name.get().strip()
            email_val = r_email.get().strip().lower()
            pw_val = r_pw.get().strip()
            confirm_val = r_confirm.get().strip()

            if not name_val or not email_val or not pw_val or not confirm_val:
                if r_status.winfo_exists():
                    r_status.configure(text="Please fill out all registration fields.", text_color="#f87171")
                return

            if pw_val != confirm_val:
                if r_status.winfo_exists():
                    r_status.configure(text="Passwords do not match.", text_color="#f87171")
                return

            success, result = register_user(name_val, email_val, pw_val)
            if success:
                self.current_user = result
                self._update_current_user_ui()
                self._refresh_profile_content()
                try:
                    modal.grab_release()
                    modal.destroy()
                except Exception:
                    pass
                messagebox.showinfo("Registration Successful", f"Welcome to SpeakWise AI, {name_val}! Your account was dynamically added to MySQL in real-time.")
            else:
                if r_status.winfo_exists():
                    r_status.configure(text=str(result), text_color="#f87171")

        btn_r_submit = ctk.CTkButton(
            tab_register,
            text="Register & Sign In",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
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
            text_color=ACCENT_CYAN,
            hover=False,
            command=lambda: tabview.set("Log In"),
        )
        btn_switch_login.pack()

    def _update_current_user_ui(self):
        """Update top bar user badge and initials upon login/register/logout and flush pending takes."""
        if self.current_user:
            u_name = self.current_user.get("name", "User")
            initials = "".join([part[0].upper() for part in u_name.split()[:2]]) or "U"
            role_text = "Student"
            circle_bg = ACCENT_BLUE

            # Auto-save any buffered session from guest practice into MySQL
            if getattr(self, "last_unsaved_session", None):
                try:
                    save_speech_session(
                        user_id=self.current_user["user_id"],
                        **self.last_unsaved_session,
                    )
                    self.last_unsaved_session = None
                except Exception as e:
                    print(f"[Auto-Save Session Error] {e}")
        else:
            u_name = "Sign In / Register"
            initials = "👤"
            role_text = "Guest Mode"
            circle_bg = "#1f293d"

        if hasattr(self, "top_u_circle"):
            self.top_u_circle.configure(text=initials, fg_color=circle_bg)
        if hasattr(self, "top_u_name_lbl"):
            self.top_u_name_lbl.configure(text=u_name)
        if hasattr(self, "top_u_role_lbl"):
            self.top_u_role_lbl.configure(text=role_text)

        if hasattr(self, "home_container"):
            self._render_home_content()

    def _open_database_inspector(self):
        """Open real-time MySQL database table and user inspector."""
        modal = ctk.CTkToplevel(self)
        modal.title("MySQL Database Tables & Users — SpeakWise AI")
        modal.geometry("700x520")
        modal.configure(fg_color=BG_DARK)

        # Center on parent
        modal.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 350
        y = self.winfo_y() + (self.winfo_height() // 2) - 260
        modal.geometry(f"+{x}+{y}")

        box = ctk.CTkFrame(modal, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkLabel(box, text="🗄️ MySQL Database Tables & Records", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=TEXT_WHITE)
        header.pack(anchor="w", padx=20, pady=(20, 4))

        stats = get_db_stats() or {"users": 0, "sessions": 0, "takes": 0}
        sub = ctk.CTkLabel(
            box,
            text=f"Connected to MySQL (`speakwise`)  •  Total Users: {stats['users']}  •  Total Sessions: {stats['sessions']}  •  Total Takes: {stats['takes']}",
            font=ctk.CTkFont(size=12),
            text_color=ACCENT_CYAN,
        )
        sub.pack(anchor="w", padx=20, pady=(0, 16))

        # Users table display
        tbl_frame = ctk.CTkScrollableFrame(box, fg_color="#0c111a", corner_radius=10)
        tbl_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Header row
        h_row = ctk.CTkFrame(tbl_frame, fg_color="#182334", corner_radius=6)
        h_row.pack(fill="x", pady=2, ipady=4)
        ctk.CTkLabel(h_row, text="User ID", width=70, font=ctk.CTkFont(weight="bold", size=12), text_color=TEXT_WHITE).pack(side="left", padx=4)
        ctk.CTkLabel(h_row, text="Name", width=180, font=ctk.CTkFont(weight="bold", size=12), text_color=TEXT_WHITE, anchor="w").pack(side="left", padx=4)
        ctk.CTkLabel(h_row, text="Email", width=240, font=ctk.CTkFont(weight="bold", size=12), text_color=TEXT_WHITE, anchor="w").pack(side="left", padx=4)
        ctk.CTkLabel(h_row, text="Sessions", width=80, font=ctk.CTkFont(weight="bold", size=12), text_color=TEXT_WHITE).pack(side="left", padx=4)

        users = get_all_users()
        for u in users:
            u_row = ctk.CTkFrame(tbl_frame, fg_color="transparent")
            u_row.pack(fill="x", pady=2, ipady=3)
            ctk.CTkLabel(u_row, text=f"#{u['user_id']}", width=70, font=ctk.CTkFont(size=12), text_color=ACCENT_BLUE).pack(side="left", padx=4)
            ctk.CTkLabel(u_row, text=u['name'], width=180, font=ctk.CTkFont(size=12), text_color=TEXT_WHITE, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(u_row, text=u['email'], width=240, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(u_row, text=str(u['session_count']), width=80, font=ctk.CTkFont(size=12), text_color=ACCENT_EMERALD).pack(side="left", padx=4)

        btn_close = ctk.CTkButton(box, text="Close", font=ctk.CTkFont(size=13), fg_color="#1e293b", hover_color="#334155", command=modal.destroy, height=36)
        btn_close.pack(anchor="e", padx=20, pady=(0, 16))

    def _create_settings_view(self):
        frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        title = ctk.CTkLabel(
            frame,
            text="Application Settings & Database",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=TEXT_WHITE,
        )
        title.pack(anchor="w", pady=(0, 20))

        # App Architecture Card
        card = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=20)

        lbl = ctk.CTkLabel(
            inner,
            text="Display Resolution : 1920x1080 (HD)\nDisplay Mode       : Dark (Default)\nAudio Engine       : CrisperWhisper\nComputer Vision    : MediaPipe Multi-Landmark Face Mesh\nAI Model           : Gemini 3.6 Flash",
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=TEXT_MUTED,
            justify="left",
        )
        lbl.pack(anchor="w")

        # Database Management Card
        db_card = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=CARD_BORDER)
        db_card.pack(fill="x", pady=6)

        db_inner = ctk.CTkFrame(db_card, fg_color="transparent")
        db_inner.pack(fill="x", padx=24, pady=20)

        db_title = ctk.CTkLabel(db_inner, text="🗄️ MySQL Database Engine", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=TEXT_WHITE)
        db_title.pack(anchor="w", pady=(0, 6))

        stats = get_db_stats() or {"users": 0, "sessions": 0, "takes": 0}
        db_desc = ctk.CTkLabel(
            db_inner,
            text=f"Database: speakwise  •  Status: Connected & Autocommit Active\nTables: users ({stats['users']}), sessions ({stats['sessions']}), takes ({stats['takes']})\nAll registrations, logins, and speech takes are persisted dynamically in real-time.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_MUTED,
            justify="left",
        )
        db_desc.pack(anchor="w", pady=(0, 16))

        btn_db_inspect = ctk.CTkButton(
            db_inner,
            text="🔍 View MySQL Tables & Users",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
            corner_radius=10,
            height=40,
            command=self._open_database_inspector,
        )
        btn_db_inspect.pack(anchor="w")

        return frame



if __name__ == "__main__":
    app = SpeakWiseApp()
    app.mainloop()

