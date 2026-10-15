"""Login screen pieces (pure HTML strings, no Streamlit): the Prep.AI brand panel with its own illustration, and the small brand line for the form side.

The illustration is drawn here (plain SVG shapes: a quiz paper, books, a graduation cap, a progress chart and an AI sparkle), so it belongs to Prep.AI and needs no
outside artwork. Colours come from the Prep.AI palette: burgundy (the logo), navy (the logo wordmark) and white.
"""
from __future__ import annotations

from html import escape as esc

import ui_kit as k

BRAND_NAME = "Prep.AI"
TAGLINE = "Adaptive Multi-Agent Learning Platform"
SUBLINE = "Log in to continue your MDCAT preparation"
FEATURES = ("Adaptive practice that learns your weak topics", "An AI tutor that remembers you", "Study plans, mock tests and a daily challenge")

NAVY, ROSE = "#182B49", "#F4C9D6"


def illustration() -> str:
    """A quiz paper with a ticked answer, a cap, books, a rising progress chart and an AI sparkle. Decorative: hidden from screen readers."""
    return f"""<svg class="lg-art" viewBox="0 0 520 360" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
  <circle cx="90" cy="90" r="70" fill="#fff" opacity=".07"/><circle cx="440" cy="250" r="95" fill="#fff" opacity=".07"/>
  <g transform="rotate(-4 260 180)">
    <rect x="165" y="42" width="200" height="262" rx="20" fill="#fff"/>
    <rect x="187" y="66" width="86" height="12" rx="6" fill="{NAVY}"/><rect x="187" y="86" width="140" height="8" rx="4" fill="#D9DCE3"/>
    <circle cx="198" cy="134" r="10" fill="none" stroke="{NAVY}" stroke-width="3"/><rect x="220" y="128" width="112" height="12" rx="6" fill="#D9DCE3"/>
    <circle cx="198" cy="176" r="10" fill="#92002D"/><path d="M193 176l4 4 8-9" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="220" y="170" width="96" height="12" rx="6" fill="{ROSE}"/>
    <circle cx="198" cy="218" r="10" fill="none" stroke="{NAVY}" stroke-width="3"/><rect x="220" y="212" width="120" height="12" rx="6" fill="#D9DCE3"/>
    <circle cx="198" cy="260" r="10" fill="none" stroke="{NAVY}" stroke-width="3"/><rect x="220" y="254" width="84" height="12" rx="6" fill="#D9DCE3"/>
  </g>
  <g transform="translate(330 14) rotate(8 70 40)"><path d="M70 6L140 34L70 62L0 34Z" fill="{NAVY}"/><path d="M28 50v26c0 10 20 18 42 18s42-8 42-18V50L70 66Z" fill="#0E1D38"/><path d="M136 38v38" stroke="#F2C94C" stroke-width="4" stroke-linecap="round"/><circle cx="136" cy="80" r="6" fill="#F2C94C"/></g>
  <g transform="translate(34 262)"><rect x="0" y="40" width="150" height="26" rx="6" fill="#fff"/><rect x="10" y="14" width="130" height="26" rx="6" fill="{ROSE}"/><rect x="20" y="-12" width="112" height="26" rx="6" fill="{NAVY}"/>
    <rect x="12" y="49" width="60" height="6" rx="3" fill="#92002D"/><rect x="22" y="23" width="44" height="6" rx="3" fill="#fff" opacity=".8"/><rect x="32" y="-3" width="40" height="6" rx="3" fill="#fff" opacity=".6"/></g>
  <g transform="translate(386 224)"><rect x="0" y="62" width="26" height="34" rx="5" fill="#fff" opacity=".55"/><rect x="38" y="38" width="26" height="58" rx="5" fill="#fff" opacity=".75"/><rect x="76" y="10" width="26" height="86" rx="5" fill="#fff"/>
    <path d="M6 44L50 22L88 -6" fill="none" stroke="{ROSE}" stroke-width="4" stroke-linecap="round" stroke-dasharray="1 9"/></g>
  <g fill="#fff"><path d="M118 150l8 20 20 8-20 8-8 20-8-20-20-8 20-8Z"/><path d="M420 150l5 12 12 5-12 5-5 12-5-12-12-5 12-5Z" opacity=".8"/><path d="M60 210l4 9 9 4-9 4-4 9-4-9-9-4 9-4Z" opacity=".6"/></g>
</svg>"""


def brand_row() -> str:
    """Small logo + wordmark for the top of the form side (always visible, also on phones where the brand panel is hidden)."""
    img = k.logo_uri()
    return (f'<div class="lg-brand">{f"<img src={chr(34)}{img}{chr(34)} alt={chr(34)}{BRAND_NAME} logo{chr(34)}>" if img else ""}'
            f'<span>Prep<em>.AI</em></span></div>')


def hero_panel() -> str:
    """The right-hand brand panel: white logo mark, welcome line, tagline, illustration and three promises."""
    img = k.logo_uri()
    mark = f'<img class="lg-mark" src="{img}" alt="">' if img else ""
    feats = "".join(f"<li>{esc(f)}</li>" for f in FEATURES)
    return (f'<div class="lg-hero">{mark}<h2><b>Welcome to</b><span>{esc(BRAND_NAME)}</span></h2><p class="lg-tag">{esc(TAGLINE)}</p><p class="lg-sub">{esc(SUBLINE)}</p>'
            f'{illustration()}<ul class="lg-feats">{feats}</ul></div>')
