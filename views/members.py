import streamlit as st
from db import get_units_supabase
from db import get_officer_experience_supabase
from db import get_users_supabase
from utils.ui import calc_years_by_fiscal_year
from datetime import datetime


def is_admin():
    return st.session_state.user and st.session_state.user["auth_role"] == "admin"


def calc_age(birth_date):
    if not birth_date:
        return None

    birth = datetime.strptime(birth_date, "%Y-%m-%d")
    today = datetime.today()

    return today.year - birth.year - (
        (today.month, today.day) < (birth.month, birth.day)
    )

def calc_years(join_date):
    if not join_date:
        return None

    join = datetime.strptime(join_date, "%Y-%m-%d")
    today = datetime.today()

    return today.year - join.year - (
        (today.month, today.day) < (join.month, join.day)
    )

def can_view_training():
    user = st.session_state.get("user")
    return user and user.get("role") in ["分団長", "副分団長"]

def can_edit_training():
    user = st.session_state.get("user")
    return user and user.get("role") in ["分団長", "副分団長"]


# =========================
# UI
# =========================
def user_card(user, exp_map):

    current_user = st.session_state.get("user")
    if not current_user:
        st.stop()

    st.markdown("---")

    units = get_units_supabase()
    unit_map = {u["id"]: u["name"] for u in units}
    exp = exp_map.get(user["id"], {"分団長": False, "副分団長": False})


    # =========================
    # 表示モード
    # =========================
    if user["leave_date"]:
        st.markdown("<div style='opacity:0.4'>", unsafe_allow_html=True)
    
    if user["leave_date"]:
        st.markdown(f"<span style='color:gray'>👤 {user['name']}（退団）</span>", unsafe_allow_html=True)
    else:
        st.subheader(f"👤 {user['name']}")

    unit_map = {u["id"]: u["name"] for u in units}
    age = calc_age(user["birth_date"])
    years = calc_years_by_fiscal_year(user["join_date"])

    if exp["分団長"] and exp["副分団長"]:
        exp_text = "分団長・副分団長経験あり"
    elif exp["分団長"]:
        exp_text = "分団長経験あり"
    elif exp["副分団長"]:
        exp_text = "副分団長経験あり"
    else:
        exp_text = ""

    role_text = user["role"]

    if exp_text:
        role_text += f"（{exp_text}）"

    st.write(f"🎖 役職：{role_text}")
    st.write(f"🏘 自治会：{unit_map.get(user['unit_id'], '未所属')}")
    st.write(f"🎂 生年月日：{user['birth_date']}（{age}歳）")
    st.write(f"📅 入団日：{user['join_date']}（年度末時点で満{years}年）")
    if user["leave_date"]:
        st.write(f"🏁 退団日：{user['leave_date']}")



    current_user = st.session_state.get("user")
    is_self = current_user["id"] == user["id"]

    col1, col2 = st.columns(2)
    
    if col1.button("詳細", key=f"detail_{user['id']}"):
        st.write("押されたID:", user["id"])
        st.session_state.selected_user_id = user["id"]
        st.session_state.page = "member_detail"
        st.session_state.open_edit = False
        st.rerun()
        
    if (is_admin() or is_self):
        if col2.button("編集", key=f"edit_{user['id']}", use_container_width=True):
            st.session_state.selected_user_id = user["id"]
            st.session_state.page = "member_detail"
            st.session_state.open_edit = True
            st.rerun()
    
    if user["leave_date"]:
        st.markdown("</div>", unsafe_allow_html=True)


# =========================
# main
# =========================
def main():
    st.title("👥 団員一覧")
    
    filter_option = st.selectbox(
        "表示切替",
        ["在籍中", "退団者", "全て"],
        index=0
    )
    
    users = get_users_supabase()
    
    if filter_option == "在籍中":
        users = [u for u in users if not u.get("leave_date")]
    elif filter_option == "退団者":
        users = [u for u in users if u.get("leave_date")]

    current_user = st.session_state.get("user")
    
    def sort_key(u):
        # ① 自分を最優先
        if u["id"] == current_user["id"]:
            return (0, 0)

        # ② 役職優先順位
        role_order = {
            "分団長": 1,
            "副分団長": 2,
            "団員": 3
        }

        role_rank = role_order.get(u["role"], 99)

        # ③ 在籍年数（長いほど上）
        years = calc_years(u["join_date"]) or 0

        # マイナスにして「長い順」にする
        return (role_rank, -years)

    exp_map = get_officer_experience_supabase()

    # 🔽 ソート実行
    sorted_users = sorted(users, key=sort_key)


    # 🔽 表示
    for u in sorted_users:
        user_card(u, exp_map)

    # =========================
    # 免許別集計
    # =========================
    st.markdown("## 🚗 免許別一覧")
    
    license_map = {}

    for u in users:
        license_type = u["license_type"] or "未設定"

        # 在籍中だけにしたい場合（おすすめ）
        if filter_option == "在籍中" and u["leave_date"]:
            continue

        if license_type not in license_map:
            license_map[license_type] = {
                "count": 0,
                "names": []
            }

        license_map[license_type]["count"] += 1
        license_map[license_type]["names"].append(u["name"])

    # 表用データ作成
    table_data = []

    for license_type, data in license_map.items():
        table_data.append({
            "免許": license_type,
            "人数": data["count"],
            "名前": "、".join(data["names"])
        })

    # 表示
    st.table(table_data)


if __name__ == "__main__":
    main()