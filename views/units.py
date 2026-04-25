import streamlit as st
import sqlite3
from datetime import date
from utils.pdf import create_unit_summary_pdf

DB_NAME = "fire_corps.db"


# =========================
# DB接続
# =========================
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# データ取得（人数＋団員名まとめて取得）
# =========================
def get_units_full(target_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            u.id,
            u.name,
            u.required_members,
            COUNT(us.id) as member_count,
            GROUP_CONCAT(us.name || '（' || us.login_id || '）', '、') as member_names
        FROM units u
        LEFT JOIN users us 
            ON u.id = us.unit_id
            AND (
                us.join_date <= ?
                AND (
                    us.leave_date IS NULL 
                    OR us.leave_date = '' 
                    OR us.leave_date > ?
                )
            )
        GROUP BY u.id
        ORDER BY u.name
    """, (target_date, target_date))

    data = cursor.fetchall()
    conn.close()
    return data


# =========================
# UI（コンパクトカード）
# =========================
def unit_card(unit):
    required = unit["required_members"] or 0
    current = unit["member_count"] or 0
    shortage = current < required
    diff = required - current

    # 団員名（None対策）
    members = unit["member_names"] if unit["member_names"] else "なし"

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"### 🏘 {unit['name']}")
        st.caption(members)  # コンパクト表示

    with col2:
        st.metric("人数", f"{current}/{required}")

        if shortage:
            st.error(f"-{diff}")
        else:
            st.success("OK")

# =========================
# メイン
# =========================
def main():
    st.title("🏘 自治会別団員数")

    target_date = st.date_input(
        "時点を選択",
        value=date.today()
    )

    units = get_units_full(str(target_date))

    if not units:
        st.warning("自治会データがありません")
        return

    if st.button("📄 PDF出力"):

        pdf = create_unit_summary_pdf(units, target_date)

        st.download_button(
            label="ダウンロード",
            data=pdf,
            file_name="unit_summary.pdf",
            mime="application/pdf"
        )

    # =========================
    # 合計計算
    # =========================
    total_required = sum(u["required_members"] or 0 for u in units)
    total_current = sum(u["member_count"] or 0 for u in units)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("団員数", total_current)

    with col2:
        st.metric("定数", total_required)

    for u in units:
        unit_card(u)


if __name__ == "__main__":
    main()