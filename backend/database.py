"""
LiftCoach AI — Database Module
SQLite-backed authentication, session tracking, and gallery management.
"""

import sqlite3
import bcrypt
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Optional: psycopg2 for PostgreSQL (Supabase)
try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "liftcoach.db")
DATABASE_URL = os.environ.get("DATABASE_URL")

class DBConnection:
    """Wrapper that duck-types an SQLite connection but can route to PostgreSQL."""
    def __init__(self, conn, is_postgres=False):
        self._conn = conn
        self.is_postgres = is_postgres

    def execute(self, query, params=()):
        if self.is_postgres and "?" in query and "%s" not in query:
            query = query.replace("?", "%s")
        cur = self._conn.cursor()
        cur.execute(query, params)
        return cur

    def executescript(self, script):
        if self.is_postgres:
            script = script.replace("AUTOINCREMENT", "SERIAL")
            script = script.replace("INTEGER PRIMARY KEY SERIAL", "SERIAL PRIMARY KEY")
        
        cur = self._conn.cursor()
        if self.is_postgres:
            cur.execute(script)
        else:
            cur.executescript(script)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def cursor(self):
        # Return self so cursor.execute routes directly to our wrapper's execute
        return self


def get_connection():
    """Get a database connection wrapper."""
    if DATABASE_URL and HAS_PSYCOPG2:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            # Use DictCursor to emulate sqlite3.Row dict-like access
            conn.cursor_factory = psycopg2.extras.DictCursor
            return DBConnection(conn, is_postgres=True)
        except Exception as e:
            print(f"Failed to connect to PostgreSQL: {e}. Falling back to SQLite.")
            pass # Fall back to SQLite naturally

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return DBConnection(conn, is_postgres=False)


def init_db():
    """Initialize database tables and seed default admin account."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            age INTEGER,
            weight_kg REAL,
            height_cm REAL,
            gender TEXT DEFAULT '',
            experience_level TEXT DEFAULT '',
            preferred_lift TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            profile_photo TEXT DEFAULT '',
            role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('super_admin', 'admin', 'user')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lift_type TEXT NOT NULL DEFAULT 'Snatch',
            verdict TEXT,
            faults_json TEXT DEFAULT '[]',
            kinematic_json TEXT DEFAULT '{}',
            phases_json TEXT DEFAULT '{}',
            video_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            target TEXT DEFAULT '',
            details TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # Migrate existing DB: add new columns if they don't exist yet
    _migrate_user_columns(cursor)

    # Seed default admin if not exists
    existing = cursor.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not existing:
        pw_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
            ("admin", "admin@liftcoach.ai", pw_hash, "System Administrator", "admin"),
        )

    # Seed default super admin if not exists
    existing_sa = cursor.execute("SELECT id FROM users WHERE username = 'superadmin'").fetchone()
    if not existing_sa:
        sa_hash = bcrypt.hashpw("superadmin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
            ("superadmin", "superadmin@liftcoach.ai", sa_hash, "Super Administrator", "super_admin"),
        )

    # Seed default settings
    defaults = {
        "app_name": "LiftCoach AI",
        "tagline": "AI-powered weightlifting technique analysis",
        "model_complexity": "1",
        "detection_confidence": "0.5",
        "max_login_attempts": "5",
    }
    for key, value in defaults.items():
        if conn.is_postgres:
            cursor.execute(
                "INSERT INTO app_settings (key, value) VALUES (%s, %s) ON CONFLICT(key) DO NOTHING", (key, value)
            )
        else:
            cursor.execute(
                "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)", (key, value)
            )

    conn.commit()
    conn.close()


def _migrate_user_columns(conn_wrapper):
    """Add new profile columns to existing users table if missing."""
    if conn_wrapper.is_postgres:
        cur = conn_wrapper.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
        existing_cols = {row[0] for row in cur.fetchall()}
    else:
        cur = conn_wrapper.execute("PRAGMA table_info(users)")
        existing_cols = {row[1] for row in cur.fetchall()}
    new_columns = {
        "age": "INTEGER",
        "weight_kg": "REAL",
        "height_cm": "REAL",
        "gender": "TEXT DEFAULT ''",
        "experience_level": "TEXT DEFAULT ''",
        "preferred_lift": "TEXT DEFAULT ''",
        "bio": "TEXT DEFAULT ''",
        "profile_photo": "TEXT DEFAULT ''",
        "failed_login_attempts": "INTEGER NOT NULL DEFAULT 0",
        "locked_at": "TEXT DEFAULT NULL",
        "deactivation_reason": "TEXT DEFAULT ''",
        "must_reset_password": "INTEGER NOT NULL DEFAULT 0",
    }
    for col_name, col_type in new_columns.items():
        if col_name not in existing_cols:
            conn_wrapper.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")


# ─── AUTH ──────────────────────────────────────────────

def register_user(username: str, email: str, password: str, full_name: str = "") -> dict:
    """Register a new user. Returns {'success': bool, 'message': str}."""
    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters."}
    if len(username) < 3:
        return {"success": False, "message": "Username must be at least 3 characters."}

    conn = get_connection()
    try:
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        conn.execute(
            "INSERT INTO users (username, email, password_hash, full_name) VALUES (?, ?, ?, ?)",
            (username, email, pw_hash, full_name),
        )
        conn.commit()
        return {"success": True, "message": "Registration successful!"}
    except Exception as e:
        err_str = str(e).lower()
        if "integrityerror" in str(type(e)).lower() or "unique constraint" in err_str or "duplicate key" in err_str:
            if "username" in err_str:
                return {"success": False, "message": "Username already taken."}
            elif "email" in err_str:
                return {"success": False, "message": "Email already registered."}
        return {"success": False, "message": "Registration failed."}
    finally:
        conn.close()


def authenticate(username: str, password: str) -> dict | None:
    """Authenticate user. Returns dict with 'user' and 'status' keys.
    Status values: 'success', 'not_found', 'inactive', 'locked', 'bad_password'.
    Returns None only if username not found (backward compat).
    """
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if user is None:
        conn.close()
        return None
    if not user["is_active"]:
        conn.close()
        return None

    # Check password
    if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        # Success — reset failed attempts
        conn.execute(
            "UPDATE users SET failed_login_attempts = 0, locked_at = NULL WHERE id = ?",
            (user["id"],),
        )
        conn.commit()
        conn.close()
        return dict(user)

    # Wrong password — increment failed attempts
    new_attempts = (user["failed_login_attempts"] or 0) + 1
    max_attempts = int(get_setting("max_login_attempts", "5"))

    if new_attempts >= max_attempts:
        # Lock the account
        reason = f"Locked after {max_attempts} failed login attempts"
        conn.execute(
            "UPDATE users SET failed_login_attempts = ?, locked_at = ?, is_active = 0, deactivation_reason = ? WHERE id = ?",
            (new_attempts, datetime.now().isoformat(), reason, user["id"]),
        )
        conn.commit()
        conn.close()
        return {"__locked": True, "attempts": new_attempts, "max": max_attempts}
    else:
        conn.execute(
            "UPDATE users SET failed_login_attempts = ? WHERE id = ?",
            (new_attempts, user["id"]),
        )
        conn.commit()
        conn.close()
        remaining = max_attempts - new_attempts
        return {"__bad_password": True, "attempts": new_attempts, "remaining": remaining}


# ─── USER PROFILE ──────────────────────────────────────

def get_user(user_id: int) -> dict | None:
    """Get user by ID."""
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def update_profile(user_id: int, **kwargs) -> dict:
    """Update user profile fields. Accepts any combination of:
    full_name, email, age, weight_kg, height_cm, gender,
    experience_level, preferred_lift, bio, profile_photo
    """
    allowed = {'full_name', 'email', 'age', 'weight_kg', 'height_cm', 'gender',
               'experience_level', 'preferred_lift', 'bio', 'profile_photo'}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        return {"success": False, "message": "Nothing to update."}

    conn = get_connection()
    try:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return {"success": True, "message": "Profile updated successfully!"}
    except Exception as e:
        if "integrityerror" in str(type(e)).lower() or "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
            return {"success": False, "message": "Email already in use by another account."}
        raise e
    finally:
        conn.close()


def save_profile_photo(user_id: int, photo_bytes: bytes, filename: str) -> str:
    """Save an uploaded profile photo to disk and update the user record.
    Returns the saved file path relative to the app directory.
    """
    photos_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile_photos")
    os.makedirs(photos_dir, exist_ok=True)

    # Generate unique filename
    ext = os.path.splitext(filename)[1] or ".png"
    saved_name = f"user_{user_id}_{int(datetime.now().timestamp())}{ext}"
    saved_path = os.path.join(photos_dir, saved_name)

    with open(saved_path, "wb") as f:
        f.write(photo_bytes)

    # Store relative path in database
    rel_path = f"profile_photos/{saved_name}"
    conn = get_connection()
    conn.execute("UPDATE users SET profile_photo = ? WHERE id = ?", (rel_path, user_id))
    conn.commit()
    conn.close()
    return rel_path


def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    """Change user password."""
    if len(new_password) < 6:
        return {"success": False, "message": "New password must be at least 6 characters."}
    conn = get_connection()
    user = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    if not bcrypt.checkpw(old_password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        conn.close()
        return {"success": False, "message": "Current password is incorrect."}
    pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, user_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Password changed successfully."}


def force_reset_password(user_id: int, new_password: str) -> dict:
    """Set a new password without requiring the old one, and clear the must_reset_password flag."""
    if len(new_password) < 6:
        return {"success": False, "message": "New password must be at least 6 characters."}
    conn = get_connection()
    pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn.execute(
        "UPDATE users SET password_hash = ?, must_reset_password = 0 WHERE id = ?",
        (pw_hash, user_id),
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": "Password has been reset successfully."}


# ─── SESSIONS ──────────────────────────────────────────

def save_session(user_id: int, lift_type: str, analysis_results: dict, video_filename: str) -> int:
    """Save an analysis session. Returns session ID."""
    conn = get_connection()
    if conn.is_postgres:
        cursor = conn.execute(
            """INSERT INTO sessions (user_id, lift_type, verdict, faults_json, kinematic_json, phases_json, video_filename)
               VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            (
                user_id,
                lift_type,
                analysis_results.get("verdict", "Unknown"),
                json.dumps(analysis_results.get("faults_found", [])),
                json.dumps(analysis_results.get("kinematic_data", {})),
                json.dumps(analysis_results.get("phases", {})),
                video_filename,
            ),
        )
        session_id = cursor.fetchone()[0]
    else:
        cursor = conn.execute(
            """INSERT INTO sessions (user_id, lift_type, verdict, faults_json, kinematic_json, phases_json, video_filename)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                lift_type,
                analysis_results.get("verdict", "Unknown"),
                json.dumps(analysis_results.get("faults_found", [])),
                json.dumps(analysis_results.get("kinematic_data", {})),
                json.dumps(analysis_results.get("phases", {})),
                video_filename,
            ),
        )
        session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def get_user_sessions(user_id: int, limit: int = 50) -> list:
    """Get all sessions for a user, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(session_id: int) -> dict | None:
    """Get a single session by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── GALLERY ───────────────────────────────────────────

def save_to_gallery(session_id: int, user_id: int, title: str, notes: str = "") -> int:
    """Save a session to the user's gallery. Returns gallery ID."""
    conn = get_connection()
    if conn.is_postgres:
        cursor = conn.execute(
            "INSERT INTO gallery (session_id, user_id, title, notes) VALUES (?, ?, ?, ?) RETURNING id",
            (session_id, user_id, title, notes),
        )
        gid = cursor.fetchone()[0]
    else:
        cursor = conn.execute(
            "INSERT INTO gallery (session_id, user_id, title, notes) VALUES (?, ?, ?, ?)",
            (session_id, user_id, title, notes),
        )
        gid = cursor.lastrowid
    conn.commit()
    conn.close()
    return gid


def get_user_gallery(user_id: int) -> list:
    """Get gallery items for a user with session data joined."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT g.*, s.lift_type, s.verdict, s.faults_json, s.kinematic_json, s.video_filename, s.created_at as session_date
           FROM gallery g JOIN sessions s ON g.session_id = s.id
           WHERE g.user_id = ? ORDER BY g.created_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_gallery_item(gallery_id: int, user_id: int) -> bool:
    """Delete a gallery item (only own items)."""
    conn = get_connection()
    conn.execute("DELETE FROM gallery WHERE id = ? AND user_id = ?", (gallery_id, user_id))
    conn.commit()
    conn.close()
    return True


# ─── ADMIN ─────────────────────────────────────────────

def get_all_users() -> list:
    """Get all users for admin management."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, username, email, full_name, role, is_active, created_at, failed_login_attempts, locked_at, deactivation_reason, must_reset_password FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_user_active(user_id: int) -> bool:
    """Toggle a user's active status. On reactivation, sets must_reset_password flag."""
    conn = get_connection()
    user = conn.execute("SELECT is_active, deactivation_reason FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        new_status = 0 if user["is_active"] else 1
        if new_status == 1:
            # Reactivating — force password reset, clear lockout data
            conn.execute(
                "UPDATE users SET is_active = 1, must_reset_password = 1, failed_login_attempts = 0, locked_at = NULL, deactivation_reason = '' WHERE id = ?",
                (user_id,),
            )
        else:
            # Deactivating manually
            conn.execute(
                "UPDATE users SET is_active = 0, deactivation_reason = 'Manually deactivated by administrator' WHERE id = ?",
                (user_id,),
            )
        conn.commit()
    conn.close()
    return True


def soft_delete_user(user_id: int) -> bool:
    """Soft-delete a user by deactivating and anonymizing."""
    conn = get_connection()
    conn.execute(
        "UPDATE users SET is_active = 0, username = 'deleted_' || id, email = 'deleted_' || id || '@removed' WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
    return True


def get_admin_stats() -> dict:
    """Get dashboard statistics for admin."""
    conn = get_connection()
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'user'").fetchone()[0]
    active_users = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'user' AND is_active = 1").fetchone()[0]
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    good_lifts = conn.execute("SELECT COUNT(*) FROM sessions WHERE verdict = 'Good Lift'").fetchone()[0]
    bad_lifts = conn.execute("SELECT COUNT(*) FROM sessions WHERE verdict = 'Bad Lift'").fetchone()[0]
    total_gallery = conn.execute("SELECT COUNT(*) FROM gallery").fetchone()[0]

    recent_sessions = conn.execute(
        """SELECT s.*, u.username FROM sessions s JOIN users u ON s.user_id = u.id
           ORDER BY s.created_at DESC LIMIT 10"""
    ).fetchall()
    conn.close()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_sessions": total_sessions,
        "good_lifts": good_lifts,
        "bad_lifts": bad_lifts,
        "total_gallery": total_gallery,
        "recent_sessions": [dict(r) for r in recent_sessions],
    }


# ─── SETTINGS ──────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    """Get an app setting."""
    conn = get_connection()
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    """Set an app setting."""
    conn = get_connection()
    if conn.is_postgres:
        conn.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value", (key, value))
    else:
        conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_all_settings() -> dict:
    """Get all app settings as a dict."""
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


# ─── AUDIT LOGS ────────────────────────────────────────────

def log_action(user_id: int, action: str, target: str = "", details: str = ""):
    """Insert an audit log entry."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_logs (user_id, action, target, details) VALUES (?, ?, ?, ?)",
        (user_id, action, target, details),
    )
    conn.commit()
    conn.close()


def get_audit_logs(limit: int = 100) -> list:
    """Get recent audit logs joined with usernames."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT a.*, COALESCE(u.username, 'system') as username
           FROM audit_logs a LEFT JOIN users u ON a.user_id = u.id
           ORDER BY a.created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── SUPER ADMIN ───────────────────────────────────────────

def get_all_admins() -> list:
    """Get all users with admin or super_admin role."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, username, email, full_name, role, is_active, created_at FROM users WHERE role IN ('admin', 'super_admin') ORDER BY role, created_at"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_user_role(user_id: int, new_role: str) -> dict:
    """Change a user's role. new_role must be 'user', 'admin', or 'super_admin'."""
    if new_role not in ('user', 'admin', 'super_admin'):
        return {"success": False, "message": "Invalid role."}
    conn = get_connection()
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Role updated to {new_role}."}


def get_db_table_stats() -> list:
    """Return row counts for every table in the database."""
    conn = get_connection()
    if conn.is_postgres:
        tables = conn.execute(
            "SELECT tablename as name FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
        ).fetchall()
    else:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    stats = []
    for t in tables:
        name = t["name"]
        count = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
        stats.append({"table": name, "rows": count})
    conn.close()
    return stats
