"""Profile menu in the top bar: name, ID, email, change password and log out (replaces the sign-in details that used to sit in the sidebar)."""
from __future__ import annotations

from typing import Callable

import streamlit as st

import auth
from auth import AuthError


def _password_form(user_id: int) -> None:
    with st.expander("Change password"):
        with st.form("change_pw_form", clear_on_submit=True):
            old_pw = st.text_input("Current password", type="password", key="cp_old")
            new_pw = st.text_input("New password", type="password", key="cp_new")
            new_pw2 = st.text_input("Repeat new password", type="password", key="cp_new2")
            do_change = st.form_submit_button("Update password")
        if do_change:
            if new_pw != new_pw2:
                st.error("The new passwords do not match.")
                return
            try:
                auth.change_password(int(user_id), old_pw, new_pw)
                st.session_state.pop("auth_token", None)
                st.success("Password updated. Other devices were signed out.")
            except AuthError as exc:
                st.error(str(exc))


def render_menu(name: str, student_id: str, email: str, is_tutor: bool, user_id: int | None, on_logout: Callable[[], None]) -> None:
    """A popover opened from the user button. Students see their ID; tutors see their role (a tutor has no student ID to show)."""
    label = (name or "Account").strip() or "Account"
    with st.popover(label, icon=":material/account_circle:", use_container_width=True, key="profile_menu"):
        st.markdown(f"**{label}**")
        st.caption("Tutor account" if is_tutor else "Student account")
        st.markdown(f"**Name:** {label}")
        if not is_tutor:
            st.markdown(f"**Student ID:** `{student_id}`")
        if email:
            st.markdown(f"**Email:** {email}")
        if user_id:
            _password_form(user_id)
        if st.button("Log out", key="profile_logout", icon=":material/logout:", use_container_width=True):
            on_logout()
