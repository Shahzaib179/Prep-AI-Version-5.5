"""Study plan as a weekly calendar: days are columns, hours run down the side, every session is a coloured block with its time.

Pure functions (no Streamlit). The plan itself is unchanged (a list of days, each with sessions that have subject, topic, minutes, activity, source);
this module only decides WHEN each session happens (one after another from the student's start time) and draws it.
Every piece of plan text comes from the AI or the student, so it is HTML-escaped here.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from html import escape as esc
from typing import Any

GAP_MIN = 10                 # rest between two sessions of the same day
WEEK = 7
MIN_BLOCK_PX = 34
WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
KIND_BY_WORD = (("revis", "Revision"), ("self-test", "Test"), ("test", "Test"), ("mcq", "Practice"), ("practi", "Practice"), ("quiz", "Practice"),
                ("read", "Study"), ("note", "Study"), ("learn", "Study"))
KIND_CLASS = {"Study": "k1", "Practice": "k2", "Revision": "k3", "Test": "k4"}


def kind_of(activity: str) -> str:
    a = (activity or "").lower()
    for word, kind in KIND_BY_WORD:
        if word in a:
            return kind
    return "Study"


def hhmm(minutes: int) -> str:
    minutes = max(0, min(24 * 60, int(minutes)))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse_start(text: str, default: int = 17 * 60) -> int:
    """'17:30' -> 1050 minutes after midnight; anything unusable gives the default."""
    try:
        h, m = str(text).split(":")[:2]
        v = int(h) * 60 + int(m)
        return v if 0 <= v < 24 * 60 else default
    except (ValueError, TypeError):
        return default


def layout(plan: list[dict[str, Any]], first_day: date, start_min: int = 17 * 60, gap: int = GAP_MIN) -> list[dict[str, Any]]:
    """Day by day: date, weekday and the sessions with start/end minutes. Sessions follow each other from ``start_min`` and never overlap.
    If a day is too long to end before midnight it is moved earlier, never cut."""
    days = []
    for n, d in enumerate(plan or []):
        if not isinstance(d, dict):
            continue
        sessions = [s for s in (d.get("sessions") or []) if isinstance(s, dict)]
        durations = []
        for s in sessions:
            try:
                durations.append(max(5, int(float(s.get("minutes", 30)))))
            except (TypeError, ValueError):
                durations.append(30)
        total = sum(durations) + gap * max(0, len(durations) - 1)
        t = max(0, min(start_min, 24 * 60 - total))
        events = []
        for s, dur in zip(sessions, durations):
            events.append({"subject": str(s.get("subject", "")), "topic": str(s.get("topic", "")), "activity": str(s.get("activity", "")), "source": str(s.get("source", "") or ""),
                           "minutes": dur, "start": t, "end": min(24 * 60, t + dur), "kind": kind_of(str(s.get("activity", "")))})
            t += dur + gap
        dt = first_day + timedelta(days=n)
        days.append({"label": str(d.get("day") or f"Day {n + 1}"), "date": dt, "weekday": WEEKDAYS[dt.weekday()], "events": events, "minutes": sum(durations)})
    return days


def weeks(days: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    return [days[i:i + WEEK] for i in range(0, len(days), WEEK)]


def _scale(chunk: list[dict[str, Any]]) -> tuple[int, int, int]:
    """(first hour, last hour, pixels per hour) so that the shortest session is still readable."""
    ev = [e for d in chunk for e in d["events"]]
    if not ev:
        return 8, 18, 64
    lo = max(0, min(e["start"] for e in ev) // 60 - 1)
    hi = min(24, (max(e["end"] for e in ev) + 59) // 60 + 1)
    if hi - lo < 6:
        hi = min(24, lo + 6)
        lo = max(0, hi - 6)
    shortest = min(e["minutes"] for e in ev)
    return lo, hi, int(max(64, min(140, MIN_BLOCK_PX * 60 / max(shortest, 15))))


def to_html(chunk: list[dict[str, Any]], now: datetime | None = None) -> str:
    """One calendar (up to 7 days). ``now`` (local time) draws the red 'now' line in today's column and marks later sessions 'Planned'."""
    if not chunk:
        return ""
    lo, hi, px = _scale(chunk)
    height = (hi - lo) * px
    now = now or datetime.now()
    head = "".join(f'<div class="cal-dh{" today" if d["date"] == now.date() else ""}"><span>{d["weekday"]}</span><b>{d["date"].day}</b></div>' for d in chunk)
    hours = "".join(f'<div class="cal-hr" style="top:{(h - lo) * px}px">{h:02d}:00</div>' for h in range(lo, hi + 1) if (h - lo) * px < height + 1)
    lines = "".join(f'<i class="cal-line" style="top:{(h - lo) * px}px"></i>' for h in range(lo, hi))
    cols = []
    for d in chunk:
        blocks = []
        for e in d["events"]:
            top = (e["start"] - lo * 60) * px / 60
            h = max(MIN_BLOCK_PX - 4, (e["end"] - e["start"]) * px / 60 - 4)
            is_today = d["date"] == now.date()
            future = d["date"] > now.date() or (is_today and e["end"] > now.hour * 60 + now.minute)
            sub = esc(e["subject"]) + (", " if e["subject"] else "") + f'{hhmm(e["start"])} - {hhmm(e["end"])}'
            src = f'<small class="src">{esc(e["source"])}</small>' if e["source"] and h > 84 else ""
            short = h < 62                       # a short block shows only its title on one line (the dashed border already says "planned"); the rest is in the tooltip
            tip = f'{esc(e["topic"])} - {esc(e["activity"])} ({e["minutes"]} min, {hhmm(e["start"])} - {hhmm(e["end"])})'
            blocks.append(f'<div class="cal-ev {KIND_CLASS.get(e["kind"], "k1")}{" planned" if future else ""}{" short" if short else ""}" style="top:{top:.0f}px;height:{h:.0f}px" title="{tip}">'
                          f'{"<em>Planned</em>" if future and not short else ""}<b>{esc(e["topic"])}</b>' + (f'<span>{hhmm(e["start"])} - {hhmm(e["end"])}</span>' if short and h >= 46 else "" if short else f'<span>{sub}</span><small>{esc(e["activity"] or e["kind"])}</small>{src}') + '</div>')
        nowline = ""
        if d["date"] == now.date():
            m = now.hour * 60 + now.minute
            if lo * 60 <= m <= hi * 60:
                nowline = f'<i class="cal-now" style="top:{(m - lo * 60) * px / 60:.0f}px"></i>'
        cols.append(f'<div class="cal-col">{"".join(blocks)}{nowline}</div>')
    return (f'<div class="pp-cal" style="--n:{len(chunk)}" role="img" aria-label="Study plan calendar"><div class="cal-scroll"><div class="cal-head"><div class="cal-corner"></div>{head}</div>'
            f'<div class="cal-body" style="height:{height}px"><div class="cal-hours">{hours}</div><div class="cal-grid">{lines}{"".join(cols)}</div></div></div></div>')


def legend() -> str:
    return '<div class="cal-legend"><span class="k1">Study</span><span class="k2">Practice</span><span class="k3">Revision</span><span class="k4">Test</span><span class="pl">Planned</span></div>'


def day_summary(day: dict[str, Any]) -> str:
    h, m = divmod(int(day["minutes"]), 60)
    return f'{day["label"]} · {day["weekday"].title()} {day["date"].day} · {len(day["events"])} session(s) · {h}h {m:02d}m'


# ------------------------------------------------------------------ calendar export (.ics, opens in Google / Apple / Outlook calendar)
def _ics_text(v: str) -> str:
    return str(v).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def _fold(line: str) -> list[str]:
    """RFC 5545: lines are at most 75 octets; continuation lines start with one space."""
    raw, out = line.encode("utf-8"), []
    while len(raw) > 75:
        cut = 75
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:      # never split a multi-byte character
            cut -= 1
        out.append(raw[:cut].decode("utf-8"))
        raw = b" " + raw[cut:]
    out.append(raw.decode("utf-8"))
    return out


def to_ics(days: list[dict[str, Any]], name: str = "Prep.AI study plan", stamp: datetime | None = None) -> str:
    """One VEVENT per session, in the student's local (floating) time, so every calendar app shows it at the same clock time."""
    stamp = stamp or datetime.utcnow()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Prep.AI//Study plan//EN", "CALSCALE:GREGORIAN", f"X-WR-CALNAME:{_ics_text(name)}"]
    for d in days:
        for n, e in enumerate(d["events"]):
            day = d["date"].strftime("%Y%m%d")
            lines += ["BEGIN:VEVENT", f"UID:prepai-{day}-{n}-{hashlib.sha1(f"{e['topic']}|{e['start']}".encode()).hexdigest()[:8]}@prep-ai",
                      f"DTSTAMP:{stamp.strftime('%Y%m%dT%H%M%SZ')}",
                      f"DTSTART:{day}T{e['start'] // 60:02d}{e['start'] % 60:02d}00", f"DTEND:{day}T{min(e['end'], 1439) // 60:02d}{min(e['end'], 1439) % 60:02d}00",
                      f"SUMMARY:{_ics_text((e['subject'] + ': ' if e['subject'] else '') + e['topic'])}",
                      f"DESCRIPTION:{_ics_text(e['activity'] + (' | ' + e['source'] if e['source'] else ''))}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for ln in lines for part in _fold(ln)) + "\r\n"
