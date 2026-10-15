"""Small HTML building blocks for the redesigned interface (pure functions, no Streamlit; every piece of student text is escaped).

Colours come from CSS variables defined in theme.build_css, so the blocks follow the chosen accent colour and the light/dark themes.
"""
from __future__ import annotations

import base64
import functools
import math
from pathlib import Path
from html import escape as esc
from typing import Iterable

ASSETS = Path(__file__).resolve().parent / "assets"
GAUGE_SEGMENTS = ("#DC2626", "#F59E0B", "#EAB308", "#22C55E")   # low -> high


def badge(text: str, kind: str = "") -> str:
    return f'<span class="pp-badge {esc(kind)}">{esc(text)}</span>'


def empty(text: str) -> str:
    return f'<div class="pp-empty">{esc(text)}</div>'


def label(text: str) -> str:
    return f'<div class="pp-label">{esc(text)}</div>'


def topbar(page: str, name: str, chips: Iterable[str], subtitle: str = "", with_user: bool = True) -> str:
    """Breadcrumb + chips (+ the user chip unless ``with_user`` is False, in which case the page shows its own profile button beside it)."""
    chip_html = "".join(f'<span class="pp-chip">{esc(c)}</span>' for c in chips)
    user = ""
    if with_user:
        initial = esc((name or "?").strip()[:1].upper() or "?")
        user = f'<span class="pp-user"><span class="pp-avatar">{initial}</span><span>{esc(name)}<small>{esc(subtitle)}</small></span></span>'
    return (f'<div class="pp-topbar{"" if with_user else " bare"}"><div class="pp-crumb">Prep.AI &nbsp;/&nbsp; <b>{esc(page)}</b></div>'
            f'<div class="pp-chips">{chip_html}{user}</div></div>')


def greeting(name: str, line: str) -> str:
    return f'<div class="pp-greet"><h1>Assalam-o-Alaikum, {esc(name)}!</h1><p>{esc(line)}</p></div>'


@functools.lru_cache(maxsize=8)
def logo_uri(name: str = "logo_icon_256.png") -> str:
    """The logo as a data: URI so it can sit inside HTML blocks. Empty string if the asset is missing (the brand then shows text only)."""
    try:
        return "data:image/png;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode("ascii")
    except OSError:
        return ""


def sidebar_goal(title: str, big: str, small: str, pct: float | None = None) -> str:
    """Goal card. ``pct`` (0-100) draws a decorative progress bar; it is a plain bar, never a slider."""
    bar = f'<span class="g-bar"><i style="width:{max(0.0, min(100.0, pct)):.0f}%"></i></span>' if pct is not None else ""
    return f'<div class="pp-goal"><span class="g-label">{esc(title)}</span><span class="g-big">{esc(big)}</span><span class="g-small">{esc(small)}</span>{bar}</div>'


def brand() -> str:
    img = logo_uri()
    return f'<div class="pp-brand">{f"<img class=pp-logo src={chr(34)}{img}{chr(34)} alt={chr(34)}Prep.AI logo{chr(34)}>" if img else ""}<span class="pp-wm">Prep<em>.AI</em></span></div>'


def login_logo() -> str:
    img = logo_uri("logo_full.png")
    return f'<img class="pp-login-logo" src="{img}" alt="Prep.AI">' if img else '<div class="pp-brand" style="justify-content:center"><span class="pp-wm">Prep<em>.AI</em></span></div>'


def sidebar_header(goal_html: str) -> str:
    """Brand and goal card as ONE block: they cannot overlap each other or the navigation below."""
    return brand() + goal_html


def bar_row(title: str, right: str, pct: float | None, sub: str = "") -> str:
    """Labelled progress bar. pct None = no data (empty bar). Colour follows the same 75/60 thresholds as the mastery rings."""
    val = 0.0 if pct is None else max(0.0, min(100.0, pct))
    kind = "" if pct is None else "ok" if val >= 75 else "warn" if val >= 60 else "err"
    return (f'<div class="pp-barrow"><div class="top"><span>{esc(title)}</span><span>{esc(right)}</span></div>'
            f'<div class="pp-bar {kind}" role="img" aria-label="{esc(title)} {val:.0f}%"><i style="width:{val:.0f}%"></i></div>' + (f'<small>{esc(sub)}</small>' if sub else "") + '</div>')


def score_vs_target(score: float | None, target: int | None, scale: int) -> str:
    left = "–" if score is None else f"{score:.0f}"
    right = "Not set" if not target else f"{target}"
    if score is None:
        mid = "Your estimate appears after enough answers"
    elif not target:
        mid = f"out of {scale}. Set a target to see the gap"
    elif score >= target:
        mid = "Target reached on practice so far"
    else:
        mid = f"{target - score:.0f} points to go"
    return (f'<div class="pp-vs"><div class="a"><small>Your estimate</small><b>{left}</b></div><div class="m">{esc(mid)}</div>'
            f'<div class="c"><small>Your target</small><b>{esc(right)}</b></div></div>')


def trend_svg(points: list[tuple[str, float]], scale: int, target: int | None = None) -> str:
    """Line of the running estimate over the days it could be computed. Needs >= 2 points; the caller shows an empty state otherwise."""
    w, h, pl, pr, pt, pb = 320, 130, 30, 10, 10, 22
    n = len(points)
    xs = [pl + (w - pl - pr) * (i / (n - 1) if n > 1 else 0.5) for i in range(n)]
    ys = [pt + (h - pt - pb) * (1 - max(0.0, min(1.0, v / scale))) for _, v in points]
    grid = "".join(f'<line x1="{pl}" x2="{w - pr}" y1="{pt + (h - pt - pb) * f:.1f}" y2="{pt + (h - pt - pb) * f:.1f}" stroke="var(--p-border)" stroke-width="1"/>'
                   f'<text x="{pl - 4}" y="{pt + (h - pt - pb) * f + 3:.1f}" text-anchor="end" font-size="9" fill="var(--p-muted)">{scale * (1 - f):.0f}</text>' for f in (0, .5, 1))
    tline = ""
    if target:
        ty = pt + (h - pt - pb) * (1 - max(0.0, min(1.0, target / scale)))
        tline = f'<line x1="{pl}" x2="{w - pr}" y1="{ty:.1f}" y2="{ty:.1f}" stroke="var(--p-ok)" stroke-width="1.5" stroke-dasharray="4 3"/><text x="{w - pr}" y="{ty - 3:.1f}" text-anchor="end" font-size="9" fill="var(--p-ok)">target {target}</text>'
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="var(--p-primary)"/>' for x, y in zip(xs, ys))
    first, last = esc(points[0][0][5:]), esc(points[-1][0][5:])
    return (f'<div class="pp-trend"><svg viewBox="0 0 {w} {h}" role="img" aria-label="Estimated score trend from {first} to {last}">{grid}{tline}'
            f'<polyline points="{path}" fill="none" stroke="var(--p-primary)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>{dots}'
            f'<text x="{pl}" y="{h - 6}" font-size="9" fill="var(--p-muted)">{first}</text><text x="{w - pr}" y="{h - 6}" text-anchor="end" font-size="9" fill="var(--p-muted)">{last}</text></svg></div>')


def leaderboard_rows(rows: list[dict], me: dict | None = None, unit: str = "pts") -> str:
    """Ranked list. The current student's row is highlighted; if outside the shown rows it is appended after a gap."""
    def one(r: dict, forced_me: bool = False) -> str:
        rk = int(r["rank"])
        medal = f" m{rk}" if rk <= 3 else ""
        is_me = r.get("is_me") or forced_me
        return (f'<div class="r{" me" if is_me else ""}"><span class="rk{medal}">{rk}</span><div class="name">{esc(r["name"])}{" (you)" if is_me else ""}'
                f'<small>{r["correct"]} correct · {r["quizzes"]} quiz{"zes" if r["quizzes"] != 1 else ""}</small></div><span class="pts">{r["points"]} {esc(unit)}</span></div>')
    html = "".join(one(r) for r in rows)
    if me and not any(r.get("is_me") for r in rows):
        html += '<div class="r" style="justify-content:center"><span></span><small style="text-align:center">· · ·</small><span></span></div>' + one(me, True)
    return f'<div class="pp-lb">{html}</div>'


def finish_line(done: int, total: int, title: str, line: str) -> str:
    """Burgundy header of the daily checklist card with a progress track and one milestone per task."""
    total = max(0, total)
    pct = 100 * done / total if total else 0
    marks = "".join(f'<b class="{"on" if i < done else ""}" style="left:{100 * (i + 1) / total:.1f}%"></b>' for i in range(min(total, 10))) if total else ""
    return (f'<div class="pp-line"><span class="pp-done">{done}/{total} done</span><div class="pp-title">{esc(title)}</div><p>{esc(line)}</p>'
            f'<div class="pp-track"><i style="width:{pct:.1f}%"></i>{marks}</div></div>')


def task_row(title: str, detail: str, done: bool) -> str:
    return (f'<div class="pp-task"><span class="pp-tick {"on" if done else ""}">{"✓" if done else ""}</span>'
            f'<div><div class="t {"done" if done else ""}">{esc(title)}</div><div class="d">{esc(detail)}</div></div></div>')


def sch_text(title: str, detail: str, done: bool = False, badge: str = "") -> str:
    """Text of one Today's Schedule row (the tab icon and the Done / Open button are Streamlit widgets beside it)."""
    return f'<div class="pp-sch{" done" if done else ""}"><div class="t">{esc(title)}</div><div class="d">{esc(detail)}{" " + badge if badge else ""}</div></div>'


def row(title: str, sub: str = "", right: str = "") -> str:
    return f'<div class="pp-row"><div>{esc(title)}<small>{esc(sub)}</small></div><div>{right}</div></div>'


def ring(pct: float | None, short: str, size: int = 52) -> str:
    """Small progress ring. pct None = no data yet (grey ring and an en dash, never a fake 0%)."""
    r, c = 20, 2 * math.pi * 20
    val = 0 if pct is None else max(0.0, min(100.0, pct))
    colour = "var(--p-border)" if pct is None else "var(--p-ok)" if val >= 75 else "var(--p-warn)" if val >= 60 else "var(--p-err)"
    text = "–" if pct is None else f"{val:.0f}%"
    return (f'<div><svg width="{size}" height="{size}" viewBox="0 0 48 48" role="img" aria-label="{esc(short)} {esc(text)}">'
            f'<circle cx="24" cy="24" r="{r}" fill="none" stroke="var(--p-border)" stroke-width="5"/>'
            f'<circle cx="24" cy="24" r="{r}" fill="none" stroke="{colour}" stroke-width="5" stroke-linecap="round" stroke-dasharray="{c * val / 100:.1f} {c:.1f}" transform="rotate(-90 24 24)"/>'
            f'<text x="24" y="28" text-anchor="middle" font-size="11" font-weight="700" fill="var(--p-text)">{esc(text)}</text></svg>'
            f'<div class="n">{esc(short)}</div></div>')


def gauge(value: float | None, scale: int, low: float | None = None, high: float | None = None) -> str:
    """Semicircle gauge from 0 to ``scale``. value None draws an empty grey dial without a needle."""
    cx, cy, r = 110, 105, 80

    def pt(frac: float, rad: float) -> tuple[float, float]:
        a = math.pi * (1 - frac)
        return cx + rad * math.cos(a), cy - rad * math.sin(a)

    segs = []
    n = len(GAUGE_SEGMENTS)
    for i, col in enumerate(GAUGE_SEGMENTS):
        x1, y1 = pt(i / n, r)
        x2, y2 = pt((i + 1) / n, r)
        colour = col if value is not None else "var(--p-border)"
        segs.append(f'<path d="M{x1:.1f} {y1:.1f} A{r} {r} 0 0 1 {x2:.1f} {y2:.1f}" fill="none" stroke="{colour}" stroke-width="16" stroke-linecap="butt"/>')
    band = ""
    if value is not None and low is not None and high is not None and scale:
        x1, y1 = pt(max(0, low) / scale, r + 14)
        x2, y2 = pt(min(scale, high) / scale, r + 14)
        band = f'<path d="M{x1:.1f} {y1:.1f} A{r + 14} {r + 14} 0 0 1 {x2:.1f} {y2:.1f}" fill="none" stroke="var(--p-primary)" stroke-width="4" stroke-linecap="round" opacity=".55"/>'
    needle = ""
    if value is not None and scale:
        nx, ny = pt(max(0.0, min(1.0, value / scale)), r - 22)
        needle = (f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="var(--p-text)" stroke-width="3.5" stroke-linecap="round"/>'
                  f'<circle cx="{cx}" cy="{cy}" r="7" fill="var(--p-card)" stroke="var(--p-text)" stroke-width="3"/>')
    big = "–" if value is None else f"{value:.0f}"
    return (f'<div class="pp-gauge"><svg viewBox="0 0 220 150" width="100%" style="max-width:300px" role="img" aria-label="Estimated score {esc(big)} out of {scale}">'
            f'{"".join(segs)}{band}{needle}'
            f'<text x="{cx - r - 6}" y="{cy + 18}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--p-err)">0</text>'
            f'<text x="{cx + r + 6}" y="{cy + 18}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--p-ok)">{scale}</text>'
            f'<text x="{cx}" y="{cy + 40}" text-anchor="middle" font-size="30" font-weight="800" fill="var(--p-text)">{esc(big)}</text></svg></div>')


def qnav(n: int, answered: set[int]) -> str:
    """Question number chips; filled = answered. Each links to the question's anchor on the page."""
    return '<div class="pp-qnav">' + "".join(f'<a href="#q{i + 1}" class="{"on" if i in answered else ""}">{i + 1}</a>' for i in range(n)) + "</div>"


def qcard(number: int, text: str) -> str:
    """Question heading with an anchor (target of the question navigator)."""
    return f'<div class="pp-qcard" id="q{number}"><span class="pp-qnum">{number}</span><div class="pp-qtext">{esc(text)}</div></div>'
