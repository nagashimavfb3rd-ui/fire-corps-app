import streamlit as st

st.set_page_config(
    page_title="長島第３分団出欠等管理アプリ",
    layout="centered"
)
import os
import uuid
from db import(
    authenticate_user_supabase,
    
    get_next_training_supabase,
    get_user_meal_option_supabase,
    get_user_attendance_supabase,
    save_attendance_supabase,
    save_meal_supabase,
    
    get_user_reward_summary_supabase,
    get_hose_reward_summary_supabase,
    
    change_password_supabase,
    
    save_login_token,
    get_user_by_token,
    delete_login_token
)
from utils.ui import show_toast
from datetime import datetime

# 各ページ読み込み
import views.trainings as trainings
import views.training_detail as training_detail
import views.members as members
import views.member_detail as member_detail
import views.units as units
import views.todos as todos
import views.handover as handover
import views.admin as admin
import views.my_reward as my_reward
import views.admin_reward as admin_reward

from streamlit_cookies_manager import EncryptedCookieManager

cookies = EncryptedCookieManager(
    prefix="shobo_app_",
    password="a8F!k29sL#pQzX7vN3mR@tY6uW"
)

if not cookies.ready():
    st.stop()

# =========================
# セッション初期化
# =========================
if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "login"

# =========================
# ログイン画面
# =========================
def login_page():
    st.title("🚒 長島第３分団出欠等管理ログイン")

    # ログインID保存
    saved_id = cookies.get("saved_login_id", "")

    login_id = st.text_input("ログインID", value=saved_id)
    password = st.text_input("パスワード", type="password")

    if st.button("ログイン", use_container_width=True):
        user = authenticate_user_supabase(login_id, password)

        if user:
            token = str(uuid.uuid4())
            save_login_token(user["id"], token)

            cookies["auth_token"] = token
            cookies["saved_login_id"] = login_id
            cookies.save()

            st.session_state.user = user
            st.session_state.page = "home"
            st.rerun()
        else:
            st.error("ログイン失敗")

def auto_login():
    token = cookies.get("auth_token")

    if not token:
        return False
    
    user = get_user_by_token(token)

    if user:
        st.session_state.user = user
        st.session_state.page = "home"
        return True

    return False

# =========================
# ログアウト
# =========================
def logout():
    token = cookies.get("auth_token")

    if token:
        # DB側のトークン削除
        delete_login_token(token)

    if "auth_token" in cookies:
        del cookies["auth_token"]
    cookies.save()

    st.session_state.user = None
    st.session_state.page = "login"
    st.rerun()


# =========================
# ホーム
# =========================
def home_page():
    st.title("🏠 ホーム")

    user = st.session_state.user
    user_id = user["id"]

    st.write("左上の＞＞ボタンでサイドメニューを開閉してページ遷移してください。")

    st.markdown("---")

    # =========================
    # ① 次回訓練
    # =========================
    next_training = get_next_training_supabase()
    
    st.markdown("## 🚒 次回訓練")

    if next_training:
        st.success(
            f"{next_training['date']}｜{next_training['title']}\n\n"
            f"📍 {next_training['location']}"
        )

        training_id = next_training["id"]
        event_type = next_training.get("event_type")
        meal_option = get_user_meal_option_supabase(training_id, user_id)

        st.markdown("---")
        st.markdown("### 行事出席回答状況")

        # =========================
        # 出欠ステータス取得
        # =========================
        status = get_user_attendance_supabase(training_id, user_id)

        if status == "present":
            st.success("✅ 出席予定")
        elif status == "absent":
            st.error("❌ 欠席予定")
        else:
            st.warning("⚠️ 未回答")

        # =========================
        # 出欠ボタン
        # =========================
        col1, col2 = st.columns(2)

        with col1:
            if st.button("出席", use_container_width=True):
                save_attendance_supabase(training_id, user_id, "present")
                st.rerun()

        with col2:
            if st.button("欠席", use_container_width=True):
                save_attendance_supabase(training_id, user_id, "absent")
                st.rerun()

        # =========================
        # 🍻 宴会・食事会ステータス
        # =========================
        if event_type in ["party", "meal"]:

            st.markdown("### 🍻 宴会・食事会回答状況")

            if meal_option == "join":
                st.success("🍻 参加")
            elif meal_option == "bento":
                st.info("🍱 弁当のみ")
            elif meal_option == "no":
                st.error("❌ 不参加")
            else:
                st.warning("❔ 未回答")

        col3, col4, col5, col6 = st.columns(4)

        if col3.button("参加", use_container_width=True):
            save_meal_supabase(training_id, user_id, "join")
            st.rerun()

        if col4.button("弁当のみ", use_container_width=True):
            save_meal_supabase(training_id, user_id, "bento")
            st.rerun()

        if col5.button("不参加", use_container_width=True):
            save_meal_supabase(training_id, user_id, "no")
            st.rerun()

        if col6.button("未定", use_container_width=True):
            save_meal_supabase(training_id, user_id, "none")
            st.rerun()

        # =========================
        # 残り日数
        # =========================
        st.markdown("---")

        training_date = datetime.strptime(next_training["date"], "%Y-%m-%d")
        days_left = (training_date - datetime.today()).days

        st.info(f"あと {days_left} 日")

        # =========================
        # 詳細ボタン
        # =========================
        if st.button("詳細を見る"):
            st.session_state.training_id = training_id
            st.session_state.page = "training_detail"
            st.rerun()
            
    else:
        st.info("予定されている訓練はありません")

    # =========================
    # ② 現在年度の報酬
    # =========================
    today = datetime.today()
    fiscal_year = today.year if today.month >= 4 else today.year - 1
    hose_count, hose_reward = get_hose_reward_summary_supabase(user_id, fiscal_year)

    data = get_user_reward_summary_supabase(user_id, fiscal_year)

    st.markdown("---")
    st.markdown("## 💰 今年度の報酬")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("実績", f"{data['actual_total']:,}円")

    with col2:
        st.metric("見込み", f"{data['estimated_total']:,}円")

    st.metric("ホース報酬", f"{hose_reward:,}円")

    # =========================
    # 合計（ホース込み）
    # =========================
    st.markdown("---")

    col3, col4 = st.columns(2)

    with col3:
        total_actual = data["actual_total"] + hose_reward
        st.metric("実績合計", f"{total_actual:,}円")

    with col4:
        total_estimated = data["estimated_total"] + hose_reward
        st.metric("見込合計", f"{total_estimated:,}円")

    st.markdown("---")

    st.subheader("パスワード変更")

    current_password = st.text_input("現在のパスワード", type="password")
    new_password = st.text_input("新しいパスワード", type="password")
    confirm_password = st.text_input("確認用", type="password")

    if st.button("変更する"):

        if not current_password or not new_password:
            st.error("入力してください")

        elif new_password != confirm_password:
            st.error("一致しません")

        elif len(new_password) < 6:
            st.error("6文字以上にしてください")

        else:
            success, msg = change_password_supabase(
                st.session_state.user["id"],
                current_password,
                new_password
            )

            if success:
                st.success(msg)
            else:
                st.error(msg)

    st.markdown("---")

    if st.button("ログアウト", use_container_width=True):
        logout()

# =========================
# サイドバー
# =========================
def sidebar_nav():
    st.sidebar.title("🚒 メニュー")

    user = st.session_state.user

    # =========================
    # 👤 ログイン情報を表示（追加ここ）
    # =========================
    if user:
        st.sidebar.markdown("---")
        st.sidebar.success(f"👤 {user['name']}")
        st.sidebar.caption(f"ログインID：{user.get('login_id')}")
        st.sidebar.caption(f"権限：{user.get('auth_role')}")
        st.sidebar.markdown("---")

    def nav(label, page_name, icon=""):
        current = st.session_state.page == page_name

        # 現在ページは押せない＋強調
        if current:
            st.sidebar.markdown(f"👉 **{icon} {label}**")
        else:
            if st.sidebar.button(f"{icon} {label}", use_container_width=True):
                st.session_state.page = page_name
                st.rerun()

    # -------------------------
    # 共通メニュー
    # -------------------------
    nav("ホーム", "home", "🏠")
    nav("訓練", "trainings", "🚒")
    nav("団員", "members", "👨‍🚒")
    nav("自治会", "units", "🏘")
    nav("報酬確認", "my_reward", "💰")

    st.sidebar.markdown("---")

    # -------------------------
    # 管理者のみ表示
    # -------------------------
    if user and user.get("auth_role") == "admin":
        st.sidebar.markdown("🔧 管理者")
        nav("報酬一覧", "admin_reward", "💰")
        nav("設定", "settings", "⚙️")
        nav("ToDo", "todos", "📝")
        nav("引継メモ", "handover", "📝")

        st.sidebar.markdown("---")

    # -------------------------
    # ログアウト
    # -------------------------
    if st.sidebar.button("🚪 ログアウト", use_container_width=True):
        logout()

# =========================
# ルーティング
# =========================
def router():
    page = st.session_state.page

    if st.session_state.user is None:
        login_page()
        return

    if page == "home":
        home_page()

    elif page == "trainings":
        trainings.main()

    elif page == "training_detail":
        training_detail.main()

    elif page == "members":
        members.main()
    
    elif page == "member_detail":
        member_detail.main()

    elif page == "my_reward":
        my_reward.main()

    elif page == "units":
        units.main()

    elif page == "todos":
        if st.session_state.user.get("auth_role") == "admin":
            todos.main()
        else:
            st.error("権限がありません")

    elif page == "handover":
        if st.session_state.user.get("auth_role") == "admin":
            handover.main()
        else:
            st.error("権限がありません")

    elif page == "settings":
        if st.session_state.user.get("auth_role") == "admin":
            admin.main()
        else:
            st.error("権限がありません")

    elif page == "admin_reward":
        if st.session_state.user.get("auth_role") == "admin":
            admin_reward.main()
        else:
            st.error("権限がありません")


# =========================
# メイン
# =========================
def main():
    show_toast()

    # =========================
    # 毎回自動ログインチェック
    # =========================
    if st.session_state.user is None:
        if auto_login():
            st.rerun()

    # =========================
    # 未ログインならログイン画面
    # =========================
    if st.session_state.user is None:
        login_page()
        return

    sidebar_nav()
    router()

main()