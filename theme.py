"""
YouTube-flavored visual theme for the Streamlit app.

Keeping this in its own module means style tweaks (colors, fonts, chat
bubble shapes) never require touching app.py's logic — just edit the
CSS string below and rerun.
"""

import streamlit as st

YOUTUBE_RED = "#FF0000"
YOUTUBE_RED_DARK = "#CC0000"
YOUTUBE_DARK_BG = "#0F0F0F"
YOUTUBE_CARD_BG = "#FFFFFF"
YOUTUBE_TEXT = "#0F0F0F"
YOUTUBE_GRAY = "#606060"


def apply_youtube_theme() -> None:
    """Inject YouTube-styled CSS. Call once, near the top of the app."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Roboto', Arial, sans-serif;
        }}

        /* Top bar accent */
        .yt-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0.75rem 0 1rem 0;
            border-bottom: 3px solid {YOUTUBE_RED};
            margin-bottom: 1.5rem;
        }}
        .yt-header .yt-logo {{
            background-color: {YOUTUBE_RED};
            color: white;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 1.1rem;
            letter-spacing: 0.5px;
        }}
        .yt-header .yt-title {{
            font-size: 1.4rem;
            font-weight: 500;
            color: {YOUTUBE_TEXT};
        }}

        /* Buttons — pill-shaped, YouTube red */
        div.stButton > button {{
            border-radius: 999px;
            border: none;
            font-weight: 500;
            padding: 0.5rem 1.25rem;
            transition: background-color 0.15s ease-in-out;
        }}
        div.stButton > button[kind="primary"] {{
            background-color: {YOUTUBE_RED};
            color: white;
        }}
        div.stButton > button[kind="primary"]:hover {{
            background-color: {YOUTUBE_RED_DARK};
        }}
        div.stButton > button[kind="secondary"] {{
            background-color: #F2F2F2;
            color: {YOUTUBE_TEXT};
            border: 1px solid #D3D3D3;
        }}
        div.stButton > button[kind="secondary"]:hover {{
            background-color: #E5E5E5;
        }}

        /* Text inputs — rounded, YouTube search-bar style */
        div.stTextInput > div > div > input {{
            border-radius: 999px;
            border: 1px solid #D3D3D3;
            padding: 0.5rem 1rem;
        }}
        div.stTextInput > div > div > input:focus {{
            border-color: {YOUTUBE_RED};
            box-shadow: 0 0 0 1px {YOUTUBE_RED};
        }}

        /* Chat bubbles */
        [data-testid="stChatMessage"] {{
            border-radius: 16px;
            padding: 0.25rem 0.5rem;
        }}

        /* Section captions */
        .yt-caption {{
            color: {YOUTUBE_GRAY};
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def youtube_header(title: str = "Video Summarizer") -> None:
    """Render a small YouTube-style header bar."""
    st.markdown(
        f"""
        <div class="yt-header">
            <span class="yt-logo">▶ YouTube</span>
            <span class="yt-title">{title}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
