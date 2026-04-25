import streamlit as st
from db import get_connection
from db import get_user_reward_summary
from db import get_fiscal_years
from db import get_user_specific_training_reward
from db import get_hose_reward_summary
from datetime import datetime

def main():
    
    # =========================
    # ログインチェック
    # =========================
    user = st.session_state.get("user")

    if not user:
        st.write("LOGIN USER:", user)
        st.write("SESSION:", st.session_state)
        st.error("ログインしてください")
        st.stop()

    user_id = user["id"]

    # =========================
    # タイトル
    # =========================
    st.title("💰 報酬確認")
    st.write("※実際の振込額は消防本部で計算されるので、参考額として確認してください。")

    # =========================
    # データ取得
    # =========================
    conn = get_connection()

    try:
        years = get_fiscal_years(conn)
    
        if not years:
            years = [datetime.today().year]

        # 今日の年度
        today = datetime.today()
        current_year = today.year if today.month >= 4 else today.year - 1

        default_index = years.index(current_year) if current_year in years else 0

        fiscal_year = st.selectbox(
            "年度を選択",
            years,
            index=default_index,
            key="my_reward_year"
        )

        data = get_user_reward_summary(conn, user_id, fiscal_year)
        
        target_titles = ["ポンプ点検", "年末夜警"]
        
        specific_actual, specific_estimated, specific_records = get_user_specific_training_reward(
            conn,
            user_id,
            fiscal_year,
            target_titles
        )
        
        hose_count, hose_reward = get_hose_reward_summary(
            conn,
            user_id,
            fiscal_year
        )
        
        # 計算
        adjusted_actual = data['actual_total'] - specific_actual
        adjusted_estimated = data['estimated_total'] - specific_estimated
        collection_total = specific_actual + data['role_reward']
        transfer_total = data['actual_total'] + data['role_reward']
        # 実績ベース
        total_receive_actual = adjusted_actual + hose_reward
        # 予定ベース
        total_receive_estimated = adjusted_estimated + hose_reward

        records = data["records"]


    finally:
        conn.close()

    # =========================
    # サマリー表示
    # =========================

    st.markdown("## 💰 受取見込額（今年度）")
    st.write("左は実際の出席状況のみで計算。右は出席予定の訓練の報酬を含めてい計算")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 実出欠ベース")
        st.metric("出動手当", f"{adjusted_actual:,}円")
        st.metric("ホース報酬", f"{hose_reward:,}円")
        st.metric("合計受取", f"{total_receive_actual:,}円")

    with col2:
        st.markdown("### 出欠予定込ベース")
        st.metric("出動手当", f"{adjusted_estimated:,}円")
        st.metric("ホース報酬", f"{hose_reward:,}円")
        st.metric("合計受取", f"{total_receive_estimated:,}円")

    with st.expander("🧯 ホース片付け詳細", expanded=False):
        col1, col2 = st.columns(2)
        col1.metric("合計本数", f"{hose_count}本")
        col2.metric("報酬額", f"{hose_reward:,}円")

    st.markdown("---")
    
    with st.expander("📊 受取見込計算根拠（実出欠ベース）", expanded=False):

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 💰 振込見込")
            st.metric("出動手当", f"{data['actual_total']:,}円")
            st.metric("年間報酬", f"{data['role_reward']:,}円")
            st.metric("振込合計", f"{transfer_total:,}円")

        with col2:
            st.markdown("### 🚒 徴収予定")
            st.metric("対象手当", f"{specific_actual:,}円")
            st.metric("年間報酬", f"{data['role_reward']:,}円")
            st.metric("徴収合計", f"{collection_total:,}円")

    # =========================
    # 訓練参加履歴（整形）
    # =========================
    st.markdown("---")
    st.markdown("## 📋 訓練参加履歴")

    if not records:
        st.info("データがありません")
    else:
        table_data = []

        for r in records:
            # 表示用に日本語変換
            status_label = "出席" if r["status"] == "present" else "欠席"
            source_label = "実績" if r["source"] == "actual" else "予定"

            table_data.append({
                "日付": r["date"],
                "訓練名": r["title"],
                "判定": status_label,
                "種別": source_label,
                "金額": f"{r['amount']:,}円"
            })

        st.dataframe(table_data, use_container_width=True)