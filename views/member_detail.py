import streamlit as st
import sqlite3
from datetime import datetime
from datetime import date
from db import get_user_field_values
from db import update_user
from db import get_fields
from db import get_units
from db import get_officer_experience
from utils.ui import calc_years_by_fiscal_year

DB_NAME = "fire_corps.db"

def calc_age(birth_date):
    if not birth_date:
        return None

    birth = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()

    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    conn.close()
    return user

def training_count_editor(user_id):
    conn = sqlite3.connect("fire_corps.db")
    conn.row_factory = sqlite3.Row
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
            key=f"detail_train_{user_id}_{t['id']}"
        )

        if st.button("保存", key=f"detail_save_{user_id}_{t['id']}"):

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

def main():
    st.title("👤 団員詳細")

    user_id = st.session_state.get("selected_user_id")
    
    st.write("user_id =", user_id)

    if not user_id:
        st.error("団員が選択されていません")
        st.write(st.session_state)  # デバッグ
        return

    user = get_user(user_id)

    if not user:
        st.error("データが見つかりません")
        return

    # =========================
    # 表示
    # =========================
    label_map = {
        "name": "名前",
        "role": "役職",
        "unit_id": "自治会",
        "license_type": "免許",
        "address": "住所",
        "phone": "電話",
        "email": "メール",
        "birth_date": "生年月日",
        "join_date": "入団日",
        "leave_date": "退団日",
    }

    # =========================
    # 権限チェック
    # =========================
    current_user = st.session_state.get("user")

    is_admin = current_user and current_user["auth_role"] == "admin"
    is_self = current_user and current_user["id"] == user["id"]

    # =========================
    # 編集モード初期化
    # =========================
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False
    
    # 外部からの遷移対応
    if st.session_state.get("open_edit"):
        st.session_state.edit_mode = True
        st.session_state.open_edit = False

    # =========================
    # 編集ボタン
    # =========================
    if is_admin or is_self:
        if st.button("✏️ 編集", use_container_width=True):
            st.session_state.edit_mode = True
            st.rerun()

    # =========================
    # 表示 or 編集切り替え
    # =========================
    if st.session_state.edit_mode and (is_admin or is_self):

        st.subheader(f"✏️ {user['name']} を編集")

        units = get_units()
        unit_map = {u["id"]: u["name"] for u in units}
        unit_options = {u["name"]: u["id"] for u in units}
        
        name = st.text_input("名前", value=user["name"])
        
        #　この画面では変更不可
        st.write(f"🎖 役職：{user['role']}")
        role = user["role"]  # 変更させない

        unit_name = st.selectbox(
            "自治会",
        list(unit_options.keys()),
        index=list(unit_options.keys()).index(unit_map.get(user["unit_id"], list(unit_options.keys())[0]))
        )

        license_options = [
            "なし",
            "普通（3.5t）",
            "準中型（5t限定）：平成29年3月11日以前の普通免許",
            "準中型（7.5t）",
            "中型（8t限定）：平成19年6月1日以前の普通免許",
            "中型（11t）",
            "大型"
        ]
        
        license_type = st.selectbox(
            "免許",
            license_options,
            index=license_options.index(user["license_type"]) if user["license_type"] in license_options else 0
        )

        address = st.text_input("住所", value=user["address"] or "")
        phone = st.text_input("電話", value=user["phone"] or "")
        email = st.text_input("メール", value=user["email"] or "")
        
        birth_date = st.date_input(
            "生年月日",
            value=datetime.strptime(user["birth_date"], "%Y-%m-%d") if user["birth_date"] else datetime.today(),
            min_value=datetime(1900, 1, 1).date(),
            max_value=datetime(2033, 4, 1).date()
        )

        join_date = st.date_input(
            "入団日",
            value=datetime.strptime(user["join_date"], "%Y-%m-%d") if user["join_date"] else datetime.today(),
            min_value=datetime(1900, 1, 1).date(),
            max_value=datetime(2033, 4, 1).date()
        )
        
        leave_date = st.date_input(
            "退団日（未入力なら在籍中）",
            value=datetime.strptime(user["leave_date"], "%Y-%m-%d") if user["leave_date"] else None,
            min_value=datetime(1900, 1, 1).date(),
            max_value=datetime(2033, 4, 1).date()
        )

        values = get_user_field_values(user["id"])
        fields = get_fields()
        inputs = {}
        
        if fields:
            st.markdown("### 📋 追加項目")
        
            for f in fields:
                old_value = next(
                    (v["value"] for v in values if v["field_id"] == f["id"]),
                    ""
                )

                inputs[f["id"]] = st.text_input(
                    f["field_name"],
                    old_value or ""
                )
        
        col1, col2 = st.columns(2)

        if col1.button("保存"):
            data = {
                "name": name,
                "role": role,
                "unit_id": unit_options[unit_name],
                "license_type": license_type,
                "birth_date": str(birth_date),
                "join_date": str(join_date),
                "leave_date": str(leave_date) if leave_date else None,    
                "address": address,
                "phone": phone,
                "email": email
            }

            update_user(
                user["id"],
                data,
                inputs,
                st.session_state.user["name"]
            )

            st.success("保存しました")
            st.session_state.edit_mode = False
            st.rerun()

        if col2.button("キャンセル"):
            st.session_state.edit_mode = False
            st.rerun()
        
        st.markdown("---")
        if is_admin:
            training_count_editor(user_id)

    else:
        # ===== 表示モード =====
        st.subheader(user["name"])

        units = get_units()
        unit_map = {u["id"]: u["name"] for u in units}
        
        for key in user.keys():
            if key in ["id", "password_hash", "salt"]:
                continue

            label = label_map.get(key, key)
            value = user[key]

            # =========================
            # 個別変換（ここが重要）
            # =========================
            if key == "unit_id":
                value = unit_map.get(value, "未所属")

            elif key == "role":
                st.write(f"{label}：{value}")

                # 👇 役員経験をここで表示
                exp = get_officer_experience(user["id"])

                if exp["分団長"] and exp["副分団長"]:
                    exp_text = "分団長・副分団長 両方経験あり"
                elif exp["分団長"]:
                    exp_text = "分団長経験あり"
                elif exp["副分団長"]:
                    exp_text = "副分団長経験あり"
                else:
                    exp_text = "なし"

                st.write(f"役員経験：{exp_text}")

                continue  # ← これ重要！

            elif key == "birth_date":
                age = calc_age(value)
                value = f"{value}（{age}歳）" if value else "-"

            elif key == "join_date":
                years = calc_years_by_fiscal_year(value)
                value = f"{value}（年度末時点で満{years}年）" if value else "-"
            
            elif key == "leave_date":
                value = value if value else "在籍中"

            else:
                value = value if value else "-"

            st.write(f"{label}：{value}")

        values = get_user_field_values(user["id"])

        if values:
            st.markdown("### 📋 追加項目")

            for v in values:
                st.write(f"{v['field_name']}：{v['value'] or '-'}")

    st.markdown("---")

    if st.button("← 戻る", use_container_width=True):
        st.session_state.page = "members"
        st.rerun()