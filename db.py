# db.py
import sqlite3
import os
import hashlib
import secrets
import shutil
import os
from datetime import datetime

DB_NAME = "fire_corps.db"


# =========================
# DB接続
# =========================
def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
           
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=3000;")
    
    return conn


# =========================
# 初期化
# =========================
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # users（団員）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        login_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,

        role TEXT,
        auth_role TEXT DEFAULT 'user',
        unit_id INTEGER,
        
        birth_date TEXT,
        join_date TEXT,
        leave_date TEXT,
        
        address TEXT,
        phone TEXT,
        email TEXT,

        license_type TEXT,
        
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL
    )
    """)
    
    # 項目定義テーブル
    # field_type: text / number / date / select
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_fields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        field_name TEXT NOT NULL,
        field_type TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0
    )
    """)
    
    # 値テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_field_values (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        field_id INTEGER,
        value TEXT,
        UNIQUE(user_id, field_id)
    )
    """)

    # units（自治会）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        required_members INTEGER DEFAULT 0,
        leader_name TEXT,
        leader_phone TEXT,
        leader_term INTEGER,
        leader_start_date TEXT
    )
    """)

    # trainings（訓練）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trainings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,

        date TEXT NOT NULL,
        fiscal_year INTEGER,
        
        start_time TEXT,
        end_time TEXT,
        
        location TEXT,
        
        meeting_point TEXT,
        meeting_time TEXT,
        uniform TEXT,
        
        reward_amount INTEGER,
        
        status TEXT DEFAULT 'planned',
        
        created_by INTEGER,
        
        event_type TEXT DEFAULT 'none',
        
        target_scope TEXT DEFAULT 'all',
        target_roles TEXT,
        target_user_ids TEXT,
        
        required_members INTEGER DEFAULT 0,
        
        note TEXT,
        
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # training_targets（対象団員）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS training_targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        training_id INTEGER,
        user_id INTEGER
    )
    """)

    # attendance（出欠）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS training_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        training_id INTEGER,
        user_id INTEGER,
        
        attend_status TEXT,
        actual_status TEXT, 
        meal_option TEXT,
        
        created_at TEXT,
        
        UNIQUE(training_id, user_id)
    )
    """)
    
    # training_actual_attendance（実出欠）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS training_actual_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        training_id INTEGER,
        user_id INTEGER,
        
        is_present INTEGER,
        
        confirmed_by INTEGER,
        confirmed_at TEXT,
        UNIQUE(training_id, user_id)
    )
    """)

    # training_fuel（給油）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS training_fuel (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        training_id INTEGER,
        
        fuel_done INTEGER,
        fuel_amount REAL,
        odometer INTEGER,
        
        note TEXT,
        recorded_by INTEGER,
        recorded_at TEXT
    )
    """)

    # training_hose（ホース本体）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS training_hose (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        training_id INTEGER,
        
        hose_count INTEGER,
        
        recorded_at TEXT
    )
    """)

    # training_hose（ホース本体）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS training_hose_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hose_id INTEGER,
        user_id INTEGER,
        hose_count INTEGER
    )
    """)

    # training_hose（ホース本体）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS training_incident (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        training_id INTEGER,
        
        has_incident INTEGER,
        
        injury_flag INTEGER,
        traffic_accident_flag INTEGER,
        
        police_called INTEGER,
        reported_to_commander INTEGER,
        reported_to_hq INTEGER,
        
        incident_datetime TEXT,
        incident_location TEXT,
        
        incident_summary TEXT,
        injury_details TEXT,
        damage_details TEXT,
        
        note TEXT,
        
        recorded_at TEXT
        )
    """)

    # todos（ToDo）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        deadline TEXT,
        status TEXT DEFAULT 'open'
    )
    """)

    # role_history（役職履歴）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS role_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        start_date TEXT,
        end_date TEXT
    )
    """)
    
    # user_history（履歴）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        changed_by TEXT,
        field_name TEXT,
        old_value TEXT,
        new_value TEXT,
        changed_at TEXT
    )
    """)
    
    # 役職報酬マスタ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS role_rewards (
        role TEXT PRIMARY KEY,
        amount INTEGER
    )
    """)


    # =========================
    # 訓練種別マスタ
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS training_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    # =========================
    # 団員ごとの訓練回数
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS training_counts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        training_type_id INTEGER,
        count INTEGER DEFAULT 0,
        UNIQUE(user_id, training_type_id)
    )
    """)

    conn.commit()
    conn.close()


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


# =========================
# ユーザー作成
# =========================
def create_user(login_id, name, password, role, auth_role, unit_id,
                birth_date, join_date, leave_date,
                address, phone, email,
                license_type):

    conn = get_connection()
    cursor = conn.cursor()

    password_hash, salt = create_password_hash(password)

    cursor.execute("""
    INSERT INTO users (
        login_id,
        name, role, auth_role, unit_id,
        birth_date, join_date, leave_date,
        address, phone, email,
        license_type,
        password_hash, salt
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        login_id, 
        name, role, auth_role, unit_id,
        birth_date, join_date, leave_date,
        address, phone, email,
        license_type,
        password_hash, salt
    ))

    conn.commit()
    conn.close()

# =========================
# ユーザー作成
# =========================
def is_active_user(user):
    return user["leave_date"] is None or user["leave_date"] == ""

# =========================
# ログインID自動生成
# =========================
def generate_login_id():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(id) FROM users")
    max_id = cursor.fetchone()[0] or 0

    new_id = max_id + 1

    conn.close()

    return f"nagashima{new_id:03d}"

# =========================
# ユーザー更新
# =========================
def update_user(user_id, data, dynamic_values, editor):
    conn = get_connection()
    cursor = conn.cursor()

    # =========================
    # ① 旧基本データ取得
    # =========================
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    old_user = cursor.fetchone()

    # =========================
    # ② 基本項目：履歴
    # =========================
    fields = [
        "name", "role", "unit_id", "license_type",
        "birth_date", "join_date", "leave_date",
        "address", "phone", "email"
    ]

    for f in fields:
        if str(old_user[f]) != str(data[f]):
            add_user_history(
                cursor,
                user_id,
                editor,
                f,
                str(old_user[f]),
                str(data[f])
            )

    # =========================
    # ③ 基本項目：更新
    # =========================
    cursor.execute("""
        UPDATE users
        SET name=?,
            role=?,
            unit_id=?,
            license_type=?,
            birth_date=?,
            join_date=?,
            leave_date=?,
            address=?,
            phone=?,
            email=?
        WHERE id=?
    """, (
        data["name"],
        data["role"],
        data["unit_id"],
        data["license_type"],
        data["birth_date"],
        data["join_date"],
        data["leave_date"],
        data["address"],
        data["phone"],
        data["email"],
        user_id
    ))

    # =========================
    # ④ 動的項目：旧値取得
    # =========================
    cursor.execute("""
        SELECT f.field_name, v.value
        FROM user_fields f
        LEFT JOIN user_field_values v
        ON f.id = v.field_id AND v.user_id = ?
    """, (user_id,))
    
    rows = cursor.fetchall()
    old_dynamic = {
        r["field_name"]: r["value"]or ""
        for r in rows
    }

    # =========================
    # ⑤ 動的項目：履歴＋保存
    # =========================
    for field_id, new_value in dynamic_values.items():

        # field_name取得
        cursor.execute(
            "SELECT field_name FROM user_fields WHERE id=?",
            (field_id,)
        )
        field_name = cursor.fetchone()["field_name"]

        old_value = old_dynamic.get(field_name, "")

        if str(old_value) != str(new_value):
            add_user_history(
                cursor,
                user_id,
                editor,
                field_name,
                str(old_value),
                str(new_value)
            )

        cursor.execute("""
            INSERT INTO user_field_values (user_id, field_id, value)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, field_id)
            DO UPDATE SET value=excluded.value
        """, (user_id, field_id, new_value))

    conn.commit()
    conn.close()

# =========================
# 役員経験データの取得
# =========================
def get_all_officer_experience():
    conn = get_connection()
    cursor = conn.cursor()

    roles_to_check = ["分団長", "副分団長"]
    placeholders = ",".join(["?"] * len(roles_to_check))

    query = f"""
    SELECT user_id, role FROM role_history
    WHERE role IN ({placeholders})
    """

    cursor.execute(query, roles_to_check)
    rows = cursor.fetchall()
    conn.close()

    result = {}

    for row in rows:
        uid = row["user_id"]
        role = row["role"]

        if uid not in result:
            result[uid] = {"分団長": False, "副分団長": False}

        result[uid][role] = True

    return result

def get_officer_experience(user_id):
    exp_map = get_all_officer_experience()
    return exp_map.get(user_id, {"分団長": False, "副分団長": False})

# =========================
# ログイン認証
# =========================
def authenticate_user(login_id, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE login_id = ?", (login_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return None

    if verify_password(password, user["password_hash"], user["salt"]):
        return dict(user)

    return None

# 年度計算
def get_fiscal_year(date_str):
    from datetime import datetime
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.year if d.month >= 4 else d.year - 1

# =========================
# 可変項目取得
# =========================
def get_user_field_values(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT f.id as field_id, f.field_name, v.value
        FROM user_fields f
        LEFT JOIN user_field_values v
            ON f.id = v.field_id AND v.user_id = ?
        ORDER BY f.sort_order ASC, f.id ASC
    """, (user_id,))

    data = cursor.fetchall()
    conn.close()
    return data

# 可変項目保存
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

#フィールド取得
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

# =========================
# 
# =========================
def get_target_users(training_id, target_date):
    conn = get_connection()
    cursor = conn.cursor()

    users_dict = {}

    # =========================
    # ① 個別指定
    # =========================
    cursor.execute("""
        SELECT u.*
        FROM training_targets tt
        JOIN users u ON tt.user_id = u.id
        WHERE tt.training_id = ?
        AND (u.leave_date IS NULL OR u.leave_date = '' OR u.leave_date >= ?)
    """, (training_id, target_date))

    for u in cursor.fetchall():
        users_dict[u["id"]] = u

    # =========================
    # ② 役職指定
    # =========================
    cursor.execute("SELECT target_roles FROM trainings WHERE id=?", (training_id,))
    training = cursor.fetchone()

    if training and training["target_roles"]:
        roles = training["target_roles"].split(",")

        query = f"""
            SELECT * FROM users
            WHERE role IN ({",".join(["?"] * len(roles))})
            AND (leave_date IS NULL OR leave_date = '' OR leave_date >= ?)
        """
        cursor.execute(query, roles + [target_date])

        for u in cursor.fetchall():
            users_dict[u["id"]] = u

    # =========================
    # ③ 両方なし → 全員
    # =========================
    if not users_dict:
        cursor.execute("""
            SELECT * FROM users
            WHERE leave_date IS NULL OR leave_date = '' OR leave_date >= ?
        """, (target_date,))

        for u in cursor.fetchall():
            users_dict[u["id"]] = u

    conn.close()

    return list(users_dict.values())

# =========================
# 
# =========================
def get_training_target_ids(training_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id
        FROM training_targets
        WHERE training_id=?
    """, (training_id,))

    rows = cursor.fetchall()
    conn.close()

    return [r["user_id"] for r in rows]

# =========================
# 初期データ作成
# =========================
def seed_data():
    conn = get_connection()
    cursor = conn.cursor()

    # =========================
    # ユーザー（admin + 一般団員）シード
    # =========================
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        
        admin_hash, admin_salt = create_password_hash("1234")
        
        cursor.execute("""
        INSERT INTO users (
            login_id,
            name, role, auth_role, unit_id,
            birth_date, join_date, leave_date,
            address, phone, email,
            license_type,
            password_hash, salt
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "admin",
            "管理者",
            "分団長",
            "admin",
            1,
            "1984-01-01",
            "2020-04-01",
            "",
            "未設定",
            "000-0000-0000",
            "admin@test.com",
            "普通（3.5t）",
            admin_hash,
            admin_salt
        ))
        
        cursor.execute("SELECT COUNT(*) FROM user_fields")
        if cursor.fetchone()[0] == 0:
            
            cursor.execute("INSERT INTO user_fields (field_name, field_type) VALUES (?, ?)", ("血液型", "text"))
            cursor.execute("INSERT INTO user_fields (field_name, field_type) VALUES (?, ?)", ("資格", "text"))
            cursor.execute("INSERT INTO user_fields (field_name, field_type) VALUES (?, ?)", ("備考", "text"))

    # =========================
    # 自治会シード
    # =========================
    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] == 0:

        cursor.execute("INSERT INTO units (name) VALUES (?)", ("西川",))
        cursor.execute("INSERT INTO units (name) VALUES (?)", ("千倉",))


    # =========================
    # 訓練シード
    # =========================
    cursor.execute("SELECT COUNT(*) FROM trainings")
    if cursor.fetchone()[0] == 0:
        
        date = "2026-04-15"
        fiscal_year = get_fiscal_year(date)
        
        cursor.execute("""
    INSERT INTO trainings (
        title, date, fiscal_year,
        start_time, end_time,
        location,
        meeting_point, meeting_time, uniform,
        reward_amount, status,
        created_by, event_type,
        target_scope, target_roles, target_user_ids,
        required_members,
        note, created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (
        "基本放水訓練",
        date,
        fiscal_year,
        "09:00",
        "11:00",
        "第1訓練場",
        "車庫",
        "08:30",
        "活動服",
        3000,
        "planned",
        1,
        "none",
        "all",
        None,
        None,
        0,
        ""
    ))
    
    # =========================
    # 訓練種別（初期データ）
    # =========================
    cursor.execute("SELECT COUNT(*) FROM training_types")
    if cursor.fetchone()[0] == 0:
        
        cursor.execute("INSERT INTO training_types (name) VALUES (?)", ("放水訓練",))
        cursor.execute("INSERT INTO training_types (name) VALUES (?)", ("救助訓練",))
        cursor.execute("INSERT INTO training_types (name) VALUES (?)", ("防火訓練",))

    # =========================
    # ToDo
    # =========================
    cursor.execute("SELECT COUNT(*) FROM todos")
    if cursor.fetchone()[0] == 0:

        cursor.execute("""
        INSERT INTO todos (title, deadline, status)
        VALUES (?, ?, ?)
        """, ("備品チェック", "2026-04-18", "open"))

        cursor.execute("""
        INSERT INTO todos (title, deadline, status)
        VALUES (?, ?, ?)
        """, ("消防ポンプ点検", "2026-04-19", "open"))

    # =========================
    # 役員報酬（シード）
    # =========================
    cursor.execute("SELECT COUNT(*) FROM role_rewards")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO role_rewards VALUES (?, ?)", ("分団長", 52185))
        cursor.execute("INSERT INTO role_rewards VALUES (?, ?)", ("副分団長", 39660))
        cursor.execute("INSERT INTO role_rewards VALUES (?, ?)", ("団員", 36500))

    conn.commit()
    conn.close()


# =========================
# 年度取得
# =========================
def get_fiscal_years(conn):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT fiscal_year
        FROM trainings
        WHERE fiscal_year IS NOT NULL
        ORDER BY fiscal_year DESC
    """)

    return [row["fiscal_year"] for row in cursor.fetchall()]

# =========================
# 次回訓練の出欠取得
# =========================
def get_user_attendance(conn, training_id, user_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT attend_status
        FROM training_attendance
        WHERE training_id = ? AND user_id = ?
    """, (training_id, user_id))

    row = cursor.fetchone()
    return row["attend_status"] if row else None

# =========================
# 次回訓練の出欠保存
# =========================
def save_attendance(conn, training_id, user_id, status):
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO training_attendance (
            training_id, user_id, attend_status, created_at
        )
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(training_id, user_id)
        DO UPDATE SET attend_status = excluded.attend_status
    """, (training_id, user_id, status))

    conn.commit()

# =========================
# 次回訓練の取得
# =========================
def get_next_training(conn):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM trainings
        WHERE date >= date('now')
        ORDER BY date ASC
        LIMIT 1
    """)

    return cursor.fetchone()

# =========================
#　報酬取得
# =========================
def get_role_reward(conn, user_id, fiscal_year):

    start, end = get_fiscal_year_range(fiscal_year)
    cursor = conn.cursor()

    # 役職取得
    cursor.execute("""
        SELECT DISTINCT role
        FROM role_history
        WHERE user_id = ?
        AND (
            start_date <= ?
            AND (end_date IS NULL OR end_date >= ?)
        )
    """, (user_id, end, start))

    roles = [row["role"] for row in cursor.fetchall()]

    if not roles:
        # usersテーブルから現在の役職を取得
        cursor.execute("SELECT role FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()

        if row and row["role"]:
            roles = [row["role"]]
        else:
            roles = ["団員"]

    # 金額取得
    placeholders = ",".join(["?"] * len(roles))

    cursor.execute(f"""
        SELECT role, amount
        FROM role_rewards
        WHERE role IN ({placeholders})
    """, roles)

    reward_map = {row["role"]: row["amount"] for row in cursor.fetchall()}

    total = sum(reward_map.get(role, 0) for role in roles)

    return total

# =========================
# 団員の履歴強化
# =========================
def add_user_history(cursor, user_id, changed_by, field_name, old_value, new_value):
    cursor.execute("""
        INSERT INTO user_history (
            user_id, changed_by, field_name, old_value, new_value, changed_at
        )
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (user_id, changed_by, field_name, old_value, new_value))


def get_units():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM units")
    data = cursor.fetchall()
    conn.close()
    return data


# =========================
# 役員の履歴
# =========================
def add_role_history(member_id, role, start_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO role_history (user_id, role, start_date)
        VALUES (?, ?, ?)
    """, (member_id, role, start_date))

    conn.commit()
    conn.close()

# =========================
# 報酬計算ロジック
# =========================


# 年度範囲取得
def get_fiscal_year_range(year):
    start = f"{year}-04-01"
    end = f"{year+1}-03-31"
    return start, end


# =========================
# 実績報酬
# =========================
def get_user_actual_reward(conn, user_id, fiscal_year):

    start, end = get_fiscal_year_range(fiscal_year)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.date, t.title, t.reward_amount, a.actual_status
        FROM trainings t
        JOIN training_attendance a
        ON t.id = a.training_id
        WHERE a.user_id = ?
        AND t.date BETWEEN ? AND ?
        ORDER BY t.date ASC
    """, (user_id, start, end))

    rows = cursor.fetchall()

    total = 0
    records = []

    for row in rows:
        amount = row["reward_amount"] or 0

        if row["actual_status"] == "present":
            total += amount

        records.append({
            "date": row["date"],
            "title": row["title"],
            "status": row["actual_status"],
            "source": "actual",
            "amount": amount if row["actual_status"] == "present" else 0
        })

    return total, records


# =========================
# 見込み報酬
# =========================
def get_user_estimated_reward(conn, user_id, fiscal_year):

    start, end = get_fiscal_year_range(fiscal_year)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.date, t.title, t.reward_amount,
               a.attend_status, a.actual_status
        FROM trainings t
        JOIN training_attendance a
        ON t.id = a.training_id
        WHERE a.user_id = ?
        AND t.date BETWEEN ? AND ?
        ORDER BY t.date ASC
    """, (user_id, start, end))

    rows = cursor.fetchall()

    total = 0
    records = []

    for row in rows:

        # 実績優先
        if row["actual_status"] is not None:
            status = row["actual_status"]
            source = "actual"
        else:
            status = row["attend_status"]
            source = "planned"

        amount = row["reward_amount"] or 0

        if status == "present":
            total += amount

        records.append({
            "date": row["date"],
            "title": row["title"],
            "status": status,
            "source": source,
            "amount": amount if status == "present" else 0
        })

    return total, records




# =========================
# 統合
# =========================
def get_user_reward_summary(conn, user_id, fiscal_year):

    actual_total, actual_records = get_user_actual_reward(conn, user_id, fiscal_year)
    estimated_total, estimated_records = get_user_estimated_reward(conn, user_id, fiscal_year)
    role_reward = get_role_reward(conn, user_id, fiscal_year)

    # 見込み側のrecordsを採用（実績も含まれるため）
    records = estimated_records

    grand_total = estimated_total + role_reward

    return {
        "actual_total": actual_total,
        "estimated_total": estimated_total,
        "role_reward": role_reward,
        "grand_total": grand_total,
        "records": records
    }


# =========================
# ポンプ点検、年末警戒の報酬額取得
# =========================
def get_user_specific_training_reward(conn, user_id, fiscal_year, target_titles):

    start, end = get_fiscal_year_range(fiscal_year)
    cursor = conn.cursor()

    placeholders = ",".join(["?"] * len(target_titles))

    cursor.execute(f"""
        SELECT t.date, t.title, t.reward_amount,
               a.attend_status, a.actual_status
        FROM trainings t
        JOIN training_attendance a
        ON t.id = a.training_id
        WHERE a.user_id = ?
        AND t.date BETWEEN ? AND ?
        AND t.title IN ({placeholders})
        ORDER BY t.date ASC
    """, [user_id, start, end] + target_titles)

    rows = cursor.fetchall()

    actual_total = 0
    estimated_total = 0
    records = []

    for row in rows:
        amount = row["reward_amount"] or 0

        # =========================
        # 実績
        # =========================
        if row["actual_status"] == "present":
            actual_total += amount

        # =========================
        # 見込み（実績優先）
        # =========================
        if row["actual_status"] is not None:
            status = row["actual_status"]
            source = "actual"
        else:
            status = row["attend_status"]
            source = "planned"

        if status == "present":
            estimated_total += amount

        records.append({
            "date": row["date"],
            "title": row["title"],
            "status": status,
            "source": source,
            "amount": amount if status == "present" else 0
        })

    return actual_total, estimated_total, records


# =========================
# ホース報酬取得
# =========================
def get_hose_reward_summary(conn, user_id, fiscal_year):
    start, end = get_fiscal_year_range(fiscal_year)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUM(h.hose_count) as total_count
        FROM training_hose_members h
        JOIN trainings t ON h.hose_id = t.id
        WHERE h.user_id = ?
        AND t.date BETWEEN ? AND ?
    """, (user_id, start, end))

    row = cursor.fetchone()

    total_count = row["total_count"] or 0
    reward = total_count * 1000

    return total_count, reward


# =========================
# 管理者用一覧
# =========================
def get_all_user_reward_summary(conn, fiscal_year):

    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM users")
    users = cursor.fetchall()

    result = []

    for user in users:
        
        user_id = user["id"]

        data = get_user_reward_summary(conn, user_id, fiscal_year)

        # ★ 特定訓練（my_rewardと同じ）
        target_titles = ["ポンプ点検", "年末夜警"]

        specific_actual, _, _ = get_user_specific_training_reward(
            conn,
            user_id,
            fiscal_year,
            target_titles
        )

        # ★ 徴収額（完全一致ロジック）
        collection = specific_actual + data["role_reward"]

        result.append({
            "user_id": user_id,
            "name": user["name"],
            "actual": data["actual_total"],
            "estimated": data["estimated_total"],
            "role": data["role_reward"],
            "total": data["grand_total"],
            "collection": collection

        })

    return result



# =========================
# データベース保守用
# =========================
def export_db():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_fire_corps_{timestamp}.db"

    shutil.copy(DB_NAME, backup_file)

    return backup_file

def import_db(uploaded_file):
    backup = f"{DB_NAME}.before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 現在DBを退避
    if os.path.exists(DB_NAME):
        shutil.copy(DB_NAME, backup)

    # 一時ファイル経由で復元
    temp_path = "temp_restore.db"

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # 入れ替え
    shutil.move(temp_path, DB_NAME)

    return backup