import streamlit as st


def init_session():
    """セッション状態を初期化する"""
    if "user" not in st.session_state:
        st.session_state.user = None

    if "page" not in st.session_state:
        st.session_state.page = "login"


def set_user(user):
    """ログインユーザーをセッションに保存する"""
    st.session_state.user = user


def get_user():
    """現在のログインユーザーを取得する"""
    return st.session_state.get("user")


def clear_user():
    """ログインユーザーをセッションから削除する"""
    st.session_state.user = None
    st.session_state.page = "login"