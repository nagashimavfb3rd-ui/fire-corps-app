import streamlit as st
import sqlite3
from datetime import datetime

DB_NAME = "fire_corps.db"


# =========================
# DB接続
# =========================
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# 権限チェック
# =========================
def is_admin():
    return (
        "user" in st.session_state and
        st.session_state.user and
        st.session_state.user["auth_role"] == "admin"
    )


# =========================
# テーブル作成
# =========================
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS handover_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT NOT NULL,
        created_by INTEGER,
        created_at DATE NOT NULL
    )
    """)

    conn.commit()
    conn.close()


# =========================
# 取得
# =========================
def get_logs(category=None):
    conn = get_connection()
    cursor = conn.cursor()

    if category and category != "all":
        cursor.execute("""
            SELECT * FROM handover_logs
            WHERE category=?
            ORDER BY created_at DESC
        """, (category,))
    else:
        cursor.execute("""
            SELECT * FROM handover_logs
            ORDER BY created_at DESC
        """)

    data = cursor.fetchall()
    conn.close()
    return data


# =========================
# 追加
# =========================
def add_log(title, content, category, user_id, created_at):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO handover_logs (
            title, content, category, created_by, created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        title,
        content,
        category,
        user_id,
        created_at.strftime("%Y-%m-%d")
    ))

    conn.commit()
    conn.close()


# =========================
# 更新
# =========================
def update_log(log_id, title, content, category):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE handover_logs
        SET title=?, content=?, category=?
        WHERE id=?
    """, (title, content, category, log_id))

    conn.commit()
    conn.close()


# =========================
# 削除
# =========================
def delete_log(log_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM handover_logs
        WHERE id=?
    """, (log_id,))

    conn.commit()
    conn.close()


# =========================
# UI
# =========================
def handover_panel():
    st.subheader("📜 引き継ぎ管理")

    if not is_admin():
        st.error("管理者のみアクセス可能です")
        return

    # =========================
    # カテゴリフィルタ
    # =========================
    category_filter = st.selectbox(
        "カテゴリフィルタ",
        ["すべて", "備品情報", "運用変更記録", "その他"]
    )
    
    filter_map = {
        "備品情報": "equipment_info",
        "運用変更記録": "operation_change",
        "その他": "other"
    }

    # =========================
    # 新規追加
    # =========================
    st.markdown("## ➕ 新規追加")

    title = st.text_input("タイトル")
    category = st.selectbox(
        "カテゴリ",
        ["備品情報", "運用変更記録", "その他"],
        key="create_category"
    )
    log_date = st.date_input("日付")
    content = st.text_area("内容")

    if st.button("追加", use_container_width=True):

        if not title or not content:
            st.error("タイトルと内容は必須です")
        else:
            category_map = {
                "備品情報": "equipment_info",
                "運用変更記録": "operation_change",
                "その他": "other"
            }
            add_log(
                title,
                content,
                category_map[category],
                st.session_state.user["id"],
                log_date
            )
            st.success("追加しました")
            st.rerun()

    # =========================
    # 一覧表示
    # =========================
    st.markdown("---")
    st.subheader("📋 一覧")

    logs = get_logs(
        None if category_filter == "すべて"
        else filter_map[category_filter]
    )

    for log in logs:
        st.markdown("---")

        icon_map = {
            "equipment_info": "🔧 備品情報",
            "operation_change": "🔄 運用変更",
            "other": "📌 その他"
        }

        st.write(f"{icon_map.get(log['category'], '📌')} {log['title']}")
        st.caption(f"📅 {log['created_at']}（{log['category']}）")

        with st.expander("詳細を見る"):
            st.write(log["content"])

            col1, col2 = st.columns(2)

            # =========================
            # 編集
            # =========================
            with col1:
                if st.button("編集", key=f"edit_{log['id']}"):
                    st.session_state.edit_log = log["id"]
                    st.rerun()

            # =========================
            # 削除
            # =========================
            with col2:
                if st.button("削除", key=f"del_{log['id']}"):
                    delete_log(log["id"])
                    st.success("削除しました")
                    st.rerun()

    # =========================
    # 編集UI
    # =========================
    if "edit_log" in st.session_state:
        edit_id = st.session_state.edit_log

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM handover_logs WHERE id=?", (edit_id,))
        log = cursor.fetchone()
        conn.close()

        if log:
            st.markdown("---")
            st.subheader("✏️ 編集")

            new_title = st.text_input("タイトル", value=log["title"])
            reverse_map = {
                "equipment_info": "備品情報",
                "operation_change": "運用変更記録",
                "other": "その他"
            }
            
            new_category_jp = st.selectbox(
                "カテゴリ",
                ["備品情報", "運用変更記録", "その他"],
                index=list(reverse_map.values()).index(reverse_map[log["category"]])
            )
            
            new_content = st.text_area("内容", value=log["content"])

            col1, col2 = st.columns(2)

            if col1.button("更新"):
                reverse_map = {
                    "備品情報": "equipment_info",
                    "運用変更記録": "operation_change",
                    "その他": "other"
                }
                
                update_log(
                    edit_id,
                    new_title,
                    new_content,
                    reverse_map[new_category_jp]
                )
                del st.session_state.edit_log
                st.success("更新しました")
                st.rerun()

            if col2.button("キャンセル"):
                del st.session_state.edit_log
                st.rerun()

# =========================
# 本体
# =========================
def main():
    init_db()
    handover_panel()

# =========================
# 実行
# =========================
if __name__ == "__main__":
    main()