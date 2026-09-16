import extra_streamlit_components as stx

from datetime import datetime, timedelta


COOKIE_NAME = "shobo_app_auth_token"


def get_cookie_manager():
    return stx.CookieManager(
        key="shobo_app_cookie"
    )


def get_token(cookie_manager):
    return cookie_manager.get(
        COOKIE_NAME
    )


def save_token(cookie_manager, token):
    print("Cookie保存開始")
    print("token:", token)

    result = cookie_manager.set(
        COOKIE_NAME,
        token,
        expires_at=datetime.now() + timedelta(days=90),
        path="/"
    )

    print("Cookie保存完了")

    return result


def delete_token(cookie_manager):
    try:
        token = cookie_manager.get(COOKIE_NAME)

        if token:
            cookie_manager.delete(COOKIE_NAME)

    except KeyError:
        pass