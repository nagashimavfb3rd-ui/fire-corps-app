from db import authenticate_user_supabase


def authenticate_user(login_id, password):
    """ログインIDとパスワードでユーザー認証する"""
    return authenticate_user_supabase(login_id, password)