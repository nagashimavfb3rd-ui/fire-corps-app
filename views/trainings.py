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
    get_incidents_map_supabase,
    get_user_attendance_supabase
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

    # 必要人数が未設定（0を含む）の場合は表示しない
    required = training.get("required_members") or 0

    event_labels = {
        "meal": "食事あり",
        "party": "懇親会あり",
    }
    event_label = event_labels.get(training.get("event_type"))

    incident_flag = incident_map.get(training["id"], 0)
    title = training.get("title") or "訓練"

    if incident_flag:
        title += " 🚨事故あり"

    # 日付と訓練情報をまとめるコンテナ
    training_date = datetime.strptime(training["date"], "%Y-%m-%d")
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]

    with st.container(
        key=f"training_card_{training['id']}",
        border=True,
    ):

        date_col, detail_col = st.columns(
            [0.7, 4.3],
            vertical_alignment="top",
            wrap=False,
        )

        with date_col:
            st.markdown(
                f"""
                <div class="training-calendar">
                    <div class="training-calendar-month">
                        {training_date.month}月
                    </div>
                    <div class="training-calendar-day">
                        {training_date.day}
                    </div>
                    <div class="training-calendar-weekday">
                        {weekdays[training_date.weekday()]}曜日
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with detail_col:
            # 訓練名から詳細画面へ移動
            if event_label:
                with st.container(key=f"training_title_row_{training['id']}"):
                    title_col, event_col = st.columns(
                        [0.8, 0.2],
                        vertical_alignment="top",
                        gap="small",
                        wrap=False,
                    )

                with title_col:
                    clicked = st.button(
                        title,
                        key=f"detail_{training['id']}",
                        use_container_width=True,
                    )

                with event_col:
                    st.badge(event_label)

            else:
                clicked = st.button(
                    title,
                    key=f"detail_{training['id']}",
                    use_container_width=True,
                )

            if clicked:
                st.session_state.training_id = training["id"]
                st.session_state.page = "training_detail"
                st.rerun()


            # 集合時間・集合場所
            meeting_time = training.get("meeting_time")
            meeting_point = training.get("meeting_point")

            if meeting_time:
                meeting_text = f"集合 {meeting_time}"
                if meeting_point:
                    meeting_text += f"（{meeting_point}）"

                st.markdown(
                    f'<div class="training-meeting-info">'
                    f'{meeting_text}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # 参加人数・必要人数
            attendance_text = f"参加{present}人"
            if required > 0:
                attendance_text += f" / 必要{required}人"

            # ログイン中の団員の回答状態
            user = st.session_state.get("user")
            user_id = user.get("id") if user else None

            if user_id:
                my_status = get_user_attendance_supabase(
                    training["id"],
                    user_id,
                )
            else:
                my_status = None

            # 出欠バッジの表示内容
            if my_status == "present":
                status_text = "自分：出席"
                status_color = "#188038"
            elif my_status == "absent":
                status_text = "自分：欠席"
                status_color = "#c62828"
            else:
                status_text = "未回答"
                status_color = "#666666"

            # 参加人数と出欠状況を同じHTML行に配置
            st.markdown(
                f"""
                <div class="training-attendance-info"
                     style="margin-top: 0.5rem;">
                    <span class="training-attendance-count">
                        {attendance_text}
                    </span>
                    <span class="training-attendance-status"
                          style="background-color: {status_color};">
                        {status_text}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )



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
