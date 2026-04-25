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
# データ取得
# =========================
def get_todos():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM todos
        ORDER BY status ASC, deadline DESC
    """)

    data = cursor.fetchall()
    conn.close()
    return data


# =========================
# ToDo追加
# =========================
def add_todo(title, deadline):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO todos (title, deadline, status)
        VALUES (?, ?, 'open')
    """, (title, deadline))

    conn.commit()
    conn.close()


# =========================
# 完了処理
# =========================
def complete_todo(todo_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE todos
        SET status='done'
        WHERE id=?
    """, (todo_id,))

    conn.commit()
    conn.close()


# =========================
# UI（カード）
# =========================
def todo_card(todo):
    st.markdown("---")

    status = todo["status"]
    is_done = status == "done"

    # 状態表示
    if is_done:
        st.success(f"✔ 完了：{todo['title']}")
    else:
        st.subheader(f"📝 {todo['title']}")

    st.write(f"📅 期限：{todo['deadline'] or '未設定'}")

    # 状態バッジ
    if status == "open":
        st.warning("進行中")
    else:
        st.success("完了")

    # 完了ボタン（adminのみ）
    if not is_done and is_admin():
        if st.button("完了にする", key=f"done_{todo['id']}", use_container_width=True):
            complete_todo(todo["id"])
            st.rerun()


# =========================
# 追加UI（adminのみ）
# =========================
def add_todo_ui():
    st.markdown("## ➕ ToDo追加（管理者）")

    title = st.text_input("内容")
    deadline = st.date_input("期限")

    if st.button("追加", use_container_width=True):
        if title:
            add_todo(title, str(deadline))
            st.success("追加しました")
            st.rerun()
        else:
            st.error("内容を入力してください")


# =========================
# メイン
# =========================
def main():
    st.title("📋 ToDo管理")

    # 権限表示
    if not is_admin():
        st.warning("※ このページは管理者のみ操作可能です")

    # 追加（adminのみ）
    if is_admin():
        add_todo_ui()

    todos = get_todos()

    if not todos:
        st.info("ToDoがありません")
        return

    for t in todos:
        todo_card(t)


if __name__ == "__main__":
    main()