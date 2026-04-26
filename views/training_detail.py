import streamlit as st
import sqlite3
from db import get_target_users
from db import get_training_target_ids
from utils.ui import set_toast, show_toast

DB_NAME = "fire_corps.db"

# =========================
# ICS生成
# =========================
def create_ics(title, date, meeting_time, end_time, meeting_point, note=""):

    mt = meeting_time if meeting_time and meeting_time.strip() else "09:00"
    et = end_time if end_time and end_time.strip() else "10:00"

    mt = mt.zfill(5)
    et = et.zfill(5)

    start = f"{date.replace('-', '')}T{mt.replace(':', '')}00"
    end = f"{date.replace('-', '')}T{et.replace(':', '')}00"

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Fire Corps App//JP
BEGIN:VEVENT
SUMMARY:🚒 {title}
DTSTART:{start}
DTEND:{end}
LOCATION:{meeting_point or ''}
DESCRIPTION:{note or ''}
END:VEVENT
END:VCALENDAR
"""

    ics = ics.replace("\n", "\r\n")

    return ics

# =========================
# DB接続
# =========================
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# 権限チェック
# =========================
def is_admin():
    return (
        "user" in st.session_state and
        st.session_state.user and
        st.session_state.user.get("auth_role") == "admin"
    )


# =========================
# データ取得
# =========================
def get_training(training_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM trainings WHERE id=?", (training_id,))
    data = cursor.fetchone()

    conn.close()
    return data


def get_active_users(target_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE
            (join_date IS NULL OR join_date <= ?)
            AND
            (leave_date IS NULL OR leave_date = '' OR leave_date >= ?)
        ORDER BY id ASC
    """, (target_date, target_date))

    data = cursor.fetchall()
    conn.close()
    return data


def get_attendance(training_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM training_attendance
        WHERE training_id=?
    """, (training_id,))

    data = cursor.fetchall()
    conn.close()
    return data


# =========================
# 出欠更新（予定 or 実績）
# =========================
def upsert_attendance(training_id, user_id, status, mode="planned"):
    current_user = st.session_state.get("user")
    
    # 🔒 実績は管理者のみ
    if mode == "actual" and not is_admin():
        st.error("管理者のみ実績を変更できます")
        return

    # 🔒 予定出欠：自分 or 管理者のみ
    if mode == "planned":
        if current_user["id"] != user_id and not is_admin():
            st.error("自分の出欠のみ変更できます")
            return

    conn = get_connection()
    cursor = conn.cursor()

    if mode == "actual":
        column = "actual_status"
    else:
        column = "attend_status"

    cursor.execute("""
        SELECT id FROM training_attendance
        WHERE training_id=? AND user_id=?
    """, (training_id, user_id))

    exists = cursor.fetchone()

    if exists:
        cursor.execute(f"""
            UPDATE training_attendance
            SET {column}=?
            WHERE training_id=? AND user_id=?
        """, (status, training_id, user_id))
    else:
        cursor.execute(f"""
            INSERT INTO training_attendance (
                training_id, user_id, attend_status, actual_status, created_at
            )
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (
            training_id,
            user_id,
            status if mode == "planned" else None,
            status if mode == "actual" else None
        ))

    conn.commit()
    conn.close()


# =========================
# 
# =========================
def save_meal(training_id, user_id, meal_option):
    current_user = st.session_state.get("user")

    # 🔒 自分 or 管理者のみ
    if current_user["id"] != user_id and not is_admin():
        st.error("自分の宴会参加のみ変更できます")
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM training_attendance
        WHERE training_id=? AND user_id=?
    """, (training_id, user_id))

    exists = cursor.fetchone()

    if exists:
        cursor.execute("""
            UPDATE training_attendance
            SET meal_option=?
            WHERE training_id=? AND user_id=?
        """, (meal_option, training_id, user_id))
    else:
        cursor.execute("""
            INSERT INTO training_attendance (
                training_id, user_id, meal_option, created_at
            )
            VALUES (?, ?, ?, datetime('now'))
        """, (training_id, user_id, meal_option))

    conn.commit()
    conn.close()

# =========================
# 一括操作（管理者のみ）
# =========================
def bulk_attendance(users, training_id, mode="planned"):
    st.markdown("### ⚡ 一括操作")

    col1, col2 = st.columns(2)

    if col1.button("全員出席", key="bulk_present"):
        for u in users:
            upsert_attendance(training_id, u["id"], "present", mode)
        st.rerun()

    if col2.button("全員欠席", key="bulk_absent"):
        for u in users:
            upsert_attendance(training_id, u["id"], "absent", mode)
        st.rerun()

# =========================
# ホースの片付け登録関数（管理者のみ）
# =========================
def save_hose_count(training_id, user_id, count):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM training_hose_members
        WHERE hose_id=? AND user_id=?
    """, (training_id, user_id))

    exists = cursor.fetchone()

    if exists:
        cursor.execute("""
            UPDATE training_hose_members
            SET hose_count=?
            WHERE hose_id=? AND user_id=?
        """, (count, training_id, user_id))
    else:
        cursor.execute("""
            INSERT INTO training_hose_members (hose_id, user_id, hose_count)
            VALUES (?, ?, ?)
        """, (training_id, user_id, count))

    conn.commit()
    conn.close()
    
    set_toast("ホース本数を保存しました", "update")

# =========================
# ホースの片付け本数取得
# =========================
def get_hose_counts(training_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, hose_count
        FROM training_hose_members
        WHERE hose_id=?
    """, (training_id,))

    rows = cursor.fetchall()

    # 👇 user_id → 本数 の形にする
    result = {r["user_id"]: r["hose_count"] for r in rows}

    conn.close()
    return result

# =========================
# 事故報告
# =========================
def save_incident(training_id, data):
    conn = get_connection()
    cursor = conn.cursor()

    # 既存チェック
    cursor.execute("""
        SELECT id FROM training_incident
        WHERE training_id=?
        ORDER BY id DESC
        LIMIT 1
    """, (training_id,))

    exists = cursor.fetchone()

    if exists:
        # UPDATE（編集）
        cursor.execute("""
            UPDATE training_incident
            SET
                has_incident=?,
                injury_flag=?,
                traffic_accident_flag=?,
                police_called=?,
                reported_to_commander=?,
                reported_to_hq=?,
                incident_datetime=?,
                incident_location=?,
                incident_summary=?,
                injury_details=?,
                damage_details=?,
                note=?
            WHERE id=?
        """, (
            data["has_incident"],
            data["injury_flag"],
            data["traffic_accident_flag"],
            data["police_called"],
            data["reported_to_commander"],
            data["reported_to_hq"],
            data["incident_datetime"],
            data["incident_location"],
            data["incident_summary"],
            data["injury_details"],
            data["damage_details"],
            data["note"],
            exists["id"]
        ))

    else:
        # INSERT（初回）
        cursor.execute("""
            INSERT INTO training_incident (
                training_id,
                has_incident,
                injury_flag,
                traffic_accident_flag,
                police_called,
                reported_to_commander,
                reported_to_hq,
                incident_datetime,
                incident_location,
                incident_summary,
                injury_details,
                damage_details,
                note,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            training_id,
            data["has_incident"],
            data["injury_flag"],
            data["traffic_accident_flag"],
            data["police_called"],
            data["reported_to_commander"],
            data["reported_to_hq"],
            data["incident_datetime"],
            data["incident_location"],
            data["incident_summary"],
            data["injury_details"],
            data["damage_details"],
            data["note"],
        ))

    conn.commit()
    conn.close()

    set_toast("事故記録を保存しました", "update")

# =========================
# 事故報告情報取得
# =========================
def get_incident(training_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM training_incident
        WHERE training_id=?
        ORDER BY id DESC
        LIMIT 1
    """, (training_id,))

    row = cursor.fetchone()
    conn.close()
    return row

# =========================
# ユーザーカード
# =========================
def user_card(user, training_id, planned_status, actual_status, meal_option, event_type):
    st.subheader(f"👤 {user['name']}")
    
    current_user = st.session_state.get("user")
    is_self = current_user["id"] == user["id"]
    can_edit = is_self or is_admin()


    #  出欠予定表示
    if planned_status == "present":
        st.success("出欠予定：🟢 出席")
    elif planned_status == "absent":
        st.error("出欠予定：🔴 欠席")
    else:
        st.warning("出欠予定：未定")

    #  出欠予定回答
    col1, col2 = st.columns(2)

    if col1.button(
        "出席",
        key=f"p_{user['id']}_{training_id}",
        disabled=not can_edit
    ):
        upsert_attendance(training_id, user["id"], "present", "planned")
        st.rerun()

    if col2.button(
        "欠席",
        key=f"a_{user['id']}_{training_id}",
        disabled=not can_edit
    ):
        upsert_attendance(training_id, user["id"], "absent", "planned")
        st.rerun()
    
    # 管理者のみ実績操作
    if is_admin():
        if actual_status == "present":
            st.success("実出席")
        elif actual_status == "absent":
            st.error("実欠席")
        else:
            st.warning("未確認")
    
    # 🍻 宴会・食事会のときだけ表示
    if event_type in ["party", "meal"]:

        if meal_option == "join":
            st.success("🍻 宴会・食事会参加")
        elif meal_option == "bento":
            st.info("🍱 弁当のみ")
        elif meal_option == "no":
            st.error("❌ 宴会・食事会不参加、弁当不要")
        else:
            st.warning("宴会・食事会：未定")

        st.markdown("🍻 宴会参加")

        col5, col6, col7, col8 = st.columns(4)

        if col5.button(
            "参加",
            key=f"meal_join_{user['id']}_{training_id}",
            disabled=not can_edit
        ):
            save_meal(training_id, user["id"], "join")
            st.rerun()

        if col6.button(
            "弁当のみ",
            key=f"meal_bento_{user['id']}_{training_id}",
            disabled=not can_edit
        ):
            save_meal(training_id, user["id"], "bento")
            st.rerun()

        if col7.button(
            "不参加",
            key=f"meal_no_{user['id']}_{training_id}",
            disabled=not can_edit
        ):
            save_meal(training_id, user["id"], "no")
            st.rerun()

        if col8.button(
            "未定",
            key=f"meal_none_{user['id']}_{training_id}",
            disabled=not can_edit
        ):
            save_meal(training_id, user["id"], "none")
            st.rerun()

# =========================
# メイン
# =========================
def main():
    st.title("📘 訓練詳細")
    
    show_toast()
    
    if st.button("← 一覧へ戻る"):
        st.session_state.page = "trainings"
        st.rerun()

    # クエリパラメータから取得
    training_id = st.session_state.get("training_id")
    
    if not training_id:
        st.warning("訓練が選択されていません")
        st.stop()
        
    # 念のためint変換
    training_id = int(training_id)

    hose_map = get_hose_counts(training_id)

    training = get_training(training_id)
    training_date = training["date"]

    users = get_active_users(training_date)
    attendance = get_attendance(training_id)
    training = get_training(training_id)
    target_users = get_target_users(training_id, training_date)
    target_ids = [u["id"] for u in target_users]

    if not training:
        st.error("訓練データが見つかりません")
        return

    st.subheader(f"🚒 {training['title']}")

    st.markdown("### 🎯 参加対象者")

    # 🎯 参加対象表示
    target_roles = training["target_roles"]
    target_users = get_target_users(training["id"], training["date"])
    individual_ids = get_training_target_ids(training["id"])

    # 👇 ユーザー表示
    with st.container():
        st.markdown("#### 👥 対象情報")

        # ① 役職指定
        if target_roles:
            roles = target_roles.split(",")

            cols = st.columns(len(roles))
            for i, r in enumerate(roles):
                cols[i].info(f"🎖 {r}")

        # ② 個別指定
        elif individual_ids:
            names = [u["name"] for u in target_users if u["id"] in individual_ids]

            st.caption("👤 個別指定")

            # 横並び（最大4列）
            chunk_size = 4
            for i in range(0, len(names), chunk_size):
                cols = st.columns(min(chunk_size, len(names) - i))
                for j, name in enumerate(names[i:i+chunk_size]):
                    cols[j].success(f"{name}")

        # ③ 全員
        else:
            st.success("👥 全員対象")

    st.write(f"📅 日付：{training['date']}")
    st.write(f"⏰ 時間：{training['start_time']} ～ {training['end_time']}")
    st.write(f"📍 場所：{training['location']}")

    st.write(f"🚗 集合：{training['meeting_point']}（{training['meeting_time']}）")
    st.write(f"👕 服装：{training['uniform']}")
    st.write(f"💰 手当：{training['reward_amount']} 円")
    
    event_type = training["event_type"]
    
    if event_type == "party":
        st.success("🍻 宴会あり")
    elif event_type == "meal":
        st.info("🍱 食事会あり")
    else:
        st.caption("🚒 宴会・食事会なし")

    st.write(f"📌 ステータス：{training['status']}")
    st.write(f"📝 備考：{training['note'] or 'なし'}")

    # =========================
    # 📅 カレンダー登録ボタン
    # =========================
    ics_data = create_ics(
        title=training["title"],
        date=training["date"],
        meeting_time=training["meeting_time"] or training["start_time"],  # ← 集合時間
        end_time=training["end_time"] or "23:59",
        meeting_point=training["meeting_point"],  # ← 集合場所
        note=training["note"]
    )

    meeting_time = training["meeting_time"] or training["start_time"]
    end_time = training["end_time"] or "23:59"

    st.write(training["date"], meeting_time, end_time)
    
    st.markdown("---")
    
    st.download_button(
        label="📅 カレンダーに追加",
        data=ics_data,
        file_name=f"{training['title']}_{training['date']}.ics",
        mime="text/calendar"
    )

    st.caption("※ダウンロード後に開くとカレンダーに追加されます※動作未確認")

    # attendance map
    attendance_map = {
        a["user_id"]: {
            "attend_status": a["attend_status"],
            "meal_option": a["meal_option"],
            "actual_status": a["actual_status"]
        }
        for a in attendance
    }


    # 管理者：一括操作
    if is_admin():
        mode = st.radio(
            "一括更新モード",
            ["planned", "actual"],
            format_func=lambda x: "出席予定" if x == "planned" else "実出席",
            horizontal=True
        )

        bulk_attendance(users, training_id, mode=mode)

    current_user = st.session_state.get("user")

    # =========================
    # 🙋 自分の出欠（操作OK）
    # =========================
    my_data = attendance_map.get(current_user["id"], {})
    my_planned = my_data.get("attend_status")
    my_meal = my_data.get("meal_option")
    my_actual = my_data.get("actual_status")

    with st.expander("## 🙋 自分の出欠", expanded=False):
        st.info("あなたの出欠を入力してください")

        user_card(
            current_user,
            training_id,
            my_planned,
            my_actual,
            my_meal,
            event_type
        )

    # =========================
    # 👥 出欠一覧（テーブル表示）
    # =========================
    st.markdown("---")
    st.markdown("## 👥 出欠一覧")
    
    # 🔽 ソート（出席 → 未定 → 欠席）
    def sort_key(u):
        data = attendance_map.get(u["id"], {})
        status = data.get("attend_status")
        
        order = {
            "present": 0,
            None: 1,
            "absent": 2
        }
        return order.get(status, 1)
    
    sorted_users = sorted(users, key=sort_key)
    
    # =========================
    # 📊 出欠集計
    # =========================

    # 訓練出欠
    train_present = 0
    train_pending = 0
    train_absent = 0

    # 宴会・食事会
    meal_join = 0
    meal_pending = 0
    meal_absent = 0
    meal_bento = 0

    for u in users:
        data = attendance_map.get(u["id"], {})

        # --- 訓練 ---
        status = data.get("attend_status")
        if status == "present":
            train_present += 1
        elif status == "absent":
            train_absent += 1
        else:
            train_pending += 1

        # --- 宴会 ---
        if event_type in ["party", "meal"]:
            meal = data.get("meal_option")

            if meal == "join":
                meal_join += 1
            elif meal == "bento":
                meal_bento += 1
            elif meal == "no":
                meal_absent += 1
            else:
                meal_pending += 1

    # =========================
    # 📢 表示
    # =========================

    st.markdown("### 📊 出欠集計")

    st.success(
        f"訓練出欠：出席 {train_present}名　未定 {train_pending}名　欠席 {train_absent}名"
    )

    # 🍻 イベントがあるときだけ表示
    if event_type in ["party", "meal"]:
        st.info(
            f"宴会（食事会）出欠：出席 {meal_join}名　未定 {meal_pending}名　欠席 {meal_absent}名　弁当 {meal_bento}名"
        )
    
    # 🔽 ヘッダー
    if is_admin():
        col1, col2, col3, col4, col5 = st.columns([2,2,2,2,3])
        col1.markdown("**団員名**")
        col2.markdown("**出欠予定**")
        col3.markdown("**宴会出欠**")
        col4.markdown("**実出席**")
        col5.markdown("**操作**")
    else:
        col1, col2, col3, col4 = st.columns([2,2,2,2])
        col1.markdown("**団員名**")
        col2.markdown("**出欠予定**")
        col3.markdown("**宴会出欠**")
        col4.markdown("**実出席**")
    
    # 🔽 行表示
    for u in sorted_users:
        data = attendance_map.get(u["id"], {})
        planned = data.get("attend_status")
        meal = data.get("meal_option")
        actual = data.get("actual_status")

        if is_admin():
            col1, col2, col3, col4, col5 = st.columns([2,2,2,2,3])
        else:
            col1, col2, col3, col4 = st.columns([2,2,2,2])

        # 名前
        name = u["name"]
        if u["id"] == current_user["id"]:
            name += "（あなた）"
        
        col1.write(name)

        # 出欠予定
        if planned == "present":
            col2.success("出席")
        elif planned == "absent":
            col2.error("欠席")
        else:
            col2.warning("未定")

        # 宴会
        if event_type in ["party", "meal"]:
            if meal == "join":
                col3.success("参加")
            elif meal == "bento":
                col3.info("弁当")
            elif meal == "no":
                col3.error("不参加")
            else:
                col3.warning("未定")
        else:
            col3.write("-")
        
        # 実出席
        if actual == "present":
            col4.success("出席")
        elif actual == "absent":
            col4.error("欠席")
        else:
            col4.warning("未")

        # 操作（管理者のみ）
        if is_admin():
            c1, c2 = col5.columns(2)

            if c1.button("出席", key=f"act_p_{u['id']}_{training_id}"):
                upsert_attendance(training_id, u["id"], "present", "actual")
                st.rerun()

            if c2.button("欠席", key=f"act_a_{u['id']}_{training_id}"):
                upsert_attendance(training_id, u["id"], "absent", "actual")
                st.rerun()

    # =========================
    # 🚒 ホース片付け入力（管理者のみ）
    # =========================
    if is_admin():
        with st.expander("## 🚒 ホース片付け記録", expanded=False):
            st.info("各団員の片付け本数を入力してください")

            for u in sorted_users:
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:# 名前
                    st.write(u["name"])

                with col2:# 入力
                    hose_count = st.number_input(
                        "本数",
                        min_value=0,
                        step=1,
                        value=hose_map.get(u["id"], 0),
                        key=f"hose_{training_id}_{u['id']}",
                        label_visibility="collapsed"
                    )

                with col3:
                    if st.button(
                        "保存",
                        key=f"save_hose_{u['id']}_{training_id}",
                        use_container_width=True
                    ):
                        save_hose_count(training_id, u["id"], hose_count)
                        st.rerun()

    # =========================
    # 🚨 事故記録フォーム（ホースの下）
    # =========================
    if is_admin():

        incident = dict(get_incident(training_id) or {})
        
        with st.expander("## 🚨 訓練時事故記録", expanded=False):

            with st.form("incident_form"):
                has_incident = st.checkbox(
                    "事故あり",
                    value=bool(incident.get("has_incident", 0))
                )
            
                injury_flag = st.checkbox(
                    "負傷あり",
                    value=bool(incident.get("injury_flag", 0))
                )
            
                traffic_accident_flag = st.checkbox(
                    "交通事故あり",
                    value=bool(incident.get("traffic_accident_flag", 0))
                )
            
                police_called = st.checkbox(
                    "警察通報",
                    value=bool(incident.get("police_called", 0))
                )
            
                reported_to_commander = st.checkbox(
                    "分団長へ報告",
                    value=bool(incident.get("reported_to_commander", 0))
                )
            
                reported_to_hq = st.checkbox(
                    "本部へ報告",
                    value=bool(incident.get("reported_to_hq", 0))
                )
            
                incident_datetime = st.text_input(
                    "発生日時",
                    value=incident.get("incident_datetime", "") or ""
                )
            
                incident_location = st.text_input(
                    "発生場所",
                    value=incident.get("incident_location", "") or ""
                )
            
                incident_summary = st.text_area(
                    "事故概要",
                    value=incident.get("incident_summary", "") or ""
                )
            
                injury_details = st.text_area(
                    "負傷内容",
                    value=incident.get("injury_details", "") or ""
                )
            
                damage_details = st.text_area(
                    "物的損害",
                    value=incident.get("damage_details", "") or ""
                )
            
                note = st.text_area(
                    "備考",
                    value=incident.get("note", "") or ""
                )

                submitted = st.form_submit_button("事故記録を保存")

                if submitted:
                    save_incident(training_id, {
                        "has_incident": int(has_incident),
                        "injury_flag": int(injury_flag),
                        "traffic_accident_flag": int(traffic_accident_flag),
                        "police_called": int(police_called),
                        "reported_to_commander": int(reported_to_commander),
                        "reported_to_hq": int(reported_to_hq),
                        "incident_datetime": incident_datetime,
                        "incident_location": incident_location,
                        "incident_summary": incident_summary,
                        "injury_details": injury_details,
                        "damage_details": damage_details,
                        "note": note,
                    })

                    st.rerun()

if __name__ == "__main__":
    main()