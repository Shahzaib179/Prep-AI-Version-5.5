"""Sidebar structure. Route names are the page names the app has always used (``routes`` in app.py); only the grouping is new."""
from __future__ import annotations

# (group label, [(route, material icon)])
STUDENT_NAV = [
    ("Main", [("Dashboard", "dashboard"), ("Today", "today")]),
    ("Learning", [("Learn", "menu_book"), ("Practice", "bolt"), ("Exam", "assignment"), ("Mock Test", "quiz"), ("Live Quiz", "podcasts"),
                  ("My Classes", "groups"), ("Published Quizzes", "publish")]),
    ("Gamification", [("Learning Games", "sports_esports"), ("Daily Challenge", "emoji_events"), ("Leaderboard", "leaderboard")]),
    ("Performance", [("Score Predictor", "speed"), ("Mistakes Diary", "error_outline"), ("History", "history")]),
    ("Study tools", [("AI Tutor", "smart_toy"), ("Voice Tutor", "mic"), ("Research Agent", "travel_explore"), ("Study Plan", "event_note"),
                     ("Merit Calculator", "calculate"), ("Path Finder", "alt_route")]),
    ("Other", [("Memory", "psychology"), ("Settings", "settings")]),
]
TUTOR_NAV = [("Tutor", [("Tutor Dashboard", "school")]), ("Account", [("Settings", "settings")])]


def groups(is_tutor: bool) -> list[tuple[str, list[tuple[str, str]]]]:
    return TUTOR_NAV if is_tutor else STUDENT_NAV


def routes(is_tutor: bool) -> list[str]:
    return [r for _, items in groups(is_tutor) for r, _ in items]


def default_page(is_tutor: bool) -> str:
    return "Tutor Dashboard" if is_tutor else "Dashboard"


def resolve(current: str | None, is_tutor: bool) -> str:
    """The page to show: the stored one if it is valid for this account, otherwise the home page. Accepts labels like 'My Classes (2)'."""
    name = (current or "").split(" (")[0]
    return name if name in routes(is_tutor) else default_page(is_tutor)


def label(route: str, pending_classes: int = 0) -> str:
    return f"{route} ({pending_classes})" if route == "My Classes" and pending_classes else route


def slug(route: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in route.lower())


def badge_css(route: str, count: int) -> str:
    """A red count pill on the right of one sidebar button (Streamlit button labels cannot hold HTML, so it is drawn with CSS). Empty when the count is 0."""
    n = int(count or 0)
    if n <= 0:
        return ""
    text = "99+" if n > 99 else str(n)
    s = slug(route)
    return (f'<style>[class*="st-key-nav_{s}"] button, [class*="st-key-navon_{s}"] button {{ position: relative; padding-right: 3rem !important; }}'
            f'[class*="st-key-nav_{s}"] button::after, [class*="st-key-navon_{s}"] button::after {{ content: "{text}"; position: absolute; right: .7rem; top: 50%; transform: translateY(-50%); '
            f'background: #E5383B; color: #fff; border-radius: 99px; font-size: .72rem; font-weight: 700; line-height: 1; padding: .22rem .5rem; min-width: 1.5rem; text-align: center; box-sizing: border-box; }}</style>')
