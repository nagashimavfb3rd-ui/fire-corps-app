import streamlit as st
from datetime import datetime, date

def show_toast():
    if "toast" in st.session_state:
        msg, type_ = st.session_state.toast

        if type_ == "success":
            st.toast(f"✅ {msg}")
        elif type_ == "delete":
            st.toast(f"🗑️ {msg}")
        elif type_ == "update":
            st.toast(f"🔄 {msg}")
        elif type_ == "error":
            st.toast(f"⚠️ {msg}")

        del st.session_state.toast


def set_toast(msg, type_="success"):
    st.session_state.toast = (msg, type_)

# 在籍年数計算
def calc_years_by_fiscal_year(join_date: str, ref_date=None):
    if not join_date:
        return None

    join = datetime.strptime(join_date, "%Y-%m-%d").date()
    ref = ref_date or date.today()

    # =========================
    # ① 入団が未来なら0
    # =========================
    if join > ref:
        return 0

    # =========================
    # ② 入団年度（FY）
    # =========================
    join_fy = join.year if join.month >= 4 else join.year - 1

    # =========================
    # ③ 閲覧日の年度末を決める
    # =========================
    ref_fy = ref.year if ref.month >= 4 else ref.year - 1

    # =========================
    # ④ 年度ベースでカウント（ここが本体）
    # =========================
    return ref_fy - join_fy + 1