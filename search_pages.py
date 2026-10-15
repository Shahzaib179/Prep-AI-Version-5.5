"""Search results panel (v5.6). The input lives in the top bar (app.py, key ``global_search``); this draws the matches under it."""
from __future__ import annotations

import streamlit as st

import search
from ui import go_to

KEY = "global_search"


def _open(route: str) -> None:
    """Button callback: open the page and empty the search box (callbacks run before widgets are drawn, so setting the widget value here is allowed)."""
    st.session_state[KEY] = ""
    go_to(route)


def _clear() -> None:
    st.session_state[KEY] = ""


def render_results(user_id: str, is_tutor: bool) -> None:
    query = (st.session_state.get(KEY) or "").strip()
    if not query:
        return
    if len(query) < 2:
        st.caption("Type at least 2 letters to search.")
        return
    found = search.search(query, user_id, is_tutor)
    with st.container(border=True, key="search_panel"):
        head, clear = st.columns([6, 1], vertical_alignment="center")
        head.markdown(f'<div class="pp-sr-head">{len(found)} result(s) for “{query.replace("<", "&lt;")}”</div>', unsafe_allow_html=True)
        clear.button("Clear", key="search_clear", on_click=_clear, use_container_width=True)
        if not found:
            st.caption("Nothing found. Try a page name (for example Mock Test), a subject, a topic or a class name.")
        for n, r in enumerate(found):
            icon, text, btn = st.columns([1, 9, 2.4], vertical_alignment="center", gap="small")
            icon.markdown(f":material/{r['icon']}:")
            text.markdown(f'<div class="pp-sr"><div class="t">{r["title"].replace("<", "&lt;")}</div><div class="d">{r["kind"]} · {r["detail"].replace("<", "&lt;")}</div></div>', unsafe_allow_html=True)
            btn.button("Open", key=f"search_open_{n}", on_click=_open, args=(r["route"],), use_container_width=True)
