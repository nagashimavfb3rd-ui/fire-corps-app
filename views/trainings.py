# views/trainings.py
import streamlit as st
from datetime import datetime
from db import (
    get_fiscal_year,
    get_training_target_ids_supabase,
    get_trainings_supabase,
    get_attendance_count_supabase,
    get_active_users_supabase,
    get_target_users_frontend,
    save_attendance_supabase,
    get_training_years_supabase,
    get_incidents_map_supabase
)
from utils.pdf import create_training_pdf


# =========================
# PDF用関数
# =========================
def build_target_label(training):
    individual_ids = get_training_target_ids_supabase(training["id"])

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
    present, absent = get_attendance_count_supabase(training["id"])

    required = training["required_members"] or 0
    shortage_flag = present < required

    EVENT_TYPE_LABELS = {
       "none": "なし",
       "meal": "食事あり",
       "party": "宴会",
    }
    
    st.divider()

    incident_flag = incident_map.get(training["id"], 0)
    
    title = f"📘 {training['title']}（{training['date']}）"
    
    if incident_flag:
        title += " 🚨事故あり"
    
    event_label = EVENT_TYPE_LABELS.get(training["event_type"], "未設定")
    if st.button(title, key=f"detail_{training['id']}", use_container_width=True):
        st.session_state.training_id = training["id"]
        st.session_state.page = "training_detail"
        st.rerun()

    st.caption(
        f"⏰ 集合時間：{training['meeting_time']}　｜　🍱 食事：{event_label}"
    )
    
    # 🎯 参加対象表示
    target_roles = training["target_roles"]
    individual_ids = get_training_target_ids_supabase(training["id"])

    # ⭐ ここが重要（training_detailと同じ）
    users = get_active_users_supabase(training["date"])

    targets = {
        "roles": target_roles,
        "individual_ids": individual_ids
    }

    target_users = get_target_users_frontend(
        training,
        users,
        targets,
        training["date"]
    )

    # 表示ロジック
    if target_roles:
        st.caption(f"🎯 対象役職：{target_roles}")

    elif individual_ids:
        names = [u["name"] for u in target_users]

        if names:
            st.caption("🎯 個別対象者：" + "、".join(names))
        else:
            st.caption("🎯 個別対象者：なし")

    else:
        st.caption("🎯 全員対象")

    # 出欠
    attendance_summary = f"出席：{present}人　｜　欠席：{absent}人"
    if shortage_flag:
        attendance_summary += f"　｜　⚠ 人数不足（必要：{required}人）"
    else:
        attendance_summary += "　｜　✅ OK"
    st.caption(attendance_summary)

# =========================
# メイン画面
# =========================
def main():
    st.title("🚒 訓練一覧")

    # -------------------------
    # 年度取得
    # -------------------------
    years = get_training_years_supabase()

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
    trainings = get_trainings_supabase(selected_year)
    
    incidents_map = get_incidents_map_supabase()

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
        
        training_card(t, incidents_map)


# =========================
# Streamlit entry
# =========================
if __name__ == "__main__":
    main()
