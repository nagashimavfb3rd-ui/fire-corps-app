# db.py
import os
import hashlib
import secrets
import shutil
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def save_login_token(user_id, token):
    supabase.table("users")\
        .update({"auth_token": token})\
        .eq("id", user_id)\
        .execute()


def get_user_by_token(token):
    res = supabase.table("users")\
        .select("*")\
        .eq("auth_token", token)\
        .execute()

    if res.data:
        return res.data[0]

    return None

def delete_login_token(token):
    supabase.table("users").update({
        "auth_token": None
    }).eq("auth_token", token).execute()

# =========================
# Supabase版 users取得
# =========================
def get_users_supabase():
    res = supabase.table("users").select("*").execute()
    return res.data

# =========================
# Supabase版 user作成
# =========================
def create_user_supabase(user_data):

    # login_id生成（安全版）
    if not user_data.get("login_id"):
        user_data["login_id"] = generate_login_id_supabase()

    # passwordが来ている場合だけハッシュ化
    if "password" in user_data and user_data["password"]:
        password_hash, salt = create_password_hash(user_data["password"])
        user_data["password_hash"] = password_hash
        user_data["salt"] = salt
        user_data.pop("password")

    # Supabaseへ送信
    return supabase.table("users").insert(user_data).execute()

def generate_login_id_supabase():
    res = supabase.table("users").select("login_id").execute().data

    max_num = 0

    for u in res:
        login_id = u.get("login_id", "")
        if login_id.startswith("nagashima"):
            try:
                num = int(login_id.replace("nagashima", ""))
                max_num = max(max_num, num)
            except:
                pass

    return f"nagashima{max_num + 1:03d}"


def change_password_supabase(user_id, current_password, new_password):

    # ユーザー取得
    res = supabase.table("users") \
        .select("password_hash, salt") \
        .eq("id", user_id) \
        .single() \
        .execute()

    if not res.data:
        return False, "ユーザーが存在しません"

    user = res.data

    # 現在パスワード確認
    if not verify_password(current_password, user["password_hash"], user["salt"]):
        return False, "現在のパスワードが違います"

    # 新パスワード生成
    new_hash, new_salt = create_password_hash(new_password)

    # 更新
    supabase.table("users") \
        .update({
            "password_hash": new_hash,
            "salt": new_salt
        }) \
        .eq("id", user_id) \
        .execute()

    return True, "変更しました"

def admin_reset_password_supabase(target_user_id, new_password):

    new_hash, new_salt = create_password_hash(new_password)

    supabase.table("users") \
        .update({
            "password_hash": new_hash,
            "salt": new_salt
        }) \
        .eq("id", target_user_id) \
        .execute()

    return True, "初期化しました"



def get_units_supabase():
    return supabase.table("units").select("*").execute().data

def create_unit_supabase(data):
    return supabase.table("units").insert(data).execute()

def update_unit_supabase(unit_id, data):
    return supabase.table("units").update(data).eq("id", unit_id).execute()

def delete_unit_supabase(unit_id):
    return supabase.table("units").delete().eq("id", unit_id).execute()

def get_units_full(target_date):
    # ① units取得
    units_res = supabase.table("units").select("*").execute()
    units = units_res.data

    # ② users取得（期間フィルタは後で処理）
    users_res = supabase.table("users").select("*").execute()
    users = users_res.data

    result = []

    for u in units:

        member_names = []
        member_count = 0

        for us in users:

            if us["unit_id"] != u["id"]:
                continue

            # 在籍チェック
            if us["join_date"] and us["join_date"] > str(target_date):
                continue

            if us["leave_date"] and us["leave_date"] != "" and us["leave_date"] <= str(target_date):
                continue

            member_count += 1
            member_names.append(f"{us['name']}（{us['login_id']}）")

        result.append({
            "id": u["id"],
            "name": u["name"],
            "required_members": u["required_members"] or 0,
            "member_count": member_count,
            "member_names": "、".join(member_names) if member_names else "なし"
        })

    return result

def get_user_supabase(user_id):
    return supabase.table("users").select("*").eq("id", user_id).single().execute().data


def get_fields_supabase():
    return supabase.table("user_fields") \
        .select("*") \
        .order("sort_order") \
        .execute().data


def get_user_field_values_supabase(user_id):
    fields = get_fields_supabase()

    values = supabase.table("user_field_values") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute().data

    value_map = {
        v["field_id"]: v["value"]
        for v in values
    }

    result = []

    for f in fields:
        result.append({
            "field_id": f["id"],
            "field_name": f["field_name"],
            "value": value_map.get(f["id"], "")
        })

    return result

def create_field_supabase(field_name, field_type, sort_order=0):
    return supabase.table("user_fields").insert({
        "field_name": field_name,
        "field_type": field_type,
        "sort_order": sort_order
    }).execute()

def update_field_supabase(field_id, data):
    return supabase.table("user_fields") \
        .update(data) \
        .eq("id", field_id) \
        .execute()

def delete_field_supabase(field_id):

    # 値も一緒に削除（重要）
    supabase.table("user_field_values") \
        .delete() \
        .eq("field_id", field_id) \
        .execute()

    return supabase.table("user_fields") \
        .delete() \
        .eq("id", field_id) \
        .execute()

def update_field_order_supabase(field_orders):
    """
    field_orders = [
        {"id": 1, "sort_order": 1},
        {"id": 2, "sort_order": 2}
    ]
    """

    for f in field_orders:
        supabase.table("user_fields") \
            .update({"sort_order": f["sort_order"]}) \
            .eq("id", f["id"]) \
            .execute()

def get_user_full_profile_supabase(user_id):

    user = get_user_supabase(user_id)
    fields = get_user_field_values_supabase(user_id)

    return {
        "user": user,
        "fields": fields
    }

def get_field_options_supabase(field_id):
    return supabase.table("user_field_options") \
        .select("*") \
        .eq("field_id", field_id) \
        .execute().data

# =========================
# 訓練種別（Supabase）
# =========================
def get_training_types_supabase():
    res = supabase.table("training_types").select("*").execute()
    return res.data


def create_training_type_supabase(name):
    supabase.table("training_types").insert({
        "name": name
    }).execute()


def delete_training_type_supabase(type_id):
    supabase.table("training_types").delete().eq("id", type_id).execute()


# =========================
# 役員変更系（Supabase）
# =========================
def update_user_role_supabase(user_id, auth_role):
    supabase.table("users") \
        .update({"auth_role": auth_role}) \
        .eq("id", user_id) \
        .execute()


def update_role_with_history_supabase(user_id, new_role, change_date):

    # 現在のユーザー取得
    user = supabase.table("users") \
        .select("role") \
        .eq("id", user_id) \
        .single() \
        .execute()

    current_role = user.data["role"]

    target_roles = ["分団長", "副分団長"]

    # =========================
    # ① 前の役職終了
    # =========================
    if current_role in target_roles and new_role != current_role:
        supabase.table("role_history") \
            .update({"end_date": change_date}) \
            .eq("user_id", user_id) \
            .eq("role", current_role) \
            .is_("end_date", None) \
            .execute()

    # =========================
    # ② 新しい役職開始
    # =========================
    if new_role != current_role and new_role in target_roles:
        supabase.table("role_history") \
            .insert({
                "user_id": user_id,
                "role": new_role,
                "start_date": change_date
            }) \
            .execute()

    # =========================
    # ③ users更新
    # =========================
    supabase.table("users") \
        .update({"role": new_role}) \
        .eq("id", user_id) \
        .execute()


# =========================
# 役員履歴系（Supabase）
# =========================
def get_role_history_supabase(role_filter=None):
    query = supabase.table("role_history").select("*, users(name)")

    if role_filter and role_filter != "すべて":
        query = query.eq("role", role_filter)
    else:
        query = query.in_("role", ["分団長", "副分団長"])

    query = query.order("end_date", desc=True)

    return query.execute().data


def update_role_history_supabase(id, role, start_date, end_date):
    return supabase.table("role_history").update({
        "role": role,
        "start_date": start_date,
        "end_date": end_date
    }).eq("id", id).execute()


def delete_role_history_supabase(id):
    return supabase.table("role_history").delete().eq("id", id).execute()


def get_officer_experience_supabase():
    res = supabase.table("role_history") \
        .select("user_id, role") \
        .in_("role", ["分団長", "副分団長"]) \
        .execute()

    result = {}

    for row in res.data:
        uid = row["user_id"]
        role = row["role"]

        if uid not in result:
            result[uid] = {"分団長": False, "副分団長": False}

        result[uid][role] = True

    return result


# =========================
# 報酬設定系（Supabase）
# =========================
def get_role_rewards_supabase():
    return supabase.table("role_rewards").select("*").execute().data


def update_role_reward_supabase(role, amount):
    return supabase.table("role_rewards").update({
        "amount": amount
    }).eq("role", role).execute()


# =========================
# マイ報酬系（Supabase）
# =========================
def get_fiscal_years_supabase():
    res = supabase.table("trainings") \
        .select("fiscal_year") \
        .execute()

    years = list(set(r["fiscal_year"] for r in res.data if r["fiscal_year"]))
    return sorted(years, reverse=True)


def get_user_actual_reward_supabase(user_id, fiscal_year):
    start, end = get_fiscal_year_range(fiscal_year)

    rows = supabase.table("training_attendance") \
        .select("actual_status, trainings(date,title,reward_amount)") \
        .eq("user_id", user_id) \
        .gte("trainings.date", start) \
        .lte("trainings.date", end) \
        .execute().data

    total = 0
    records = []

    for r in rows:
        t = r["trainings"]
        amount = t["reward_amount"] or 0

        if r["actual_status"] == "present":
            total += amount

        records.append({
            "date": t["date"],
            "title": t["title"],
            "status": r["actual_status"],
            "source": "actual",
            "amount": amount if r["actual_status"] == "present" else 0
        })

    return total, records


def get_user_estimated_reward_supabase(user_id, fiscal_year):
    start, end = get_fiscal_year_range(fiscal_year)

    rows = supabase.table("training_attendance") \
        .select("attend_status, actual_status, trainings(date,title,reward_amount)") \
        .eq("user_id", user_id) \
        .gte("trainings.date", start) \
        .lte("trainings.date", end) \
        .execute().data

    total = 0
    records = []

    for r in rows:
        t = r["trainings"]

        if r["actual_status"] is not None:
            status = r["actual_status"]
            source = "actual"
        else:
            status = r["attend_status"]
            source = "planned"

        amount = t["reward_amount"] or 0

        if status == "present":
            total += amount

        records.append({
            "date": t["date"],
            "title": t["title"],
            "status": status,
            "source": source,
            "amount": amount if status == "present" else 0
        })

    return total, records


def get_role_reward_supabase(user_id, fiscal_year):
    # 今は簡易版（usersのroleだけ使う）
    user = supabase.table("users") \
        .select("role") \
        .eq("id", user_id) \
        .single() \
        .execute().data

    role = user.get("role") or "団員"

    res = supabase.table("role_rewards") \
        .select("amount") \
        .eq("role", role) \
        .execute()

    if res.data:
        return res.data[0]["amount"]

    return 0


def get_user_reward_summary_supabase(user_id, fiscal_year):

    actual_total, actual_records = get_user_actual_reward_supabase(user_id, fiscal_year)
    estimated_total, estimated_records = get_user_estimated_reward_supabase(user_id, fiscal_year)
    role_reward = get_role_reward_supabase(user_id, fiscal_year)

    return {
        "actual_total": actual_total,
        "estimated_total": estimated_total,
        "role_reward": role_reward,
        "grand_total": estimated_total + role_reward,
        "records": estimated_records
    }


def get_user_specific_training_reward_supabase(user_id, fiscal_year, target_titles):

    start, end = get_fiscal_year_range(fiscal_year)

    rows = supabase.table("training_attendance") \
        .select("attend_status, actual_status, trainings(date,title,reward_amount)") \
        .eq("user_id", user_id) \
        .in_("trainings.title", target_titles) \
        .gte("trainings.date", start) \
        .lte("trainings.date", end) \
        .execute().data

    actual_total = 0
    estimated_total = 0
    records = []

    for r in rows:
        t = r["trainings"]
        
        if not t:
            continue  # ←これ重要
        
        amount = t["reward_amount"] or 0

        if r["actual_status"] == "present":
            actual_total += amount

        if r["actual_status"] is not None:
            status = r["actual_status"]
        else:
            status = r["attend_status"]

        if status == "present":
            estimated_total += amount

        records.append({
            "date": t["date"],
            "title": t["title"],
            "status": status,
            "amount": amount
        })

    return actual_total, estimated_total, records


def get_hose_reward_summary_supabase(user_id, fiscal_year):

    start, end = get_fiscal_year_range(fiscal_year)

    rows = supabase.table("training_hose_members") \
        .select("hose_count, training_hose(training_id, trainings(date))") \
        .eq("user_id", user_id) \
        .gte("training_hose.trainings.date", start) \
        .lte("training_hose.trainings.date", end) \
        .execute().data

    total = sum(r["hose_count"] for r in rows if r["hose_count"])

    return total, total * 1000


# =========================
# todo系（Supabase）
# =========================
def get_todos_supabase():
    return supabase.table("todos") \
        .select("*") \
        .order("status") \
        .order("deadline", desc=True) \
        .execute().data


def add_todo_supabase(title, deadline):
    supabase.table("todos").insert({
        "title": title,
        "deadline": deadline,
        "status": "open"
    }).execute()


def complete_todo_supabase(todo_id):
    supabase.table("todos") \
        .update({"status": "done"}) \
        .eq("id", todo_id) \
        .execute()


# =========================
# 引継系（Supabase）
# =========================
# 取得
def get_logs_supabase(category=None):
    query = supabase.table("handover_logs").select("*").order("created_at", desc=True)

    if category:
        query = query.eq("category", category)

    res = query.execute()
    return res.data


# 追加
def add_log_supabase(title, content, category, user_id, created_at):
    supabase.table("handover_logs").insert({
        "title": title,
        "content": content,
        "category": category,
        "created_by": user_id,
        "created_at": created_at.strftime("%Y-%m-%d")
    }).execute()


# 更新
def update_log_supabase(log_id, title, content, category):
    supabase.table("handover_logs").update({
        "title": title,
        "content": content,
        "category": category
    }).eq("id", log_id).execute()


# 削除
def delete_log_supabase(log_id):
    supabase.table("handover_logs").delete().eq("id", log_id).execute()


# 単体取得（編集用）
def get_log_by_id_supabase(log_id):
    res = supabase.table("handover_logs").select("*").eq("id", log_id).single().execute()
    return res.data


# =========================
# 訓練作成・更新系（Supabase）
# =========================
def create_training_supabase(data, target_user_ids):

    data["fiscal_year"] = get_fiscal_year(data["date"])

    res = supabase.table("trainings") \
        .insert(data) \
        .execute()

    training_id = res.data[0]["id"]

    # 中間テーブル
    for uid in target_user_ids:
        supabase.table("training_targets").insert({
            "training_id": training_id,
            "user_id": uid
        }).execute()


def update_training_supabase(training_id, data):

    data["fiscal_year"] = get_fiscal_year(data["date"])

    supabase.table("trainings") \
        .update(data) \
        .eq("id", training_id) \
        .execute()

def delete_training_supabase(training_id):

    supabase.table("training_targets") \
        .delete() \
        .eq("training_id", training_id) \
        .execute()

    supabase.table("trainings") \
        .delete() \
        .eq("id", training_id) \
        .execute()


def copy_training_supabase(t):

    data = dict(t)
    data.pop("id", None)
    data["title"] = data["title"] + "（コピー）"
    data["status"] = "planned"
    data["fiscal_year"] = get_fiscal_year(data["date"])

    res = supabase.table("trainings").insert(data).execute()
    new_id = res.data[0]["id"]

    # targetsコピー
    targets = supabase.table("training_targets") \
        .select("user_id") \
        .eq("training_id", t["id"]) \
        .execute()

    for r in targets.data:
        supabase.table("training_targets").insert({
            "training_id": new_id,
            "user_id": r["user_id"]
        }).execute()


def update_training_targets_supabase(training_id, user_ids):
    # ① 既存削除
    supabase.table("training_targets")\
        .delete()\
        .eq("training_id", training_id)\
        .execute()

    # ② 新規INSERT（まとめて入れる）
    if user_ids:
        data = [
            {"training_id": training_id, "user_id": uid}
            for uid in user_ids
        ]

        supabase.table("training_targets")\
            .insert(data)\
            .execute()


def get_training_target_ids_supabase(training_id):
    res = supabase.table("training_targets")\
        .select("user_id")\
        .eq("training_id", training_id)\
        .execute()

    return [r["user_id"] for r in res.data]


def get_training_target_names_supabase(training_id):
    res = supabase.table("training_targets")\
        .select("users(name)")\
        .eq("training_id", training_id)\
        .execute()

    return [r["users"]["name"] for r in res.data if r.get("users")]


def get_all_trainings_ordered_supabase():
    res = supabase.table("trainings") \
        .select("id,date") \
        .order("date").order("id") \
        .execute()

    return res.data or []


def get_prev_next_training(training_id):
    trainings = get_all_trainings_ordered_supabase()

    ids = [t["id"] for t in trainings]

    if training_id not in ids:
        return None, None

    idx = ids.index(training_id)

    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if idx < len(ids) - 1 else None

    return prev_id, next_id


# =========================
# 訓練一覧系（Supabase）
# =========================
def get_trainings_supabase(fiscal_year=None):
    query = supabase.table("trainings")\
        .select("*")\
        .order("date", desc=True)\
        .order("meeting_time", desc=True, nullsfirst=False)

    if fiscal_year:
        query = query.eq("fiscal_year", fiscal_year)

    res = query.execute()
    return res.data


def get_attendance_count_supabase(training_id):
    res = supabase.table("training_attendance") \
        .select("attend_status") \
        .eq("training_id", training_id) \
        .execute()

    present = sum(1 for r in res.data if r["attend_status"] == "present")
    absent = sum(1 for r in res.data if r["attend_status"] == "absent")

    return present, absent


def save_attendance_supabase(training_id, user_id, status, mode="planned"):
    column = "attend_status" if mode == "planned" else "actual_status"

    supabase.table("training_attendance").upsert(
        {
            "training_id": training_id,
            "user_id": user_id,
            column: status
        },
        on_conflict="training_id,user_id"
        ).execute()


def get_incidents_map_supabase():
    res = supabase.table("training_incident") \
        .select("training_id, has_incident") \
        .execute()

    return {r["training_id"]: r["has_incident"] for r in res.data}


def get_training_years_supabase():
    res = supabase.table("trainings") \
        .select("fiscal_year") \
        .execute()

    years = list(set(r["fiscal_year"] for r in res.data if r["fiscal_year"]))
    return sorted(years, reverse=True)


# =========================
# 訓練詳細系（Supabase）
# =========================
def get_training_supabase(training_id):
    return (
        supabase.table("trainings")
        .select("*")
        .eq("id", training_id)
        .single()
        .execute()
        .data
    )


def get_active_users_supabase(target_date):
    if not target_date:
        return []

    return (
        supabase.table("users")
        .select("*")
        .or_(
            "join_date.is.null,join_date.lte." + target_date
        )
        .or_(
            "leave_date.is.null,leave_date.gte." + target_date
        )
        .execute()
        .data
    )


def get_attendance_supabase(training_id):
    return (
        supabase.table("training_attendance")
        .select("*")
        .eq("training_id", training_id)
        .execute()
        .data
    )


def save_meal_supabase(training_id, user_id, meal_option):
    supabase.table("training_attendance").upsert(
        {
            "training_id": training_id,
            "user_id": user_id,
            "meal_option": meal_option
        },
        on_conflict="training_id,user_id"
    ).execute()


def get_hose_counts_supabase(hose_id):
    rows = (
        supabase.table("training_hose_members")
        .select("user_id,hose_count")
        .eq("hose_id", hose_id)
        .execute()
        .data
    )

    return {r["user_id"]: r["hose_count"] for r in rows}


def create_training_hose_supabase(training_id, hose_count):
    res = supabase.table("training_hose").insert({
        "training_id": training_id,
        "hose_count": hose_count
    }).execute()

    return res.data[0]["id"]


def save_hose_count_supabase(hose_id, user_id, count):
    supabase.table("training_hose_members").upsert(
        {
            "hose_id": hose_id,
            "user_id": user_id,
            "hose_count": count
        },
        on_conflict="hose_id,user_id"
    ).execute()


def get_incident_supabase(training_id):
    data = (
        supabase.table("training_incident")
        .select("*")
        .eq("training_id", training_id)
        .order("id", desc=True)
        .limit(1)
        .execute()
        .data
    )

    return data[0] if data else None


def save_incident_supabase(training_id, data):
    payload = {
        "training_id": training_id,
        **data
    }

    supabase.table("training_incident").upsert(
        payload,
        on_conflict="training_id"
    ).execute()


def get_attendance_count_supabase(training_id):
    rows = (
        supabase.table("training_attendance")
        .select("attend_status")
        .eq("training_id", training_id)
        .execute()
        .data
    )

    present = sum(1 for r in rows if r["attend_status"] == "present")
    absent = sum(1 for r in rows if r["attend_status"] == "absent")

    return present, absent


def get_training_target_ids_supabase(training_id):
    res = supabase.table("training_targets") \
        .select("user_id") \
        .eq("training_id", training_id) \
        .execute()

    return [r["user_id"] for r in res.data]


def get_target_users_frontend(training, users, targets, target_date):

    roles = targets.get("roles")
    individual_ids = targets.get("individual_ids") or []

    # -------------------------
    # ① 個別指定がある場合
    # -------------------------
    if individual_ids:
        return [u for u in users if u["id"] in individual_ids]

    # -------------------------
    # ② 役職指定がある場合
    # -------------------------
    if roles:
        role_list = [r.strip() for r in roles.split(",")]
        return [u for u in users if u.get("role") in role_list]

    # -------------------------
    # ③ 全員対象
    # -------------------------
    return users


def is_active(user, target_date):
    return (
        not user["leave_date"]
        or user["leave_date"] == ""
        or user["leave_date"] >= target_date
    )


def authenticate_user_supabase(login_id, password):
    res = supabase.table("users").select("*").eq("login_id", login_id).execute()

    if not res.data:
        return None

    user = res.data[0]

    if verify_password(password, user["password_hash"], user["salt"]):
        return user

    return None


# 実績報告 取得
def get_training_report_supabase(training_id):
    res = supabase.table("training_reports") \
        .select("*") \
        .eq("training_id", training_id) \
        .execute()

    if res.data:
        return res.data[0]
    return None


# 実績報告 保存（UPSERT）
def save_training_report_supabase(training_id, data):
    payload = {
        "training_id": training_id,
        **data
    }

    supabase.table("training_reports") \
        .upsert(payload, on_conflict="training_id") \
        .execute()


# 現在の分団長取得
def get_current_leader_supabase():

    res = supabase.table("role_history") \
        .select("user_id, role, end_date, users(name)") \
        .eq("role", "分団長") \
        .is_("end_date", None) \
        .limit(1) \
        .execute()

    if res.data:
        return res.data[0]["users"]["name"]

    return "（未設定）"


# =========================
# ホーム画面系supabase
# =========================
def get_next_training_supabase():
    return supabase.table("trainings")\
        .select("*")\
        .gte("date", datetime.now().strftime("%Y-%m-%d"))\
        .order("date", desc=False)\
        .order("meeting_time", desc=False)\
        .limit(1)\
        .execute().data[0] if supabase.table("trainings").select("*").execute().data else None


def get_user_attendance_supabase(training_id, user_id):
    res = supabase.table("training_attendance")\
        .select("attend_status")\
        .eq("training_id", training_id)\
        .eq("user_id", user_id)\
        .single()\
        .execute()

    return res.data["attend_status"] if res.data else None


def get_user_meal_option_supabase(training_id, user_id):
    res = supabase.table("training_attendance")\
        .select("meal_option")\
        .eq("training_id", training_id)\
        .eq("user_id", user_id)\
        .execute()

    if res.data:
        return res.data[0].get("meal_option")

    return None


def get_current_fiscal_year():
    today = datetime.today()
    return today.year if today.month >= 4 else today.year - 1


# =========================
# パスワードハッシュ
# =========================
def create_password_hash(password: str):
    salt = secrets.token_hex(16)
    hash_val = hashlib.sha256((password + salt).encode()).hexdigest()
    return hash_val, salt


def verify_password(password: str, hash_val: str, salt: str):
    check = hashlib.sha256((password + salt).encode()).hexdigest()
    return check == hash_val


def update_user_supabase(user_id, data, dynamic_values, editor):

    # =========================
    # ① 旧データ取得
    # =========================
    res = supabase.table("users") \
        .select("*") \
        .eq("id", user_id) \
        .execute()

    if not res.data:
        return  # ユーザーが存在しない場合は何もしない

    old_user = res.data[0]

    # =========================
    # ② 基本項目：履歴
    # =========================
    fields = [
        "name", "role", "unit_id", "license_type",
        "birth_date", "join_date", "leave_date",
        "address", "phone", "email"
    ]

    history_rows = []

    for f in fields:
        old_val = str(old_user.get(f, ""))
        new_val = str(data.get(f, ""))

        if old_val != new_val:
            history_rows.append({
                "user_id": user_id,
                "changed_by": editor,
                "field_name": f,
                "old_value": old_val,
                "new_value": new_val
            })

    # =========================
    # ③ 基本項目：更新
    # =========================
    supabase.table("users") \
        .update({
            "name": data["name"],
            "role": data["role"],
            "unit_id": data["unit_id"],
            "license_type": data["license_type"],
            "birth_date": data["birth_date"],
            "join_date": data["join_date"],
            "leave_date": data["leave_date"],
            "address": data["address"],
            "phone": data["phone"],
            "email": data["email"]
        }) \
        .eq("id", user_id) \
        .execute()

    # =========================
    # ④ 動的項目：旧値取得
    # =========================
    # フィールド一覧取得
    fields = supabase.table("user_fields") \
        .select("*") \
        .execute().data

    # このユーザーの値だけ取得
    values = supabase.table("user_field_values") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute().data

    # field_id → value の辞書
    value_map = {
        v["field_id"]: v["value"]
        for v in values
    }

    old_dynamic = {}

    for f in fields:
        old_dynamic[f["id"]] = value_map.get(f["id"], "")

    # =========================
    # ⑤ 動的項目：履歴＋保存
    # =========================
    for field_id, new_value in dynamic_values.items():

        # field_name取得
        res = supabase.table("user_fields") \
            .select("field_name") \
            .eq("id", field_id) \
            .execute()

        if not res.data:
            continue  # フィールドがない場合はスキップ

        field_name = res.data[0]["field_name"]
        
        old_value = str(old_dynamic.get(field_id, ""))

        if old_value != str(new_value):
            history_rows.append({
                "user_id": user_id,
                "changed_by": editor,
                "field_name": field_name,
                "old_value": old_value,
                "new_value": str(new_value)
            })

        # UPSERT
        supabase.table("user_field_values").upsert(
            {
                "user_id": user_id,
                "field_id": field_id,
                "value": new_value
            },
            on_conflict="user_id,field_id"
        ).execute()

    # =========================
    # ⑥ 履歴まとめてINSERT
    # =========================
    if history_rows:
        supabase.table("user_history").insert(history_rows).execute()



# 年度計算
def get_fiscal_year(date_str):
    from datetime import datetime
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.year if d.month >= 4 else d.year - 1



# =========================
# 報酬計算ロジック
# =========================
# 年度範囲取得
def get_fiscal_year_range(year):
    start = f"{year}-04-01"
    end = f"{year+1}-03-31"
    return start, end