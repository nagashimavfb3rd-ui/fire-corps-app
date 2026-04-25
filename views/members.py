import streamlit as st
import sqlite3
from db import get_units
from db import get_officer_experience
from utils.ui import calc_years_by_fiscal_year
from datetime import datetime

DB_NAME = "fire_corps.db"


# =========================
# DB
# =========================
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def is_admin():
    return st.session_state.user and st.session_state.user["auth_role"] == "admin"


def get_users(filter_type="all"):
    conn = get_connection()
    cursor = conn.cursor()

    if filter_type == "active":
        cursor.execute("""
            SELECT * FROM users
            WHERE leave_date IS NULL OR leave_date=''
            ORDER BY id ASC
        """)
    elif filter_type == "retired":
        cursor.execute("""
            SELECT * FROM users
            WHERE leave_date IS NOT NULL AND leave_date!=''
            ORDER BY id ASC
        """)
    else:
        cursor.execute("""
            SELECT * FROM users
            ORDER BY id ASC
        """)
    data = cursor.fetchall()
    conn.close()
    return data



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

def get_fields():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM user_fields
    ORDER BY sort_order ASC, id ASC
    """)
    data = cursor.fetchall()

    conn.close()
    return data

def get_user_field_values(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT f.field_name, v.value
        FROM user_field_values v
        JOIN user_fields f ON f.id = v.field_id
        WHERE v.user_id=?
    """, (user_id,))

    data = cursor.fetchall()
    conn.close()
    return data

def save_field_value(user_id, field_id, value):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO user_field_values (user_id, field_id, value)
    VALUES (?, ?, ?)
    ON CONFLICT(user_id, field_id)
    DO UPDATE SET value=excluded.value
    """, (user_id, field_id, value))

    conn.commit()
    conn.close()

def get_training_counts(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT tt.name, tc.count
    FROM training_counts tc
    JOIN training_types tt ON tt.id = tc.training_type_id
    WHERE tc.user_id=?
    """, (user_id,))

    data = cursor.fetchall()
    conn.close()
    return data

def training_count_editor(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM training_types")
    types = cursor.fetchall()

    st.markdown("### 🚒 訓練回数（手動入力）")

    for t in types:

        cursor.execute("""
        SELECT count FROM training_counts
        WHERE user_id=? AND training_type_id=?
        """, (user_id, t["id"]))

        row = cursor.fetchone()
        current = row["count"] if row else 0

        new_value = st.number_input(
            f"{t['name']} 回数",
            value=current,
            step=1,
            key=f"train_{user_id}_{t['id']}"
        )

        if st.button("保存", key=f"save_{user_id}_{t['id']}"):

            cursor.execute("""
            INSERT INTO training_counts (user_id, training_type_id, count)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, training_type_id)
            DO UPDATE SET count=excluded.count
            """, (user_id, t["id"], new_value))

            conn.commit()
            st.success("更新しました")
            st.rerun()

    conn.close()

# =========================
# UI
# =========================
def user_card(user):

    current_user = st.session_state.get("user")
    if not current_user:
        st.stop()

    st.markdown("---")

    units = get_units()
    unit_map = {u["id"]: u["name"] for u in units}


    # =========================
    # 表示モード
    # =========================
    if user["leave_date"]:
        st.markdown("<div style='opacity:0.4'>", unsafe_allow_html=True)
    
    if user["leave_date"]:
        st.markdown(f"<span style='color:gray'>👤 {user['name']}（退団）</span>", unsafe_allow_html=True)
    else:
        st.subheader(f"👤 {user['name']}")

    units = get_units()
    unit_map = {u["id"]: u["name"] for u in units}
    age = calc_age(user["birth_date"])
    years = calc_years_by_fiscal_year(user["join_date"])
    exp = get_officer_experience(user["id"])

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
        st.write("押されたID:", user["id"])  # ←追加
        st.session_state.selected_user_id = user["id"]
        st.session_state.page = "member_detail"
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
    
    if filter_option == "在籍中":
        users = get_users("active")
    elif filter_option == "退団者":
        users = get_users("retired")
    else:
        users = get_users("all")

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


    # 🔽 ソート実行
    sorted_users = sorted(users, key=sort_key)


    # 🔽 表示
    for u in sorted_users:
        user_card(u)

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