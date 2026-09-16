import secrets

from db import (
    save_login_token,
    get_user_by_token,
    delete_login_token,
)


def create_session_token():
    """安全なランダム認証トークンを生成する"""
    return secrets.token_urlsafe(32)


def save_session_token(user_id, token):
    """認証トークンをDBに保存する"""
    save_login_token(user_id, token)


def get_user_from_token(token):
    """認証トークンからユーザーを取得する"""
    if not token:
        return None

    return get_user_by_token(token)


def delete_session_token(token):
    """認証トークンを無効化する"""
    if token:
        delete_login_token(token)