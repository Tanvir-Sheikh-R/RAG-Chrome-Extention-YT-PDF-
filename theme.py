"""
Visual theme — orange (#F97C37) + dark (#161A1E), matching the reference design.

Everything visual lives here. app.py never contains a hex code or CSS rule —
if you want to restyle later, this is the only file you touch.
"""

import streamlit as st

ORANGE = "#F97C37"
ORANGE_DARK = "#E2661F"
DARK = "#161A1E"
PAGE_BG = "#F7F7F8"
CARD_BG = "#FFFFFF"
BORDER = "#E5E5E5"
GRAY_TEXT = "#6B7280"


def apply_theme() -> None:
    """Inject the site-wide CSS. Call once at the top of app.py."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}
        .stApp {{
            background-color: {PAGE_BG};
        }}

        /* Two-tone hero title, e.g. hero_title("AI Content", "Summarizer") */
        .hero-title {{
            text-align: center;
            font-size: 2.4rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}
        .hero-title .dark {{ color: {DARK}; }}
        .hero-title .accent {{ color: {ORANGE}; }}
        .hero-subtitle {{
            text-align: center;
            color: {GRAY_TEXT};
            font-size: 1rem;
            margin-bottom: 1.75rem;
        }}

        /* Tab-style toggle buttons (Document / YouTube) and all buttons */
        div.stButton > button {{
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.15s ease-in-out;
        }}
        div.stButton > button[kind="primary"] {{
            background-color: {ORANGE};
            color: white;
            border: none;
        }}
        div.stButton > button[kind="primary"]:hover {{
            background-color: {ORANGE_DARK};
        }}
        div.stButton > button[kind="secondary"] {{
            background-color: {CARD_BG};
            color: {DARK};
            border: 1px solid {BORDER};
        }}

        /* Text inputs — rounded, matches the search-bar look */
        div.stTextInput > div > div > input {{
            border-radius: 999px;
            border: 1px solid {BORDER};
            padding: 0.6rem 1.1rem;
        }}
        div.stTextInput > div > div > input:focus {{
            border-color: {ORANGE};
            box-shadow: 0 0 0 1px {ORANGE};
        }}

        /* Generic content card (used for results / summary panels) */
        .content-card {{
            background-color: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            max-height: 520px;
            overflow-y: auto;
        }}

        /* AI Tutor panel header */
        .tutor-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            color: {DARK};
            margin-bottom: 0.5rem;
        }}
        .tutor-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: {ORANGE};
            display: inline-block;
        }}
        .tutor-empty {{
            text-align: center;
            color: {GRAY_TEXT};
            padding: 2.5rem 1rem;
        }}
        .tutor-empty b {{ color: {DARK}; font-size: 1.05rem; }}

        /* Loading card */
        .loading-card {{
            background-color: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 3rem 2rem;
            text-align: center;
        }}
        .loading-card h3 {{ color: {DARK}; margin: 0.75rem 0 0.25rem 0; }}
        .loading-card p {{ color: {GRAY_TEXT}; margin: 0; }}
        .loading-tip {{
            color: {GRAY_TEXT};
            font-size: 0.85rem;
            margin-top: 1.25rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero_title(dark_part: str, accent_part: str, subtitle: str) -> None:
    """Two-tone title (dark word(s) + orange word(s)) plus a gray subtitle."""
    st.markdown(
        f"""
        <div class="hero-title"><span class="dark">{dark_part}</span> <span class="accent">{accent_part}</span></div>
        <div class="hero-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def loading_card(title: str, subtitle: str, tip: str) -> None:
    st.markdown(
        f"""
        <div class="loading-card">
            <div style="font-size:2.5rem;">⏳</div>
            <h3>{title}</h3>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="loading-tip">💡 Tip: {tip}</div>', unsafe_allow_html=True)


def content_card(html_or_text: str) -> None:
    st.markdown(f'<div class="content-card">{html_or_text}</div>', unsafe_allow_html=True)


def tutor_header() -> None:
    st.markdown('<div class="tutor-header"><span class="tutor-dot"></span> AI Tutor</div>', unsafe_allow_html=True)


def tutor_empty_state() -> None:
    st.markdown(
        """
        <div class="tutor-empty">
            <b>Have a question about your content?</b><br>
            Ask anything and get instant, grounded answers based on what you summarized.
        </div>
        """,
        unsafe_allow_html=True,
    )
