"""Pure helpers for the user-selectable theme (background + text colour).

No Streamlit imports here so everything can be unit-tested.
"""
from __future__ import annotations

import re

from config import MIN_CONTRAST_BLOCK, MIN_CONTRAST_WARN, THEME_PRESETS

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_hex(value: str | None) -> bool:
    return bool(value and _HEX.match(value))


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(c))) for c in rgb)


def _lin(c: int) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(h: str) -> float:
    r, g, b = _rgb(h)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(a: str, b: str) -> float:
    """WCAG contrast ratio between two #RRGGBB colours (1.0 .. 21.0)."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def mix(a: str, b: str, amount: float) -> str:
    """Blend colour `a` towards colour `b` by `amount` (0..1)."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * amount for x, y in zip(ra, rb)))


def resolve_theme(preset: str | None, bg: str | None, text: str | None) -> tuple[str, str] | None:
    """Return (background, text) to apply, or None for Streamlit's own theme."""
    if preset == "Custom":
        if is_hex(bg) and is_hex(text):
            return bg.upper(), text.upper()
        return None
    pair = THEME_PRESETS.get(preset or "Default")
    return pair if pair else None


def validate_theme(bg: str, text: str) -> tuple[str, str]:
    """Return (level, message). level is 'ok', 'warn' or 'block'."""
    if not (is_hex(bg) and is_hex(text)):
        return "block", "Colours must be in #RRGGBB format."
    ratio = contrast_ratio(bg, text)
    if ratio < MIN_CONTRAST_BLOCK:
        return "block", f"These colours are too similar to read (contrast {ratio}:1, minimum {MIN_CONTRAST_BLOCK}:1). Please pick a lighter background with darker text, or the reverse."
    if ratio < MIN_CONTRAST_WARN:
        return "warn", f"Readable but low contrast ({ratio}:1). {MIN_CONTRAST_WARN}:1 or more is recommended."
    return "ok", f"Good contrast ({ratio}:1)."


BRAND_BG, BRAND_TEXT = "#F8F3F5", "#182B49"     # Prep.AI light palette (used when the student keeps the Default theme)


def tokens(primary: str, bg: str, text: str) -> str:
    """CSS variables for one palette. Light palettes get white cards; dark palettes get a card slightly lighter than the page."""
    light = luminance(bg) > 0.45
    card = "#FFFFFF" if light else mix(bg, text, 0.07)
    border = "#E8E1E5" if (light and bg.upper() == BRAND_BG) else mix(bg, text, 0.14 if light else 0.2)
    muted = "#718096" if (light and bg.upper() == BRAND_BG) else mix(text, bg, 0.4)
    ok, warn, err = ("#15803D", "#B45309", "#B91C1C") if light else ("#4ADE80", "#FBBF24", "#F87171")
    dark = mix(primary, "#000000", 0.28)
    soft = mix(primary, card, 0.9)
    return (f":root {{ --p-primary: {primary}; --p-primary-dark: {dark}; --p-primary-soft: {soft}; --p-primary-soft2: {mix(primary, card, 0.78)}; "
            f"--p-bg: {bg}; --p-card: {card}; --p-text: {text}; --p-muted: {muted}; --p-border: {border}; "
            f"--p-ok: {ok}; --p-warn: {warn}; --p-err: {err}; --p-ok-soft: {mix(ok, card, 0.86)}; --p-warn-soft: {mix(warn, card, 0.86)}; --p-err-soft: {mix(err, card, 0.88)}; "
            f"--prep-primary: {primary}; }}")


def build_css(primary: str, bg: str | None = None, text: str | None = None) -> str:
    """The whole stylesheet. Without bg/text the Prep.AI light palette is used; with them, the student's own colours (tokens + form-field fixes)."""
    from styles import COMPONENT_CSS, FONT_IMPORT
    custom = is_hex(bg) and is_hex(text)
    b, t = (bg, text) if custom else (BRAND_BG, BRAND_TEXT)
    css = FONT_IMPORT + "\n" + tokens(primary, b, t) + "\n"
    if custom:
        field = mix(b, t, 0.08)
        border = mix(b, t, 0.25)
        css += f"""
    /* ---- user theme: background {b}, text {t} ---- */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background-color: {b} !important; color: {t} !important; }}
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div {{ background-color: var(--p-card) !important; }}
    .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stCaptionContainer"],
    .stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricLabel"], .stApp summary,
    .stApp [data-baseweb="tab"] {{ color: {t}; }}
    .stApp .small-muted, .stApp [data-testid="stCaptionContainer"] {{ color: var(--p-muted) !important; }}
    .stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div, .stApp [data-baseweb="input"],
    .stApp [data-baseweb="textarea"], .stApp [data-baseweb="base-input"] {{ background-color: {field} !important; color: {t} !important; border-color: {border} !important; }}
    .stApp [data-baseweb="select"] *, .stApp [data-baseweb="input"] * {{ color: {t} !important; }}
    div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li, div[data-baseweb="menu"] {{ background-color: {field} !important; color: {t} !important; }}
    .stApp button p, .stApp button span {{ color: inherit; }}
    [data-testid="stAlert"] {{ background-color: {field} !important; border-left: 4px solid {primary}; }}
    """
    return css + COMPONENT_CSS
