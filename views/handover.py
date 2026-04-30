import streamlit as st
from db import (
    get_logs_supabase,
    add_log_supabase,
    update_log_supabase,
    delete_log_supabase,
    get_log_by_id_supabase
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
            add_log_supabase(
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

    logs = get_logs_supabase(
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
                    delete_log_supabase(log["id"])
                    st.success("削除しました")
                    st.rerun()

    # =========================
    # 編集UI
    # =========================
    if "edit_log" in st.session_state:
        edit_id = st.session_state.edit_log

        log = get_log_by_id_supabase(edit_id)

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
                
                update_log_supabase(
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
    handover_panel()

# =========================
# 実行
# =========================
if __name__ == "__main__":
    main()