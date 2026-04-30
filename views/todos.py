import streamlit as st
from db import (
    get_todos_supabase,
    add_todo_supabase,
    complete_todo_supabase
)
from datetime import datetime


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
            complete_todo_supabase(todo["id"])
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
            add_todo_supabase(title, str(deadline))
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

    todos = get_todos_supabase()

    if not todos:
        st.info("ToDoがありません")
        return

    for t in todos:
        todo_card(t)


if __name__ == "__main__":
    main()