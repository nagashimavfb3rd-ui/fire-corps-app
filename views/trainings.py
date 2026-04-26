# views/trainings.py
import streamlit as st
import sqlite3
from datetime import datetime
from db import get_fiscal_year
from db import get_target_users
from db import get_training_target_ids
from utils.pdf import create_training_pdf

DB_NAME = "fire_corps.db"


# =========================
# DB接続
# =========================
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# データ取得
# =========================
def get_trainings(fiscal_year=None):
    conn = get_connection()
    cursor = conn.cursor()

    if fiscal_year:
        cursor.execute("""
            SELECT * FROM trainings
            WHERE fiscal_year=?
            ORDER BY date DESC
        """, (fiscal_year,))
    else:
        cursor.execute("""
            SELECT * FROM trainings
            ORDER BY date DESC
        """)
    
    data = cursor.fetchall()
    conn.close()
    return data

def get_attendance_count(training_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            SUM(CASE WHEN attend_status='present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN attend_status='absent' THEN 1 ELSE 0 END) as absent_count
        FROM training_attendance
        WHERE training_id=?
    """, (training_id,))

    result = cursor.fetchone()
    conn.close()

    return result["present_count"] or 0, result["absent_count"] or 0

def get_incidents_map():#事故情報取得関数
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT training_id, has_incident
        FROM training_incident
    """)

    rows = cursor.fetchall()
    conn.close()

    # {training_id: has_incident} に変換
    return {r["training_id"]: r["has_incident"] for r in rows}

# =========================
# PDF用関数
# =========================
def build_target_label(training):
    individual_ids = get_training_target_ids(training["id"])

    # ① 役職指定
    if training["target_roles"]:
        return training["target_roles"]

    # ② 個別指定
    elif individual_ids:
        return "対象団員"

    # ③ 全員
    else:
        return "全員"

# =========================
# UI（カード）
# =========================
def training_card(training, incident_map):
    present, absent = get_attendance_count(training["id"])

    total = present + absent
    required = training["required_members"] or 0
    shortage_flag = present < required

    EVENT_TYPE_LABELS = {
       "none": "なし",
       "meal": "食事あり",
       "drinking": "懇親会",
    }
    
    st.markdown("---")

    incident_flag = incident_map.get(training["id"], 0)
    
    title = f"📘 {training['title']}（{training['date']}）"
    
    if incident_flag:
        title += " 🚨事故あり"
    
    st.subheader(title)
    st.write(f"⏰ 集合時間：{training['meeting_time']}")
    event_label = EVENT_TYPE_LABELS.get(training["event_type"], "未設定")
    st.write(f"🍱 食事：{event_label}") 
    
    # 🎯 参加対象表示
    target_roles = training["target_roles"]
    target_users = get_target_users(training["id"], training["date"])
    individual_ids = get_training_target_ids(training["id"])

    if target_roles:
        st.write(f"🎯 対象役職：{target_roles}")

    if individual_ids:
        names = [u["name"] for u in target_users if u["id"] in individual_ids]
        st.write("🎯 個別対象者：" + "、".join(names))

    if not target_roles and not individual_ids:
        st.write("🎯 全員対象")

    # 出欠
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("出席", present)

    with col2:
        st.metric("欠席", absent)

    with col3:
        if shortage_flag:
            st.error(f"⚠ 人数不足（必要：{required}人）")
        else:
            st.success("OK")

    if st.button("詳細を見る", key=f"detail_{training['id']}"):
        st.session_state.training_id = training["id"]
        st.session_state.page = "training_detail"
        st.rerun()


# =========================
# メイン画面
# =========================
def main():
    st.title("🚒 訓練一覧")

    # -------------------------
    # 年度取得
    # -------------------------
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT fiscal_year
        FROM trainings
        ORDER BY fiscal_year DESC
    """)
    years = [row["fiscal_year"] for row in cursor.fetchall()]
    conn.close()

    # -------------------------
    # フィルタUI
    # -------------------------
    current_year = get_fiscal_year(datetime.now().strftime("%Y-%m-%d"))
    
    selected_year = st.selectbox(
        "年度で絞り込み",
        ["すべて"] + years,
        index=(["すべて"] + years).index(current_year) if current_year in years else 0
    )
    
    show_past = st.toggle("経過済みの訓練を表示する", value=False)
    today = datetime.now().date()

    # -------------------------
    # データ取得
    # -------------------------
    if selected_year == "すべて":
        trainings = get_trainings()
    else:
        trainings = get_trainings(selected_year)
    
    incidents_map = get_incidents_map()

    if not trainings:
        st.warning("訓練データがありません")
        return

    if st.button("📄 PDF出力"):

        if selected_year == "すべて":
            st.warning("年度を選択してください")
        else:
            # ★ここ追加
            trainings_with_target = []
            for t in trainings:
                t = dict(t)  # Row → dictに変換
                t["target_label"] = build_target_label(t)
                trainings_with_target.append(t)

            pdf = create_training_pdf(trainings_with_target, selected_year)

            st.download_button(
                label="ダウンロード",
                data=pdf,
                file_name=f"training_plan_{selected_year}.pdf",
                mime="application/pdf"
            )

    for t in trainings:
        training_date = datetime.strptime(t["date"], "%Y-%m-%d").date()
        
        # 経過済みチェック
        is_past = training_date < today
        
        # 非表示設定ならスキップ（今日以前の過去のみ）
        if is_past and not show_past:
            continue
        
        user_unit = st.session_state.user["unit_id"]

        training_card(t, incidents_map)


# =========================
# Streamlit entry
# =========================
if __name__ == "__main__":
    main()