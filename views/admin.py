import streamlit as st
import sqlite3
import os
from datetime import datetime
from db import (
    create_user_supabase,
    generate_login_id_supabase,
    get_users_supabase,
    get_units_supabase,
    create_unit_supabase,
    update_unit_supabase,
    delete_unit_supabase,
    get_fields_supabase,
    create_field_supabase,
    update_field_order_supabase,
    delete_field_supabase,
    get_training_types_supabase,
    create_training_type_supabase,
    delete_training_type_supabase,
    update_user_role_supabase,
    update_role_with_history_supabase,
    get_role_history_supabase,
    update_role_history_supabase,
    delete_role_history_supabase,
    get_role_rewards_supabase,
    update_role_reward_supabase,
    get_trainings_supabase,
    create_training_supabase,
    update_training_supabase,
    delete_training_supabase,
    create_training_hose_supabase,
    copy_training_supabase,
    update_training_targets_supabase,
    get_training_target_ids_supabase,
    get_training_target_names_supabase,
    create_password_hash
)
from utils.ui import show_toast, set_toast


def get_users():
    return get_users_supabase()

# =========================
# 権限チェック
# =========================
def is_admin():
    return (
        "user" in st.session_state and
        st.session_state.user and
        st.session_state.user["auth_role"] == "admin"
    )


# =========================
# 訓練管理機能
# =========================
# 本体
def training_admin_panel():
    st.subheader("🚒 訓練管理")

    # =========================
    # 新規作成
    # =========================
    if "show_create" not in st.session_state:
        st.session_state.show_create = False

    col1, col2 = st.columns([1, 3])

    if col1.button(
        "➕ 新規作成を開く" if not st.session_state.show_create else "❌ 閉じる",
        use_container_width=True
    ):
        st.session_state.show_create = not st.session_state.show_create
        st.rerun()

    if st.session_state.show_create:
        st.markdown("### ➕ 新規作成")

        title = st.text_input("訓練名", value="ポンプ点検")
        date = st.date_input("日付")
        start_time = st.text_input("開始時間", value="9:00")
        end_time = st.text_input("終了時間", value="12:00")
        location = st.text_input("場所", value="○○○")
        reward = st.number_input("報酬", value=2000)
        meeting_point = st.text_input("集合場所", value="詰所")
        meeting_time = st.text_input("集合時間", value="8:30")
        uniform = st.text_input("服装", value="活動服・編上靴・耐切創手袋・ヘルメット")

        meal_type = st.selectbox(
            "食事",
            ["none", "meal", "party"]
        )

        status = st.selectbox(
            "ステータス",
            ["planned", "done", "canceled"]
        )
    
        required_members = st.number_input(
            "必要人数",
            value=10,
            key="training_required_members"
        )
    
        target_roles = st.multiselect(
            "参加対象者",
            ["団員", "副分団長", "分団長"]
        )
        
        users = get_users()
        user_map = {u["name"]: u["id"] for u in users}
        
        selected_users = st.multiselect(
            "個別指定",
            list(user_map.keys()),
            key="create_users"
        )
        
        target_user_ids = [user_map[name] for name in selected_users]

        note = st.text_area("メモ", key="create_note")

        if st.button("作成", key="create_training", use_container_width=True):
            create_training_supabase(
                {
                    "title": title,
                    "date": str(date),
                    "start_time": start_time,
                    "end_time": end_time,
                    "location": location,
                    "meeting_point": meeting_point,
                    "meeting_time": meeting_time,
                    "uniform": uniform,
                    "reward_amount": reward,
                    "status": status,
                    "created_by": st.session_state.user["id"],
                    "note": note,
                    "event_type": meal_type,
                    "required_members": required_members,
                    "target_roles": ",".join(target_roles),
                },
                target_user_ids
            )

            st.success("作成しました")

            # 👇 作成後に閉じる
            st.session_state.show_create = False

            st.rerun()

    # =========================
    # 一覧
    # =========================
    st.markdown("---")
    st.subheader("📋 訓練一覧")

    trainings = get_trainings_supabase()

    for t in trainings:
        st.markdown("---")

        # 編集中かどうか判定
        if st.session_state.get("edit_training") == t["id"]:
            t = dict(t)
            
            st.info("編集中")

            title = st.text_input("訓練名", value=t["title"], key=f"edit_title_{t['id']}")
            
            raw_date = datetime.strptime(t["date"], "%Y-%m-%d").date()
            
            date = st.date_input(
                "日付",
                value=raw_date,
                min_value=datetime(1900, 1, 1).date(),
                max_value=datetime(2033, 4, 1).date(),
                key=f"edit_date_{t['id']}"
            )

            start_time = st.text_input("開始時間", value=t["start_time"], key=f"edit_start_{t['id']}")
            end_time = st.text_input("終了時間", value=t["end_time"], key=f"edit_end_{t['id']}")
            location = st.text_input("場所", value=t["location"], key=f"edit_loc_{t['id']}")
            meeting_point = st.text_input("集合場所", value=t["meeting_point"] or "", key=f"edit_meet_{t['id']}")
            meeting_time = st.text_input("集合時間", value=t["meeting_time"] or "", key=f"edit_meet_time_{t['id']}")
            uniform = st.text_input("服装", value=t["uniform"] or "", key=f"edit_uniform_{t['id']}")

            reward = st.number_input("報酬", value=t["reward_amount"], key=f"edit_reward_{t['id']}")
            
            status_list = ["planned", "done", "canceled"]

            status = st.selectbox(
                "ステータス",
                status_list,
                index=status_list.index(t["status"]) if t["status"] in status_list else 0,
                key=f"edit_status_{t['id']}"
            )
            
            event_list = ["none", "meal", "party"]
            
            event_type = st.selectbox(
                "食事",
                event_list,
                index=event_list.index(t["event_type"]) if t["event_type"] in event_list else 0,
                key=f"edit_event_{t['id']}"
            )
            required_members = st.number_input(
                "必要人数",
                value=t.get("required_members") or 0,
                key=f"edit_req_{t['id']}"
            )
            options = ["団員", "副分団長", "分団長"]

            roles_str = t.get("target_roles") or ""
            default_roles = [r for r in roles_str.split(",") if r in options]

            target_roles = st.multiselect(
                "参加対象者",
                options,
                default=default_roles,
                key=f"edit_target_{t['id']}"
            )
            
            users = get_users()
            user_map = {u["name"]: u["id"] for u in users}
            
            # 現在の対象ユーザー取得（関数がまだ無いので後で追加）
            current_ids = get_training_target_ids_supabase(t["id"])
            
            default_users = [name for name, uid in user_map.items() if uid in current_ids]
            
            selected_users = st.multiselect(
                "個別指定",
                list(user_map.keys()),
                default=default_users,
                key=f"edit_users_{t['id']}"
            )
            
            target_user_ids = [user_map[name] for name in selected_users]
            
            note = st.text_area(
                "メモ",
                value=t["note"] or "",
                key=f"edit_note_{t['id']}"
            )
            
            col1, col2 = st.columns(2)
            
            if col1.button("更新", key=f"update_{t['id']}"):
                update_training_supabase(t['id'], {
                    "title": title,
                    "date": str(date),
                    "start_time": start_time,
                    "end_time": end_time,
                    "location": location,
                    "meeting_point": meeting_point,
                    "meeting_time": meeting_time,
                    "uniform": uniform,
                    "reward_amount": reward,
                    "status": status,
                    "event_type": event_type,
                    "required_members": required_members,
                    "target_roles": ",".join(target_roles),
                    "note": note
                })
                
                update_training_targets_supabase(t['id'], target_user_ids)

                st.success("更新しました")
                del st.session_state.edit_training
                st.rerun()

            if col2.button("キャンセル", key=f"cancel_{t['id']}"):
                del st.session_state.edit_training
                st.rerun()
        else:
            # 通常表示
            st.write(f"📌 {t['title']}")
            st.write(f"📅 {t['date']} {t['start_time']}〜{t['end_time']}")
            st.write(f"📍 {t['location']}")
            st.write(f"💰 {t['reward_amount']}円")
            names = get_training_target_names_supabase(t["id"])
            if names:
                st.write("👤 対象者:", ", ".join(names))
                
            col1, col2, col3 = st.columns(3)
                
            if col1.button("コピー", key=f"copy_{t['id']}"):
                copy_training_supabase(t)
                st.rerun()
                
            if col2.button("削除", key=f"del_{t['id']}"):
                delete_training_supabase(t["id"])
                st.rerun()
                
            if col3.button("編集", key=f"edit_{t['id']}"):
                st.session_state.edit_training = t["id"]
                st.rerun()


# =========================
# ユーザー追加
# =========================
def add_user_panel():
    st.subheader("➕ 団員追加")

    login_id = generate_login_id_supabase()
    st.text_input("ログインID", value=login_id, disabled=True)
    name = st.text_input("名前")
    password = st.text_input("初期パスワード", type="password")

    role = st.selectbox("役職", ["団員", "副分団長", "分団長"])
    auth_role = st.selectbox("権限", ["user", "admin"])

    units = get_units_supabase()
    unit_map = {str(u["name"]): u["id"] for u in units}
    unit_name = st.selectbox("自治会", list(unit_map.keys()))

    birth_date = st.date_input(
        "生年月日",
        value=datetime(1990, 1, 1).date(),
        min_value=datetime(1900, 1, 1).date(),
        max_value=datetime.today().date()
    )
    join_date = st.date_input(
        "入団日",
        value=datetime(2026, 4, 1).date(),  # ← 適当な初期値
        min_value=datetime(1900, 1, 1).date(),
        max_value=datetime.today().date()
    )
    leave_date = st.date_input(
        "退団日（未入力なら在籍中）",
        value=None,
        min_value=datetime(1900, 1, 1).date(),
        max_value=datetime.today().date()
    )

    address = st.text_input("住所")
    phone = st.text_input("電話")
    email = st.text_input("メール")

    license_type = st.text_input("免許")
    
    if st.button("作成", key="create_user"):
        try:
            password_hash, salt = create_password_hash(password)
            
            create_user_supabase({
                "login_id": login_id,
                "name": name,
                "role": role,
                "auth_role": auth_role,
                "unit_id": unit_map[unit_name],
                "birth_date": str(birth_date),
                "join_date": str(join_date),
                "leave_date": str(leave_date) if leave_date else None,
                "address": address,
                "phone": phone,
                "email": email,
                "license_type": license_type,
                "password_hash": password_hash,
                "salt": salt
            })

            set_toast(f"{name} を追加しました", "success")

            st.rerun()

        except Exception as e:
            set_toast(f"作成失敗: {e}", "error")
            st.rerun()


# =========================
# UI：役員交代機能
# =========================
def user_admin_panel():
    st.subheader("👥 役員交代機能")
    st.write("アプリ管理権限はadminならアプリをフル機能で利用可能、userは制限あり")

    users = get_users()

    for u in users:
        st.markdown("---")
        st.write(f"👤 {u['name']}")

        col1, col2 = st.columns(2)

        with col1:
            new_auth = st.selectbox(
                "アプリ管理権限",
                ["user", "admin"],
                index=0 if u["auth_role"] == "user" else 1,
                key=f"auth_{u['id']}"
            )

        with col2:
            new_role = st.selectbox(
                "役職",
                ["団員", "副分団長", "分団長"],
                index=["団員", "副分団長", "分団長"].index(u["role"]) if u["role"] in ["団員","副分団長","分団長"] else 0,
                key=f"role_select_{u['id']}"
            )
        
        change_date = st.date_input(
            "交代日",
            value=datetime.today(),
            key=f"date_{u['id']}"
        )

        if st.button("更新", key=f"update_user_{u['id']}", use_container_width=True):
            
            try:
                # 権限はそのまま更新
                update_user_role_supabase(u["id"], new_auth)        
                
                # 役職は専用関数で処理
                update_role_with_history_supabase(
                    u["id"],
                    new_role,
                    str(change_date)
                )
                
                # ★トースト表示用にセット
                set_toast(f"{u['name']}：{u['role']} → {new_role}", "update")
                st.rerun()
            
            except Exception as e:
                set_toast(f"更新失敗: {e}", "error")
                st.rerun()


# =========================
# UI：自治会編集
# =========================
def unit_admin_panel():
    st.subheader("🏘 自治会管理")

    #　一覧
    units = get_units_supabase()

    for u in units:
        st.markdown("---")

        new_name = st.text_input(
            "自治会名",
            value=u["name"],
            key=f"unit_{u['id']}"
        )
        
        required_members = st.number_input(
            "必要人数",
            value=u["required_members"] or 0,
            key=f"req_{u['id']}"
        )

        leader_name = st.text_input(
            "自治会長名",
            value=u["leader_name"] or "",
            key=f"leader_{u['id']}"
        )
        
        leader_phone = st.text_input(
            "電話",
            value=u["leader_phone"] or "",
            key=f"phone_{u['id']}"
        )
        
        leader_term = st.number_input(
            "任期",
            value=u["leader_term"] or 0,
            key=f"term_{u['id']}"
        )
        
        leader_start_date = st.date_input(
            "就任日",
            value=datetime.strptime(u["leader_start_date"], "%Y-%m-%d") if u["leader_start_date"] else None,
            key=f"start_{u['id']}"
        )
        
        col1, col2 = st.columns(2)

        # 更新
        if col1.button("更新", key=f"update_unit_{u['id']}"):
            update_unit_supabase(u["id"], {
                "name": new_name,
                "required_members": required_members,
                "leader_name": leader_name,
                "leader_phone": leader_phone,
                "leader_term": leader_term,
                "leader_start_date": str(leader_start_date) if leader_start_date else None
            })
            set_toast("自治会を更新しました", "update")
            st.rerun()

        # 削除
        if col2.button("削除", key=f"delete_unit_{u['id']}"):
            try:
                delete_unit_supabase(u["id"])
                set_toast("自治会を削除しました", "delete")
                st.rerun()
            except Exception as e:
                st.warning(str(e))
                st.rerun()

    # 追加画面
    st.markdown("---")

    st.markdown("### ➕ 自治会追加")

    new_unit_name = st.text_input("自治会名", key="new_unit")
    required_members = st.number_input(
        "必要人数",
        value=0,
        key="new_unit_required"
    )
    leader_name = st.text_input("自治会長名")
    leader_phone = st.text_input("自治会長電話")
    leader_term = st.number_input("任期（年）", value=0)
    leader_start_date = st.date_input("就任日",value=None)

    if st.button("追加", key="add_unit", use_container_width=True):
        if not new_unit_name:
            st.error("自治会名を入力してください")
            return

        create_unit_supabase({
            "name": new_unit_name,
            "required_members": required_members,
            "leader_name": leader_name,
            "leader_phone": leader_phone,
            "leader_term": leader_term,
            "leader_start_date": str(leader_start_date) if leader_start_date else None
        })
        st.success("追加しました")
        st.rerun()

# =========================
# UI：役職履歴（表示のみ）
# =========================
def role_history_panel():
    st.subheader("📜 役職履歴")
    
    role_filter = st.radio(
        "役職フィルタ",
        ["すべて", "分団長", "副分団長"],
        horizontal=True
    )

    history = get_role_history_supabase(role_filter)

    for h in history:
        st.markdown("---")

        # =========================
        # 編集モード判定
        # =========================
        if st.session_state.get("edit_role_history") == h["id"]:
            st.info("編集中")

            role = st.selectbox(
                "役職",
                ["分団長", "副分団長"],
                index=0 if h["role"] == "分団長" else 1,
                key=f"edit_role_{h['id']}"
            )

            start_date = st.date_input(
                "開始日",
                value=datetime.strptime(h["start_date"], "%Y-%m-%d"),
                key=f"edit_start_{h['id']}"
            )

            end_date = st.date_input(
                "終了日（未入力可）",
                value=datetime.strptime(h["end_date"], "%Y-%m-%d") if h["end_date"] else None,
                key=f"edit_end_{h['id']}"
            )

            col1, col2, col3 = st.columns(3)

            # 更新
            if col1.button("更新", key=f"update_hist_{h['id']}"):
                update_role_history_supabase(
                    h["id"],
                    role,
                    str(start_date),
                    str(end_date) if end_date else None
                )
                st.success("更新しました")
                del st.session_state.edit_role_history
                st.rerun()

            # 削除
            if col2.button("削除", key=f"delete_hist_{h['id']}"):
                delete_role_history_supabase(h["id"])
                st.success("削除しました")
                st.rerun()

            # キャンセル
            if col3.button("キャンセル", key=f"cancel_hist_{h['id']}"):
                del st.session_state.edit_role_history
                st.rerun()

        else:
            # =========================
            # 通常表示
            # =========================
            st.write(f"👤 {h['users']['name']}")
            end = h['end_date'] if h['end_date'] else "現在"
            st.write(f"🎖 {h['role']}　📅 {h['start_date']} 〜 {end}")

            col1, col2 = st.columns(2)

            # 編集ボタン
            if col1.button("編集", key=f"edit_hist_{h['id']}"):
                st.session_state.edit_role_history = h["id"]
                st.rerun()

            # 削除ボタン（即削除したい場合）
            if col2.button("削除", key=f"del_hist_{h['id']}"):
                delete_role_history_supabase(h["id"])
                st.success("削除しました")
                st.rerun()

# =========================
# UI：項目管理
# =========================
def field_admin_panel():
    st.subheader("➕ 団員項目管理")

    st.markdown("### 項目追加")

    field_name = st.text_input("項目名（例：資格、血液型）")

    field_type = st.selectbox(
        "入力タイプ",
        ["text", "number", "date"]
    )
    
    sort_order = st.number_input(
        "表示順（小さいほど上）",
        value=0,
        step=1
    )

    if st.button("➕ 追加", key="add_field", use_container_width=True):

        if not field_name:
            st.error("項目名を入力してください")
            return

        create_field_supabase(
            field_name,
            field_type,
            sort_order
        )

        st.success(f"「{field_name}」を追加しました")
        st.rerun()

    # =========================
    # 現在の項目一覧
    # =========================
    st.markdown("---")
    st.subheader("📋 現在の項目")

    fields = get_fields_supabase()

    for f in fields:
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.write(f"• {f['field_name']}")
        
        with col2:
            new_order = st.number_input(
                "順番",
                value=f["sort_order"],
                key=f"sort_{f['id']}"
            )
            
            if new_order != f["sort_order"]:
                update_field_order_supabase(f["id"], new_order)
                
                st.rerun()    

        with col3:
            if st.button("削除", key=f"del_field_{f['id']}"):
                delete_field_supabase(f["id"])
                st.success("削除しました")
                st.rerun()

# =========================
# 訓練種別管理パネル
# =========================
def training_type_admin_panel():
    st.subheader("🚒 訓練種別管理")

    name = st.text_input("訓練種別名（例：救助訓練）")

    if st.button("追加", key="add_training_type", use_container_width=True):
        if not name:
            st.error("種別名を入力してください")
            return

        create_training_type_supabase(name)

        st.success("追加しました")
        st.rerun()

    st.markdown("---")
    st.subheader("📋 現在の訓練種別")

    # 一覧取得（Supabase）
    types = get_training_types_supabase()

    for t in types:
        col1, col2 = st.columns([3, 1])

        with col1:
            st.write(t["name"])

        with col2:
            if st.button("削除", key=f"del_type_{t['id']}"):
                delete_training_type_supabase(t["id"])
                st.rerun()

# =========================
# 役職報酬設定
# =========================
def role_reward_settings():
    st.markdown("## 💰 役職報酬設定")
    st.write("支払額が50,000円以上の場合、支払額から、市民税10％、所得税20.42％を引いた金額を設定すること。")

    rows = get_role_rewards_supabase()

    for row in rows:
        role = row["role"]
        amount = row["amount"]

        new_amount = st.number_input(
            f"{role}",
            value=amount,
            step=1000,
            key=f"role_{role}"
        )

        if new_amount != amount:
            update_role_reward_supabase(role, new_amount)
            st.success(f"{role} 更新しました")


# =========================
# メイン
# =========================
def main():
    st.title("⚙️ 管理画面")

    show_toast()

    if not is_admin():
        st.error("管理者のみアクセス可能です")
        return

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🚒 訓練管理",
        "➕ 団員追加",
        "🏘 自治会",
        "📜 役職履歴",
        "👥 役員交代",
        "💰 役職報酬",
        "➕ 項目管理",
        "🚒 技能種別"
    ])
    
    with tab1:
        training_admin_panel()

    with tab2:
        add_user_panel()
    
    with tab3:
        unit_admin_panel()

    with tab4:
        role_history_panel()
    
    with tab5:
        user_admin_panel()

    with tab6:
        role_reward_settings()

    with tab7:
        field_admin_panel()
        
    with tab8:
        training_type_admin_panel()

if __name__ == "__main__":
    main()