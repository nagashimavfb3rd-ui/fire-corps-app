import streamlit as st
from db import (
    get_fiscal_years_supabase,
    get_user_reward_summary_supabase,
    get_user_specific_training_reward_supabase,
    get_hose_reward_summary_supabase,
    get_users_supabase
)
from datetime import datetime


def main():

    # =========================
    # 権限チェック
    # =========================
    user = st.session_state.get("user")

    if not user:
        st.error("ログインしてください")
        st.stop()

    if user.get("auth_role") != "admin":
        st.error("権限がありません")
        st.stop()

    # =========================
    # タイトル
    # =========================
    st.title("📊 団員報酬一覧（管理者）")

    try:
        years = get_fiscal_years_supabase()

        if not years:
            years = [datetime.today().year]

        today = datetime.today()
        current_year = today.year if today.month >= 4 else today.year - 1

        default_index = years.index(current_year) if current_year in years else 0

        fiscal_year = st.selectbox(
            "年度を選択",
            years,
            index=default_index,
            key="admin_reward_year"
        )

        users = get_users_supabase()

        rows = []

        for user_row in users:
            user_id = user_row["id"]
            name = user_row["name"]

            data = get_user_reward_summary_supabase(user_id, fiscal_year)

            target_titles = ["ポンプ点検", "年末夜警"]

            specific_actual, specific_estimated, _ = get_user_specific_training_reward_supabase(
                user_id,
                fiscal_year,
                target_titles
            )

            hose_count, hose_reward = get_hose_reward_summary_supabase(
                user_id,
                fiscal_year
            )

            adjusted_actual = data['actual_total'] - specific_actual
            adjusted_estimated = data['estimated_total'] - specific_estimated

            collection_total = specific_actual + data['role_reward']
            transfer_total = data['actual_total'] + data['role_reward']

            total_receive_actual = adjusted_actual + hose_reward
            total_receive_estimated = adjusted_estimated + hose_reward
            
            rows.append({
                "user_id": user_id,
                "name": name,
                "actual": data['actual_total'],
                "estimated": data['estimated_total'],
                "role": data['role_reward'],
                "total": data['grand_total'],
                "collection": collection_total,
                "transfer": transfer_total,
                "receive_actual": total_receive_actual,
                "receive_estimated": total_receive_estimated,
                "hose_reward": hose_reward
            })

    except Exception as e:
        st.error("データ取得に失敗しました")
        st.write(e)
        st.stop()

    # =========================
    # データなし
    # =========================
    if not rows:
        st.info("データがありません")
        return

    # =========================
    # 並び替え（総支給順）
    # =========================
    rows = sorted(rows, key=lambda x: x["total"], reverse=True)

    # =========================
    # 📊 全体サマリー
    # =========================
    total_actual = sum(r["actual"] for r in rows)
    total_estimated = sum(r["estimated"] for r in rows)
    total_role = sum(r["role"] for r in rows)
    total_all = sum(r["total"] for r in rows)
    total_collection = sum(r["collection"] for r in rows)
    total_transfer = sum(r["transfer"] for r in rows)

    st.markdown("## 📊 全体サマリー")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("実績合計", f"{total_actual:,}円")
    col2.metric("見込合計", f"{total_estimated:,}円")
    col3.metric("役職報酬合計", f"{total_role:,}円")
    col4.metric("総支給合計", f"{total_all:,}円")
    col5.metric("徴収総額", f"{total_collection:,}円")
    col6.metric("振込総額", f"{total_transfer:,}円")

    st.markdown("---")

    # =========================
    # 💸 徴収一覧
    # =========================
    st.markdown("## 💸 徴収額一覧")

    collection_table = [
        {"名前": r["name"], "徴収額": f"{r['collection']:,}円"}
        for r in rows
    ]

    st.dataframe(collection_table, use_container_width=True)

    # =========================
    # 💰 振込一覧
    # =========================
    st.markdown("## 💰 振込一覧")

    transfer_table = [
        {"名前": r["name"], "振込額": f"{r['transfer']:,}円"}
        for r in rows
    ]

    st.dataframe(transfer_table, use_container_width=True)

    # =========================
    # 📋 団員一覧
    # =========================
    st.markdown("## 📋 団員一覧")

    table_data = []

    for r in rows:
        table_data.append({
            "名前": r["name"],
            "出動手当（実績）": f"{r['actual']:,}円",
            "出動手当（予定）": f"{r['estimated']:,}円",
            "役職報酬": f"{r['role']:,}円",
            "徴収額": f"{r['collection']:,}円",
            "振込額": f"{r['transfer']:,}円",
            "ホース報酬": f"{r['hose_reward']:,}円",
            "受取（実績）": f"{r['receive_actual']:,}円",
            "受取（予定）": f"{r['receive_estimated']:,}円"
        })

    st.dataframe(table_data, use_container_width=True)


    # =========================
    # 👥 個別詳細
    # =========================
    st.markdown("---")
    st.markdown("## 👥 団員別詳細")

    for r in rows:
        with st.expander(f"👤 {r['name']}"):

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("出動手当（実績）", f"{r['actual']:,}円")
                st.metric("出動手当（予定）", f"{r['estimated']:,}円")

            with col2:
                st.metric("役職報酬", f"{r['role']:,}円")
                st.metric("徴収額", f"{r['collection']:,}円")

            with col3:
                st.metric("振込額", f"{r['transfer']:,}円")
                st.metric("ホース報酬", f"{r['hose_reward']:,}円")