
import streamlit as st


def is_admin():
    user = st.session_state.get("user")
    return bool(user and user.get("auth_role") == "admin")
