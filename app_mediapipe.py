"""
LiftCoach AI — MediaPipe BlazePose Edition
Full-featured web application with authentication, role-based access,
custom UI, and AI-powered weightlifting technique analysis.
"""

import streamlit as st
import cv2
import numpy as np
import tempfile
import mediapipe as mp
import os
import time
import json
import base64
import pandas as pd
import database as db
import storage
from components.live_recorder import live_recorder
from dotenv import load_dotenv

load_dotenv()

# ── MediaPipe Tasks API ─────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode
PoseLandmarksConnections = mp.tasks.vision.PoseLandmarksConnections
mp_draw_landmarks = mp.tasks.vision.drawing_utils.draw_landmarks
DrawingSpec = mp.tasks.vision.drawing_utils.DrawingSpec

# ── Page Config ──────────────────────────────────────────
st.set_page_config(page_title="LiftCoach AI", layout="wide", initial_sidebar_state="collapsed")

# ── Initialize Database ──────────────────────────────────
db.init_db()

# ── Constants ────────────────────────────────────────────
APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(APP_DIR, "pose_landmarker_lite.task")
OUTPUT_DIR = os.path.join(APP_DIR, "output")
CSS_PATH = os.path.join(APP_DIR, "style.css")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════
#  LOAD CSS THEME
# ═══════════════════════════════════════════════════════════

def load_css():
    if os.path.exists(CSS_PATH):
        with open(CSS_PATH, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


# ═══════════════════════════════════════════════════════════
#  SESSION STATE HELPERS
# ═══════════════════════════════════════════════════════════

def init_session_state():
    defaults = {
        "user": None,
        "page": "login",
        "last_analysis": None,
        "last_session_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()


def navigate(page: str):
    st.session_state["page"] = page

def logout():
    user = st.session_state.get("user")
    if user and user.get("id"):
        db.log_action(user["id"], "logout", "auth", f"User @{user['username']} logged out")
    st.session_state["user"] = None
    st.session_state["page"] = "login"
    st.session_state["last_analysis"] = None
    st.session_state["last_session_id"] = None


def is_admin() -> bool:
    user = st.session_state.get("user")
    return user.get("role") in ("admin", "super_admin") if user else False


def is_super_admin() -> bool:
    user = st.session_state.get("user")
    return user.get("role") == "super_admin" if user else False


# ═══════════════════════════════════════════════════════════
#  NAVIGATION BAR
# ═══════════════════════════════════════════════════════════

def render_navbar():
    user = st.session_state["user"]
    if user is None:
        return

    current = st.session_state["page"]
    initial = user["username"][0].upper()

    if is_super_admin():
        nav_items = [
            ("admin_dashboard", "📊 Dashboard"),
            ("admin_users", "👥 Users"),
            ("admin_content", "⚙️ Settings"),
            ("super_admin", "🛡️ Super Admin"),
        ]
    elif is_admin():
        nav_items = [
            ("admin_dashboard", "📊 Dashboard"),
            ("admin_users", "👥 Users"),
            ("admin_content", "⚙️ Settings"),
        ]
    else:
        nav_items = [
            ("home", "🏠 Home"),
            ("analyze", "🎯 Analyze"),
            ("gallery", "🖼️ Gallery"),
            ("profile", "👤 Profile"),
        ]

    links_html = ""
    for page_key, label in nav_items:
        active = "active" if current == page_key else ""
        links_html += f'<span class="nav-link {active}" id="nav-{page_key}">{label}</span>'

    navbar_html = f"""
    <div class="nav-bar">
        <div class="nav-brand">🏋️ LiftCoach AI</div>
        <div class="nav-links">{links_html}</div>
        <div class="nav-user">
            <span class="nav-username">{user['username']}</span>
            <div class="nav-avatar">{initial}</div>
        </div>
    </div>
    """
    st.markdown(navbar_html, unsafe_allow_html=True)

    # Navigation buttons (Streamlit can't handle JS clicks on HTML,
    # so we use hidden Streamlit buttons triggered by columns)
    cols = st.columns(len(nav_items) + 2)
    for idx, (page_key, label) in enumerate(nav_items):
        with cols[idx]:
            if st.button(label.split(" ", 1)[1], key=f"navbtn_{page_key}", use_container_width=True):
                navigate(page_key)
                st.rerun()
    with cols[-2]:
        if st.button("🚪 Logout", key="navbtn_logout", use_container_width=True):
            logout()
            st.rerun()

    # Hide the button row visually (nav is done via the styled HTML above + these hidden buttons)
    st.markdown("""<style>
        div[data-testid="stHorizontalBlock"]:has(button[kind="secondary"]) { 
            margin-top: -0.5rem; margin-bottom: 0.5rem;
        }
    </style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  LIFT ANALYSIS ENGINE
# ═══════════════════════════════════════════════════════════

class LiftAnalysisMediaPipe:
    def __init__(self, landmarks_data, frame_rate, frame_width=1920, frame_height=1080):
        self.landmarks_data = landmarks_data
        self.frame_rate = frame_rate if frame_rate > 0 else 30
        self.dt = 1 / self.frame_rate
        self.num_frames = len(landmarks_data)
        self.frame_width = frame_width
        self.frame_height = frame_height

        self.landmark_map = {
            'nose': 0, 'left_eye_inner': 1, 'left_eye': 2, 'left_eye_outer': 3,
            'right_eye_inner': 4, 'right_eye': 5, 'right_eye_outer': 6,
            'left_ear': 7, 'right_ear': 8,
            'left_mouth': 9, 'right_mouth': 10,
            'left_shoulder': 11, 'right_shoulder': 12,
            'left_elbow': 13, 'right_elbow': 14,
            'left_wrist': 15, 'right_wrist': 16,
            'left_pinky': 17, 'right_pinky': 18,
            'left_index': 19, 'right_index': 20,
            'left_thumb': 21, 'right_thumb': 22,
            'left_hip': 23, 'right_hip': 24,
            'left_knee': 25, 'right_knee': 26,
            'left_ankle': 27, 'right_ankle': 28,
            'left_heel': 29, 'right_heel': 30,
            'left_foot_index': 31, 'right_foot_index': 32,
        }
        self.orientation = self._determine_lifter_orientation()
        self._preprocess_kinematics()

    def _determine_lifter_orientation(self):
        for landmarks in self.landmarks_data:
            if landmarks is not None:
                ls = landmarks[self.landmark_map['left_shoulder']]
                lh = landmarks[self.landmark_map['left_hip']]
                rs = landmarks[self.landmark_map['right_shoulder']]
                rh = landmarks[self.landmark_map['right_hip']]
                left_conf = ls[2] + lh[2]
                right_conf = rs[2] + rh[2]
                if left_conf > right_conf + 0.1:
                    return 'left'
                elif right_conf > left_conf + 0.1:
                    return 'right'
        return 'right'

    def _get_point(self, name, frame):
        if frame < self.num_frames and self.landmarks_data[frame] is not None:
            lm = self.landmarks_data[frame][self.landmark_map[name]]
            if lm[2] > 0.1:
                return np.array([lm[0] * self.frame_width, lm[1] * self.frame_height, lm[2]])
        return None

    def _calculate_angle(self, p1, p2, p3):
        if p1 is None or p2 is None or p3 is None:
            return None
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        angle = abs(np.degrees(np.arctan2(v2[1], v2[0]) - np.arctan2(v1[1], v1[0])))
        return angle if angle <= 180 else 360 - angle

    def _get_bar_position(self, frame):
        lw, rw = self._get_point('left_wrist', frame), self._get_point('right_wrist', frame)
        if lw is not None and rw is not None:
            return np.mean([lw[:2], rw[:2]], axis=0)
        return None

    def _preprocess_kinematics(self):
        self.bar_y = [p[1] if p is not None else None for p in [self._get_bar_position(i) for i in range(self.num_frames)]]
        self.bar_x = [p[0] if p is not None else None for p in [self._get_bar_position(i) for i in range(self.num_frames)]]
        self.hip_angles, self.knee_angles, self.elbow_angles, self.torso_angles = [], [], [], []
        sh_n, hip_n, knee_n, ank_n, elb_n, wri_n = (f"{self.orientation}_{n}" for n in ['shoulder', 'hip', 'knee', 'ankle', 'elbow', 'wrist'])
        for i in range(self.num_frames):
            sh, hip, knee, ank, elb, wri = (self._get_point(n, i) for n in [sh_n, hip_n, knee_n, ank_n, elb_n, wri_n])
            self.hip_angles.append(self._calculate_angle(sh, hip, knee))
            self.knee_angles.append(self._calculate_angle(hip, knee, ank))
            self.elbow_angles.append(self._calculate_angle(sh, elb, wri))
            # Torso angle: angle between shoulder-hip line and vertical
            if sh is not None and hip is not None:
                dx = sh[0] - hip[0]
                dy = sh[1] - hip[1]  # negative = shoulder above hip
                angle_from_vertical = abs(np.degrees(np.arctan2(dx, -dy)))
                self.torso_angles.append(round(angle_from_vertical, 2))
            else:
                self.torso_angles.append(None)

    def analyze_lift(self):
        faults_found, kinematic_data = [], {}
        valid_bar_y = [y for y in self.bar_y if y is not None]
        if not valid_bar_y:
            return {"faults_found": ["Could not detect barbell path."], "verdict": "Bad Lift", "phases": {}, "kinematic_data": {}}

        floor_y = np.max(valid_bar_y)
        try:
            start_frame = next(i for i, y in enumerate(self.bar_y) if y is not None and y < floor_y - 10)
        except StopIteration:
            return {"faults_found": ["Could not detect lift start."], "verdict": "Bad Lift", "phases": {}, "kinematic_data": {}}

        clean_bar_y_pull = [y if y is not None else float('inf') for y in self.bar_y[start_frame:]]
        if not clean_bar_y_pull:
            return {"faults_found": ["Analysis failed after start."], "verdict": "Bad Lift", "phases": {"start_frame": start_frame}, "kinematic_data": {}}

        end_of_pull_frame = np.argmin(clean_bar_y_pull) + start_frame
        pull_duration_sec = round((end_of_pull_frame - start_frame) / self.frame_rate, 2)
        phases = {"start_frame": start_frame, "end_of_pull_frame": end_of_pull_frame}
        kinematic_data["pull_duration_sec"] = pull_duration_sec

        # ── Hip Extension Analysis ──
        pull_hip = self.hip_angles[start_frame:end_of_pull_frame + 1]
        valid_hip = [a for a in pull_hip if a is not None]
        if valid_hip:
            peak_hip = round(np.max(valid_hip), 1)
            kinematic_data['peak_hip_extension'] = peak_hip
            if peak_hip < 170:
                faults_found.append("Incomplete Hip Extension")
        else:
            kinematic_data['peak_hip_extension'] = None
            faults_found.append("Could not analyze hip extension.")

        # ── Knee Extension Analysis ──
        pull_knee = self.knee_angles[start_frame:end_of_pull_frame + 1]
        valid_knee = [a for a in pull_knee if a is not None]
        if valid_knee:
            peak_knee = round(np.max(valid_knee), 1)
            start_knee = valid_knee[0] if valid_knee else None
            kinematic_data['peak_knee_extension'] = peak_knee
            kinematic_data['start_knee_angle'] = round(start_knee, 1) if start_knee else None
            if peak_knee < 165:
                faults_found.append("Incomplete Knee Extension")
        else:
            kinematic_data['peak_knee_extension'] = None
            kinematic_data['start_knee_angle'] = None

        # ── Elbow / Arm Bend Analysis ──
        pull_elbow = self.elbow_angles[start_frame:end_of_pull_frame + 1]
        valid_elbow = [a for a in pull_elbow if a is not None]
        if valid_elbow:
            min_elbow_during_pull = round(np.min(valid_elbow), 1)
            kinematic_data['min_elbow_angle_during_pull'] = min_elbow_during_pull

            # Check for early arm bend (bent before peak hip extension)
            if valid_hip:
                peak_hip_idx = np.argmax([a if a is not None else -1 for a in pull_hip])
                bent_count, threshold = 0, 3
                for i in range(peak_hip_idx):
                    ea = self.elbow_angles[start_frame + i]
                    if ea is not None and ea < 160:
                        bent_count += 1
                    else:
                        bent_count = 0
                    if bent_count >= threshold:
                        faults_found.append("Early Arm Bend")
                        kinematic_data['early_arm_bend_frame'] = start_frame + i
                        break
        else:
            kinematic_data['min_elbow_angle_during_pull'] = None

        # ── Torso Angle Analysis ──
        torso_at_start = self.torso_angles[start_frame] if start_frame < len(self.torso_angles) else None
        valid_torso_pull = [a for a in self.torso_angles[start_frame:end_of_pull_frame + 1] if a is not None]
        torso_at_extension = round(np.min(valid_torso_pull), 1) if valid_torso_pull else None
        kinematic_data['torso_angle_at_start'] = torso_at_start
        kinematic_data['torso_angle_at_extension'] = torso_at_extension

        if torso_at_start is not None and torso_at_start > 65:
            faults_found.append("Excessive Forward Lean at Start")
        if torso_at_extension is not None and torso_at_extension > 15:
            faults_found.append("Insufficient Torso Extension")

        # ── Bar Path Deviation ──
        valid_bar_x = [self.bar_x[i] for i in range(start_frame, end_of_pull_frame + 1) if self.bar_x[i] is not None]
        if len(valid_bar_x) > 2:
            bar_deviation = round(np.max(valid_bar_x) - np.min(valid_bar_x), 1)
            kinematic_data['bar_path_deviation_px'] = bar_deviation
            # Normalize to frame width for percentage
            bar_deviation_pct = round((bar_deviation / self.frame_width) * 100, 1)
            kinematic_data['bar_path_deviation_pct'] = bar_deviation_pct
            if bar_deviation_pct > 8:
                faults_found.append("Excessive Bar Path Deviation")
        else:
            kinematic_data['bar_path_deviation_pct'] = None

        verdict = "Good Lift" if not faults_found else "Bad Lift"

        # Convert numpy types to native Python types for JSON serialization
        def _sanitize(obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, dict):
                return {k: _sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_sanitize(i) for i in obj]
            return obj

        return _sanitize({"faults_found": faults_found, "verdict": verdict, "phases": phases, "kinematic_data": kinematic_data})


# ═══════════════════════════════════════════════════════════
#  IWF GUIDELINE COMPARISON & COACHING FEEDBACK
# ═══════════════════════════════════════════════════════════

# Reference values based on IWF technical guidelines and published
# biomechanical studies of elite Olympic weightlifters.
IWF_GUIDELINES = {
    "peak_hip_extension": {
        "label": "Peak Hip Extension",
        "unit": "°",
        "expected": "≥ 170°",
        "ideal": 175,
        "threshold": 170,
        "direction": "higher_is_better",
        "pass_feedback": "Excellent hip extension — you are reaching full triple extension, a hallmark of elite technique.",
        "fail_feedback": "Your hip extension is incomplete. Work on hip mobility drills and practice pulling to full extension before transitioning under the bar. Focus on driving your hips forward and up.",
    },
    "peak_knee_extension": {
        "label": "Peak Knee Extension",
        "unit": "°",
        "expected": "≥ 165°",
        "ideal": 170,
        "threshold": 165,
        "direction": "higher_is_better",
        "pass_feedback": "Strong knee extension — your legs are driving powerfully through the pull phase.",
        "fail_feedback": "Your knees are not fully extending during the pull. Practice clean/snatch pulls focusing on driving through the full range of motion with your legs before bending to receive.",
    },
    "min_elbow_angle_during_pull": {
        "label": "Elbow Angle During Pull",
        "unit": "°",
        "expected": "≥ 160°",
        "ideal": 175,
        "threshold": 160,
        "direction": "higher_is_better",
        "pass_feedback": "Arms stayed straight during the pull — this maximizes power transfer from legs to bar.",
        "fail_feedback": "You are bending your arms too early during the pull. Keep your arms relaxed and straight like ropes until AFTER full extension. Practice muscle snatch/clean drills to reinforce this timing.",
    },
    "torso_angle_at_start": {
        "label": "Torso Angle at Start",
        "unit": "°",
        "expected": "≤ 55°",
        "ideal": 45,
        "threshold": 55,
        "direction": "lower_is_better",
        "pass_feedback": "Good starting position — your torso is upright enough to maintain balance and leverage off the floor.",
        "fail_feedback": "You are leaning too far forward at the start position. Adjust your setup: sit your hips slightly lower, push your chest up, and ensure your shoulders are over or slightly in front of the bar.",
    },
    "torso_angle_at_extension": {
        "label": "Torso at Full Extension",
        "unit": "°",
        "expected": "≤ 10°",
        "ideal": 5,
        "threshold": 10,
        "direction": "lower_is_better",
        "pass_feedback": "Your torso reaches a near-vertical position at extension — excellent posture for an efficient turnover.",
        "fail_feedback": "Your torso is not getting vertical enough at the top of the pull. Focus on driving your chest up and finishing tall. Strengthen your back extensors and practice tall cleans/snatches.",
    },
    "bar_path_deviation_pct": {
        "label": "Bar Path Deviation",
        "unit": "%",
        "expected": "≤ 5%",
        "ideal": 3,
        "threshold": 5,
        "direction": "lower_is_better",
        "pass_feedback": "Very tight bar path — the bar stays close to your body, maximizing efficiency and reducing energy waste.",
        "fail_feedback": "The bar is swinging too far away from your body during the pull. Focus on keeping the bar close by engaging your lats. Practice hang pulls emphasizing bar contact at the hip/thigh.",
    },
    "pull_duration_sec": {
        "label": "Pull Duration",
        "unit": "s",
        "expected": "0.4–1.2s",
        "ideal": 0.7,
        "threshold_min": 0.4,
        "threshold_max": 1.2,
        "direction": "range",
        "pass_feedback": "Your pull timing is within the elite range — good speed and power through the movement.",
        "fail_feedback": "Your pull duration is outside the typical range. If too fast, you may be cutting the pull short. If too slow, work on generating more explosive leg drive.",
    },
}


def generate_iwf_comparison(kinematic_data: dict) -> list:
    """Generate a structured comparison between captured parameters and IWF guidelines.
    Returns a list of dicts: [{param, label, captured, expected, status, feedback}, ...]
    """
    results = []
    for param_key, guide in IWF_GUIDELINES.items():
        captured = kinematic_data.get(param_key)
        if captured is None:
            results.append({
                "param": param_key,
                "label": guide["label"],
                "captured": "N/A",
                "expected": guide["expected"],
                "unit": guide["unit"],
                "status": "unknown",
                "feedback": "Could not measure this parameter — ensure the full body is visible in the video.",
            })
            continue

        direction = guide["direction"]
        if direction == "higher_is_better":
            passed = captured >= guide["threshold"]
        elif direction == "lower_is_better":
            passed = captured <= guide["threshold"]
        elif direction == "range":
            passed = guide["threshold_min"] <= captured <= guide["threshold_max"]
        else:
            passed = True

        results.append({
            "param": param_key,
            "label": guide["label"],
            "captured": f"{captured}{guide['unit']}",
            "expected": guide["expected"],
            "unit": guide["unit"],
            "status": "pass" if passed else "fail",
            "feedback": guide["pass_feedback"] if passed else guide["fail_feedback"],
        })

    return results


# ═══════════════════════════════════════════════════════════
#  PAGE: LOGIN
# ═══════════════════════════════════════════════════════════

def page_login():
    st.markdown("""
    <div class="auth-container fade-in">
        <div class="auth-logo">
            <h1>🏋️ LiftCoach AI</h1>
            <p>AI-powered weightlifting technique analysis</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown("#### Sign In")
        username = st.text_input("Username", key="login_username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")

        if st.button("Sign In", key="login_btn", use_container_width=True):
            if username and password:
                result = db.authenticate(username, password)
                if result is None:
                    st.error("Invalid credentials or account deactivated. Please contact your administrator to restore access.")
                elif isinstance(result, dict) and result.get("__locked"):
                    st.error(f"🔒 Your account has been locked after {result['max']} failed login attempts. Please contact your administrator to reactivate your account.")
                elif isinstance(result, dict) and result.get("__bad_password"):
                    remaining = result["remaining"]
                    if remaining <= 2:
                        st.error(f"Incorrect password. You have **{remaining}** attempt{'s' if remaining != 1 else ''} remaining before your account is locked. Please contact your administrator if you've forgotten your password.")
                    else:
                        st.error(f"Incorrect password. You have **{remaining}** attempt{'s' if remaining != 1 else ''} remaining.")
                elif isinstance(result, dict) and "id" in result:
                    # Audit log: successful login
                    db.log_action(result["id"], "login", "auth", f"User @{result['username']} logged in")
                    # Check if must reset password
                    if result.get("must_reset_password"):
                        st.session_state["user"] = result
                        navigate("force_reset_password")
                        st.rerun()
                    else:
                        st.session_state["user"] = result
                        if result["role"] in ("admin", "super_admin"):
                            navigate("admin_dashboard")
                        else:
                            navigate("home")
                        st.rerun()
                else:
                    st.error("Invalid credentials. Please contact your administrator.")
            else:
                st.warning("Please fill in all fields.")

        st.markdown("---")
        st.markdown("<center style='color: #64748b; font-size: 0.85rem;'>Don't have an account?</center>", unsafe_allow_html=True)
        if st.button("Create Account", key="goto_register", use_container_width=True):
            navigate("register")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  PAGE: REGISTER
# ═══════════════════════════════════════════════════════════

def page_register():
    st.markdown("""
    <div class="auth-container fade-in">
        <div class="auth-logo">
            <h1>🏋️ LiftCoach AI</h1>
            <p>Create your athlete account</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown("#### Create Account")
        full_name = st.text_input("Full Name", key="reg_fullname", placeholder="Juan Dela Cruz")
        username = st.text_input("Username", key="reg_username", placeholder="Choose a username")
        email = st.text_input("Email", key="reg_email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", key="reg_password", placeholder="Min 6 characters")
        confirm = st.text_input("Confirm Password", type="password", key="reg_confirm", placeholder="Re-enter password")

        if st.button("Create Account", key="register_btn", use_container_width=True):
            if not all([full_name, username, email, password, confirm]):
                st.warning("Please fill in all fields.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                result = db.register_user(username, email, password, full_name)
                if result["success"]:
                    st.success("Account created! Please sign in.")
                    time.sleep(1)
                    navigate("login")
                    st.rerun()
                else:
                    st.error(result["message"])

        st.markdown("---")
        st.markdown("<center style='color: #64748b; font-size: 0.85rem;'>Already have an account?</center>", unsafe_allow_html=True)
        if st.button("Back to Sign In", key="goto_login", use_container_width=True):
            navigate("login")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  PAGE: HOME (Regular User)
# ═══════════════════════════════════════════════════════════

def page_home():
    render_navbar()
    user = st.session_state["user"]

    st.markdown(f"""
    <div class="fade-in">
        <div class="page-title">Welcome back, {user['full_name'] or user['username']} 👋</div>
        <div class="page-subtitle">Ready to analyze your next lift?</div>
    </div>
    """, unsafe_allow_html=True)

    # Quick stats
    sessions = db.get_user_sessions(user["id"])
    total = len(sessions)
    good = sum(1 for s in sessions if s["verdict"] == "Good Lift")
    bad = sum(1 for s in sessions if s["verdict"] == "Bad Lift")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="glass-card stat-card">
            <div class="stat-value">{total}</div>
            <div class="stat-label">Total Analyses</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="glass-card stat-card">
            <div class="stat-value success">{good}</div>
            <div class="stat-label">Good Lifts</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="glass-card stat-card">
            <div class="stat-value danger">{bad}</div>
            <div class="stat-label">Faults Found</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        rate = round((good / total * 100) if total > 0 else 0)
        st.markdown(f"""<div class="glass-card stat-card">
            <div class="stat-value warning">{rate}%</div>
            <div class="stat-label">Success Rate</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Action cards
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""<div class="glass-card action-card">
            <div class="action-icon">🎯</div>
            <div class="action-title">New Analysis</div>
            <div class="action-desc">Upload a video and get instant AI feedback on your technique</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Start Analysis →", key="home_analyze", use_container_width=True):
            navigate("analyze")
            st.rerun()

    with c2:
        st.markdown("""<div class="glass-card action-card">
            <div class="action-icon">🖼️</div>
            <div class="action-title">View Gallery</div>
            <div class="action-desc">Browse your saved analyses and track your progress over time</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Open Gallery →", key="home_gallery", use_container_width=True):
            navigate("gallery")
            st.rerun()

    with c3:
        st.markdown("""<div class="glass-card action-card">
            <div class="action-icon">👤</div>
            <div class="action-title">Your Profile</div>
            <div class="action-desc">View and update your account settings and personal info</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Edit Profile →", key="home_profile", use_container_width=True):
            navigate("profile")
            st.rerun()

    # Recent sessions
    if sessions:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="page-title" style="font-size:1.3rem;">📋 Recent Analyses</div>', unsafe_allow_html=True)
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        for s in sessions[:5]:
            verdict_class = "verdict-good" if s["verdict"] == "Good Lift" else "verdict-bad"
            faults = json.loads(s["faults_json"]) if s["faults_json"] else []
            fault_text = ", ".join(faults) if faults else "No faults"
            st.markdown(f"""
            <div class="user-row">
                <div>
                    <strong>{s['lift_type']}</strong>
                    <span style="color: var(--text-muted); font-size: 0.82rem; margin-left: 1rem;">{str(s['created_at'])[:16]}</span>
                    <span style="color: var(--text-muted); font-size: 0.8rem; margin-left: 0.5rem;">— {fault_text}</span>
                </div>
                <span class="{verdict_class}">{s['verdict']}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  PAGE: ANALYZE
# ═══════════════════════════════════════════════════════════

def page_analyze():
    render_navbar()
    user = st.session_state["user"]

    st.markdown("""
    <div class="fade-in">
        <div class="page-title">🎯 Analyze a Lift</div>
        <div class="page-subtitle">Upload a video or record live from your camera for AI technique analysis</div>
    </div>
    """, unsafe_allow_html=True)

    # Model check
    if not os.path.exists(MODEL_PATH):
        st.error(f"MediaPipe model not found at `{MODEL_PATH}`. Please download pose_landmarker_lite.task.")
        return

    # ── Input mode toggle ────────────────────────────────
    input_mode = st.radio(
        "Input Mode",
        ["📁  Upload Video", "📹  Live Record"],
        horizontal=True,
        key="input_mode",
        label_visibility="collapsed",
    )

    lift_type = st.selectbox("Lift Type", ["Snatch", "Clean & Jerk"], key="lift_type")
    st.markdown("<br>", unsafe_allow_html=True)

    if input_mode == "📁  Upload Video":
        # ── Upload mode ──────────────────────────────────
        uploaded_file = st.file_uploader(
            "Choose a video file", type=["mp4", "mov", "avi"], key="analyze_upload"
        )
        if uploaded_file:
            st.video(uploaded_file)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Analyze Lift", key="run_analysis", use_container_width=True):
                _run_analysis(uploaded_file, lift_type, user)
    else:
        # ── Live record mode ─────────────────────────────
        video_data = live_recorder(key="live_rec")
        if video_data and not st.session_state.get("_live_rec_processed"):
            # Mark as consumed so reruns don't re-trigger analysis
            st.session_state["_live_rec_processed"] = True
            try:
                video_bytes = base64.b64decode(video_data)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
                tmp.write(video_bytes)
                tmp.flush()
                tmp.close()
                st.success("✅ Recording received! Starting analysis…")
                _run_analysis(tmp.name, lift_type, user)
            except Exception as e:
                st.error(f"Error processing recording: {e}")
        elif not video_data:
            # Component is idle / user clicked Retake — allow next submission
            st.session_state["_live_rec_processed"] = False

    # Show results from session state (persists across reruns)
    if st.session_state.get("last_analysis"):
        _display_results(user)


def _run_analysis(video_source, lift_type, user):
    """Execute the full analysis pipeline.

    Args:
        video_source: Either a Streamlit UploadedFile or a file path string.
    """
    if isinstance(video_source, str):
        # Already a file path (from live recorder)
        video_path = video_source
    else:
        # Streamlit UploadedFile object
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(video_source.read())
        video_path = tfile.name

    cap, writer = None, None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Could not open video file.")

        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("**Phase 1** — Detecting pose landmarks...")
        progress_bar = st.progress(0, text="Analyzing frames...")
        all_landmarks, annotated_frames = [], []
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_rate = cap.get(cv2.CAP_PROP_FPS) or 30.0
        fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        with PoseLandmarker.create_from_options(options) as landmarker:
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                timestamp_ms = int((frame_idx / frame_rate) * 1000)
                results = landmarker.detect_for_video(mp_image, timestamp_ms)

                if results.pose_landmarks and len(results.pose_landmarks) > 0:
                    lms = [[lm.x, lm.y, lm.visibility] for lm in results.pose_landmarks[0]]
                    all_landmarks.append(np.array(lms))
                else:
                    all_landmarks.append(None)

                annotated_frame = frame.copy()
                if results.pose_landmarks and len(results.pose_landmarks) > 0:
                    mp_draw_landmarks(
                        annotated_frame, results.pose_landmarks[0],
                        PoseLandmarksConnections.POSE_LANDMARKS,
                        DrawingSpec(color=(124, 58, 237), thickness=2, circle_radius=3),
                        DrawingSpec(color=(167, 139, 250), thickness=2, circle_radius=1),
                    )
                annotated_frames.append(annotated_frame)
                frame_idx += 1
                if total_frames > 0:
                    progress_bar.progress(min(frame_idx / total_frames, 1.0), text=f"Frame {frame_idx}/{total_frames}")
                else:
                    progress_bar.progress(0, text=f"Frame {frame_idx} processed…")

            if total_frames <= 0:
                progress_bar.progress(1.0, text=f"Done — {frame_idx} frames processed")

        if not annotated_frames:
            raise Exception("No frames could be read from the video.")

        st.markdown("**Phase 2** — Analyzing lift mechanics...")
        analyzer = LiftAnalysisMediaPipe(all_landmarks, frame_rate, fw, fh)
        analysis_results = analyzer.analyze_lift()

        st.markdown("**Phase 3** — Generating output video...")
        output_filename = f"analyzed_mediapipe_{int(time.time())}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        frame_h, frame_w, _ = annotated_frames[0].shape
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        writer = cv2.VideoWriter(output_path, fourcc, frame_rate, (frame_w, frame_h))

        for i, frame in enumerate(annotated_frames):
            phases = analysis_results.get('phases', {})
            if i == phases.get('start_frame'):
                cv2.putText(frame, "LIFT START", (frame_w - 300, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            if i == phases.get('end_of_pull_frame'):
                cv2.putText(frame, "END OF PULL", (frame_w - 300, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
            writer.write(frame)
        writer.release()
        writer = None

        st.markdown('</div>', unsafe_allow_html=True)

        # Upload video to cloud storage (falls back to local if R2 not configured)
        video_ref = storage.upload_video(output_path, output_filename)

        # Save session to database
        session_id = db.save_session(user["id"], lift_type, analysis_results, output_filename)
        db.log_action(user["id"], "save_session", lift_type, f"Analyzed {lift_type}, verdict: {analysis_results.get('verdict', 'Unknown')}")
        st.session_state["last_analysis"] = analysis_results
        st.session_state["last_session_id"] = session_id
        st.session_state["last_output_filename"] = output_filename
        st.session_state["last_lift_type"] = lift_type
        st.rerun()

    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        if cap:
            cap.release()
        if writer:
            writer.release()
        if 'video_path' in locals() and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except Exception:
                pass


def _display_results(user):
    """Display analysis results from session state. Survives Streamlit reruns."""
    analysis_results = st.session_state.get("last_analysis")
    output_filename = st.session_state.get("last_output_filename")
    lift_type = st.session_state.get("last_lift_type", "Lift")
    if not analysis_results or not output_filename:
        return

    output_path = os.path.join(OUTPUT_DIR, output_filename)
    verdict = analysis_results["verdict"]
    faults = analysis_results.get("faults_found", [])
    kd = analysis_results.get("kinematic_data", {})

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Video + Comparison side by side ──
    v_col, t_col = st.columns([1, 1.3])

    with v_col:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("#### 📹 Analyzed Video")
        if os.path.exists(output_path):
            with open(output_path, 'rb') as f:
                video_bytes = f.read()
            st.video(video_bytes)
            st.download_button("⬇️ Download Video", data=video_bytes, file_name=output_filename, mime="video/mp4")
        else:
            st.warning("Video file not found.")
        st.markdown('</div>', unsafe_allow_html=True)

    with t_col:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown(f"#### 📊 {lift_type} Results")

        comparison = generate_iwf_comparison(kd)

        table_rows = ""
        for item in comparison:
            if item["status"] == "pass":
                icon, row_bg, val_color = "✅", "rgba(16,185,129,0.06)", "var(--success)"
            elif item["status"] == "fail":
                icon, row_bg, val_color = "❌", "rgba(239,68,68,0.06)", "var(--danger)"
            else:
                icon, row_bg, val_color = "⚠️", "rgba(245,158,11,0.06)", "var(--warning)"
            table_rows += f'<tr style="background:{row_bg};"><td style="padding:0.7rem 0.75rem;border-bottom:1px solid var(--border-color);color:var(--text-primary);font-weight:500;font-size:0.85rem;">{icon} {item["label"]}</td><td style="padding:0.7rem 0.75rem;border-bottom:1px solid var(--border-color);text-align:center;color:{val_color};font-weight:700;font-size:0.9rem;">{item["captured"]}</td><td style="padding:0.7rem 0.75rem;border-bottom:1px solid var(--border-color);text-align:center;color:var(--text-muted);font-size:0.85rem;">{item["expected"]}</td></tr>'

        hs = "padding:0.65rem 0.75rem;color:var(--accent-light);font-size:0.78rem;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid var(--border-color);"
        table_html = f'<table style="width:100%;border-collapse:collapse;border-radius:var(--radius);overflow:hidden;border:1px solid var(--border-color);"><thead><tr style="background:rgba(124,58,237,0.12);"><th style="text-align:left;{hs}">Parameter</th><th style="text-align:center;{hs}">Captured</th><th style="text-align:center;{hs}">Standard Expected</th></tr></thead><tbody>{table_rows}</tbody></table>'
        st.markdown(table_html, unsafe_allow_html=True)

        passed_count = sum(1 for c in comparison if c["status"] == "pass")
        total_count = len(comparison)
        st.markdown(f'<div style="margin-top:0.75rem;text-align:center;color:var(--text-muted);font-size:0.82rem;">Score: <span style="color:var(--accent-light);font-weight:700;">{passed_count}/{total_count}</span> parameters meet standard guidelines</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Coaching Feedback Section ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="glass-card-static fade-in">', unsafe_allow_html=True)
    st.markdown("#### 🏋️ Coaching Feedback")

    if verdict == "Good Lift":
        st.markdown(f'<div style="background:var(--success-bg);border:1px solid rgba(16,185,129,0.3);border-radius:var(--radius);padding:1rem;margin-bottom:1rem;"><div style="color:var(--success);font-weight:700;font-size:1rem;margin-bottom:0.3rem;">🎉 Outstanding Performance!</div><div style="color:var(--text-secondary);font-size:0.9rem;">Your {lift_type} meets technical standards across all measured parameters. Keep refining and pushing for consistency.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:var(--warning-bg);border:1px solid rgba(245,158,11,0.3);border-radius:var(--radius);padding:1rem;margin-bottom:1rem;"><div style="color:var(--warning);font-weight:700;font-size:1rem;margin-bottom:0.3rem;">⚠️ Areas for Improvement Detected</div><div style="color:var(--text-secondary);font-size:0.9rem;">Your {lift_type} has {len(faults)} area{"s" if len(faults) != 1 else ""} that {"do" if len(faults) != 1 else "does"} not meet technical standards. Review the feedback below.</div></div>', unsafe_allow_html=True)

    for item in comparison:
        if item["status"] == "pass":
            st.markdown(f'<details style="margin-bottom:0.5rem;background:var(--success-bg);border:1px solid rgba(16,185,129,0.2);border-radius:10px;"><summary style="padding:0.75rem 1rem;cursor:pointer;color:var(--success);font-weight:600;font-size:0.9rem;">✅ {item["label"]} — {item["captured"]} (Meets Standard)</summary><div style="padding:0.5rem 1rem 0.75rem;color:var(--text-secondary);font-size:0.85rem;border-top:1px solid rgba(16,185,129,0.15);">{item["feedback"]}</div></details>', unsafe_allow_html=True)
        elif item["status"] == "fail":
            st.markdown(f'<details open style="margin-bottom:0.5rem;background:var(--danger-bg);border:1px solid rgba(239,68,68,0.2);border-radius:10px;"><summary style="padding:0.75rem 1rem;cursor:pointer;color:var(--danger);font-weight:600;font-size:0.9rem;">❌ {item["label"]} — {item["captured"]} (Below Standard: {item["expected"]})</summary><div style="padding:0.5rem 1rem 0.75rem;color:var(--text-secondary);font-size:0.85rem;border-top:1px solid rgba(239,68,68,0.15);"><strong style="color:var(--text-primary);">What to work on:</strong><br>{item["feedback"]}</div></details>', unsafe_allow_html=True)
        else:
            st.markdown(f'<details style="margin-bottom:0.5rem;background:var(--warning-bg);border:1px solid rgba(245,158,11,0.2);border-radius:10px;"><summary style="padding:0.75rem 1rem;cursor:pointer;color:var(--warning);font-weight:600;font-size:0.9rem;">⚠️ {item["label"]} — Could Not Measure</summary><div style="padding:0.5rem 1rem 0.75rem;color:var(--text-secondary);font-size:0.85rem;border-top:1px solid rgba(245,158,11,0.15);">{item["feedback"]}</div></details>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Raw data expander ──
    with st.expander("📄 Full Analysis Data (JSON)"):
        st.json(analysis_results)

    # ── Save to gallery ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
    st.markdown("#### 💾 Save to Gallery?")
    g_c1, g_c2 = st.columns([3, 1])
    with g_c1:
        gallery_title = st.text_input("Title", value=f"{lift_type} Analysis — {time.strftime('%b %d, %Y')}", key="gallery_title")
        gallery_notes = st.text_area("Notes (optional)", key="gallery_notes", placeholder="Add observations about this lift...")
    with g_c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save", key="save_gallery", use_container_width=True):
            sid = st.session_state.get("last_session_id")
            if sid:
                db.save_to_gallery(sid, user["id"], gallery_title, gallery_notes)
                st.success("Saved to gallery!")
            else:
                st.error("No analysis session found. Please run the analysis first.")

        if st.button("🔄 Analyze Another", key="do_another", use_container_width=True):
            for k in ["last_analysis", "last_session_id", "last_output_filename", "last_lift_type"]:
                st.session_state.pop(k, None)
            navigate("analyze")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)



# ═══════════════════════════════════════════════════════════
#  PAGE: GALLERY
# ═══════════════════════════════════════════════════════════

def page_gallery():
    render_navbar()
    user = st.session_state["user"]

    # ── Detail view ──
    detail_id = st.session_state.get("gallery_detail_id")
    if detail_id is not None:
        _gallery_detail_view(user, detail_id)
        return

    # ── List view ──
    st.markdown("""
    <div class="fade-in">
        <div class="page-title">🖼️ Gallery</div>
        <div class="page-subtitle">Your saved analyses and training history</div>
    </div>
    """, unsafe_allow_html=True)

    items = db.get_user_gallery(user["id"])

    if not items:
        st.markdown("""
        <div class="glass-card-static empty-state">
            <div class="empty-icon">🖼️</div>
            <div class="empty-text">Your gallery is empty</div>
            <div class="empty-hint">Analyze a lift and save it to start building your training history</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🎯 Analyze Your First Lift", key="gallery_to_analyze", use_container_width=True):
            navigate("analyze")
            st.rerun()
        return

    for item in items:
        st.markdown('<div class="glass-card" style="margin-bottom: 1rem;">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            video_path = os.path.join(OUTPUT_DIR, item["video_filename"]) if item.get("video_filename") else None
            if video_path and os.path.exists(video_path):
                st.video(video_path)
        with c2:
            faults = json.loads(item["faults_json"]) if item.get("faults_json") else []
            fault_str = ", ".join(faults) if faults else "No faults"
            st.markdown(f"""
            <div class="gallery-title">{item['title']}</div>
            <div class="gallery-date">{item['lift_type']} — {str(item['session_date'])[:16]}</div>
            <div style="margin-top: 0.5rem; color: var(--text-muted); font-size: 0.85rem;">{fault_str}</div>
            """, unsafe_allow_html=True)
            if item.get("notes"):
                st.markdown(f"<div style='color: var(--text-secondary); font-size: 0.85rem; margin-top: 0.5rem;'>📝 {item['notes']}</div>", unsafe_allow_html=True)
        with c3:
            if st.button("🔍 View", key=f"view_gallery_{item['id']}", use_container_width=True, help="View full analysis"):
                st.session_state["gallery_detail_id"] = item["id"]
                st.rerun()
            if st.button("🗑️", key=f"del_gallery_{item['id']}", help="Remove from gallery"):
                db.delete_gallery_item(item["id"], user["id"])
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def _gallery_detail_view(user, gallery_id):
    """Render full detail view for a gallery item with IWF comparison."""
    items = db.get_user_gallery(user["id"])
    item = next((i for i in items if i["id"] == gallery_id), None)
    if not item:
        st.error("Gallery item not found.")
        if st.button("← Back to Gallery"):
            st.session_state.pop("gallery_detail_id", None)
            st.rerun()
        return

    if st.button("← Back to Gallery", key="back_to_gallery"):
        st.session_state.pop("gallery_detail_id", None)
        st.rerun()

    verdict = item["verdict"]
    lift_type = item["lift_type"]
    faults = json.loads(item["faults_json"]) if item.get("faults_json") else []
    kd = json.loads(item["kinematic_json"]) if item.get("kinematic_json") else {}
    session_date = str(item.get("session_date", ""))[:16]

    st.markdown(f'<div class="fade-in"><div class="page-title">{item["title"]}</div><div class="page-subtitle">{lift_type} · {session_date}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    v_col, t_col = st.columns([1, 1.3])

    with v_col:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("#### 📹 Analyzed Video")
        video_path = os.path.join(OUTPUT_DIR, item["video_filename"]) if item.get("video_filename") else None
        if video_path and os.path.exists(video_path):
            st.video(video_path)
        else:
            st.warning("Video file not available.")
        if item.get("notes"):
            st.markdown(f'<div style="margin-top:1rem;padding:0.75rem;background:var(--bg-input);border-radius:var(--radius);border:1px solid var(--border-color);"><div style="color:var(--text-muted);font-size:0.78rem;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.3rem;">Notes</div><div style="color:var(--text-secondary);font-size:0.9rem;">{item["notes"]}</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with t_col:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown(f"#### 📊 {lift_type} Results")
        comparison = generate_iwf_comparison(kd)
        table_rows = ""
        for ci in comparison:
            if ci["status"] == "pass":
                icon, row_bg, val_color = "✅", "rgba(16,185,129,0.06)", "var(--success)"
            elif ci["status"] == "fail":
                icon, row_bg, val_color = "❌", "rgba(239,68,68,0.06)", "var(--danger)"
            else:
                icon, row_bg, val_color = "⚠️", "rgba(245,158,11,0.06)", "var(--warning)"
            table_rows += f'<tr style="background:{row_bg};"><td style="padding:0.7rem 0.75rem;border-bottom:1px solid var(--border-color);color:var(--text-primary);font-weight:500;font-size:0.85rem;">{icon} {ci["label"]}</td><td style="padding:0.7rem 0.75rem;border-bottom:1px solid var(--border-color);text-align:center;color:{val_color};font-weight:700;font-size:0.9rem;">{ci["captured"]}</td><td style="padding:0.7rem 0.75rem;border-bottom:1px solid var(--border-color);text-align:center;color:var(--text-muted);font-size:0.85rem;">{ci["expected"]}</td></tr>'

        hs = "padding:0.65rem 0.75rem;color:var(--accent-light);font-size:0.78rem;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid var(--border-color);"
        st.markdown(f'<table style="width:100%;border-collapse:collapse;border-radius:var(--radius);overflow:hidden;border:1px solid var(--border-color);"><thead><tr style="background:rgba(124,58,237,0.12);"><th style="text-align:left;{hs}">Parameter</th><th style="text-align:center;{hs}">Captured</th><th style="text-align:center;{hs}">Standard Expected</th></tr></thead><tbody>{table_rows}</tbody></table>', unsafe_allow_html=True)
        passed_count = sum(1 for c in comparison if c["status"] == "pass")
        st.markdown(f'<div style="margin-top:0.75rem;text-align:center;color:var(--text-muted);font-size:0.82rem;">Score: <span style="color:var(--accent-light);font-weight:700;">{passed_count}/{len(comparison)}</span> parameters meet standard guidelines</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Coaching Feedback
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="glass-card-static fade-in">', unsafe_allow_html=True)
    st.markdown("#### 🏋️ Coaching Feedback")
    if verdict == "Good Lift":
        st.markdown(f'<div style="background:var(--success-bg);border:1px solid rgba(16,185,129,0.3);border-radius:var(--radius);padding:1rem;margin-bottom:1rem;"><div style="color:var(--success);font-weight:700;font-size:1rem;margin-bottom:0.3rem;">🎉 Outstanding Performance!</div><div style="color:var(--text-secondary);font-size:0.9rem;">Your {lift_type} meets technical standards across all measured parameters.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:var(--warning-bg);border:1px solid rgba(245,158,11,0.3);border-radius:var(--radius);padding:1rem;margin-bottom:1rem;"><div style="color:var(--warning);font-weight:700;font-size:1rem;margin-bottom:0.3rem;">⚠️ Areas for Improvement</div><div style="color:var(--text-secondary);font-size:0.9rem;">Your {lift_type} has {len(faults)} area{"s" if len(faults) != 1 else ""} below standard.</div></div>', unsafe_allow_html=True)
    for ci in comparison:
        if ci["status"] == "pass":
            st.markdown(f'<details style="margin-bottom:0.5rem;background:var(--success-bg);border:1px solid rgba(16,185,129,0.2);border-radius:10px;"><summary style="padding:0.75rem 1rem;cursor:pointer;color:var(--success);font-weight:600;font-size:0.9rem;">✅ {ci["label"]} — {ci["captured"]} (Meets Standard)</summary><div style="padding:0.5rem 1rem 0.75rem;color:var(--text-secondary);font-size:0.85rem;border-top:1px solid rgba(16,185,129,0.15);">{ci["feedback"]}</div></details>', unsafe_allow_html=True)
        elif ci["status"] == "fail":
            st.markdown(f'<details open style="margin-bottom:0.5rem;background:var(--danger-bg);border:1px solid rgba(239,68,68,0.2);border-radius:10px;"><summary style="padding:0.75rem 1rem;cursor:pointer;color:var(--danger);font-weight:600;font-size:0.9rem;">❌ {ci["label"]} — {ci["captured"]} (Below: {ci["expected"]})</summary><div style="padding:0.5rem 1rem 0.75rem;color:var(--text-secondary);font-size:0.85rem;border-top:1px solid rgba(239,68,68,0.15);"><strong style="color:var(--text-primary);">What to work on:</strong><br>{ci["feedback"]}</div></details>', unsafe_allow_html=True)
        else:
            st.markdown(f'<details style="margin-bottom:0.5rem;background:var(--warning-bg);border:1px solid rgba(245,158,11,0.2);border-radius:10px;"><summary style="padding:0.75rem 1rem;cursor:pointer;color:var(--warning);font-weight:600;font-size:0.9rem;">⚠️ {ci["label"]} — Could Not Measure</summary><div style="padding:0.5rem 1rem 0.75rem;color:var(--text-secondary);font-size:0.85rem;border-top:1px solid rgba(245,158,11,0.15);">{ci["feedback"]}</div></details>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("📄 Full Kinematic Data (JSON)"):
        st.json(kd)




# ═══════════════════════════════════════════════════════════
#  PAGE: PROFILE
# ═══════════════════════════════════════════════════════════

def page_profile():
    render_navbar()
    user = st.session_state["user"]
    u = db.get_user(user["id"])

    st.markdown("""
    <div class="fade-in">
        <div class="page-title">👤 My Profile</div>
        <div class="page-subtitle">View and manage your athlete profile</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Profile Header with Photo ──
    initial = u["username"][0].upper()
    photo_path = u.get("profile_photo", "")
    full_photo = os.path.join(APP_DIR, photo_path) if photo_path else ""
    has_photo = photo_path and os.path.exists(full_photo)

    if has_photo:
        photo_html = f'<img src="data:image/png;base64,{_img_to_base64(full_photo)}" class="profile-photo-img">'
    else:
        photo_html = f'<div class="profile-avatar">{initial}</div>'

    display_name = u["full_name"] or u["username"]
    bio_text = u.get("bio") or ""
    member_since = str(u["created_at"])[:10] if u.get("created_at") else "N/A"

    st.markdown(f"""
    <div class="glass-card-static fade-in" style="text-align:center; padding: 2rem; margin-bottom: 1.5rem;">
        {photo_html}
        <div style="font-family: var(--font-heading); font-size: 1.5rem; font-weight: 700; margin-top: 0.5rem;">{display_name}</div>
        <div style="color: var(--text-muted); font-size: 0.88rem;">@{u['username']} · {u['role'].capitalize()}</div>
        <div style="color: var(--text-muted); font-size: 0.8rem; margin-top: 0.25rem;">Member since {member_since}</div>
        {"<div style='color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.75rem; font-style: italic;'>" + bio_text + "</div>" if bio_text else ""}
    </div>
    """, unsafe_allow_html=True)

    # ── Quick Stats Row ──
    sessions = db.get_user_sessions(u["id"])
    total = len(sessions)
    good = sum(1 for s in sessions if s.get("verdict") == "Good Lift")

    _col1, _col2, _col3, _col4 = st.columns(4)
    with _col1:
        _profile_info_card("📧", "Email", u.get("email", "—"))
    with _col2:
        age_str = f"{u['age']} yrs" if u.get("age") else "—"
        _profile_info_card("🎂", "Age", age_str)
    with _col3:
        w_str = f"{u['weight_kg']} kg" if u.get("weight_kg") else "—"
        _profile_info_card("⚖️", "Weight", w_str)
    with _col4:
        h_str = f"{u['height_cm']} cm" if u.get("height_cm") else "—"
        _profile_info_card("📏", "Height", h_str)

    _col5, _col6, _col7, _col8 = st.columns(4)
    with _col5:
        _profile_info_card("⚧", "Gender", u.get("gender") or "—")
    with _col6:
        _profile_info_card("🏆", "Experience", u.get("experience_level") or "—")
    with _col7:
        _profile_info_card("🏋️", "Preferred Lift", u.get("preferred_lift") or "—")
    with _col8:
        rate = f"{round(good / total * 100)}%" if total > 0 else "—"
        _profile_info_card("📊", "Success Rate", rate)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Edit Tabs ──
    tab1, tab2, tab3, tab4 = st.tabs(["✏️ Personal Info", "🏋️ Athlete Details", "📸 Profile Photo", "🔒 Password"])

    with tab1:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("#### Personal Information")
        p_name = st.text_input("Full Name", value=u.get("full_name") or "", key="p_name")
        p_email = st.text_input("Email Address", value=u.get("email") or "", key="p_email")
        p1, p2 = st.columns(2)
        with p1:
            p_age = st.number_input("Age", min_value=0, max_value=120, value=u.get("age") or 0, step=1, key="p_age")
        with p2:
            gender_options = ["", "Male", "Female", "Other", "Prefer not to say"]
            current_gender = u.get("gender") or ""
            idx = gender_options.index(current_gender) if current_gender in gender_options else 0
            p_gender = st.selectbox("Gender", gender_options, index=idx, key="p_gender")
        p_bio = st.text_area("Bio", value=u.get("bio") or "", key="p_bio",
                             placeholder="Tell us a bit about yourself — training goals, lifting background...")

        if st.button("💾 Save Personal Info", key="save_personal", use_container_width=True):
            result = db.update_profile(
                u["id"],
                full_name=p_name,
                email=p_email,
                age=p_age if p_age > 0 else None,
                gender=p_gender,
                bio=p_bio,
            )
            if result["success"]:
                st.session_state["user"]["full_name"] = p_name
                st.session_state["user"]["email"] = p_email
                st.success(result["message"])
                st.rerun()
            else:
                st.error(result["message"])
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("#### Athlete Details")
        a1, a2 = st.columns(2)
        with a1:
            a_weight = st.number_input("Body Weight (kg)", min_value=0.0, max_value=300.0,
                                        value=float(u.get("weight_kg") or 0), step=0.5, format="%.1f", key="a_weight")
        with a2:
            a_height = st.number_input("Height (cm)", min_value=0.0, max_value=250.0,
                                        value=float(u.get("height_cm") or 0), step=0.5, format="%.1f", key="a_height")
        a3, a4 = st.columns(2)
        with a3:
            exp_options = ["", "Beginner", "Intermediate", "Advanced", "Elite", "Professional"]
            cur_exp = u.get("experience_level") or ""
            exp_idx = exp_options.index(cur_exp) if cur_exp in exp_options else 0
            a_exp = st.selectbox("Experience Level", exp_options, index=exp_idx, key="a_exp")
        with a4:
            lift_options = ["", "Snatch", "Clean & Jerk", "Both"]
            cur_lift = u.get("preferred_lift") or ""
            lift_idx = lift_options.index(cur_lift) if cur_lift in lift_options else 0
            a_lift = st.selectbox("Preferred Lift", lift_options, index=lift_idx, key="a_lift")

        # BMI calculation display
        if a_weight > 0 and a_height > 0:
            bmi = round(a_weight / ((a_height / 100) ** 2), 1)
            st.markdown(f"""
            <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 0.75rem 1rem; margin-top: 0.5rem;">
                <span style="color: var(--text-muted); font-size: 0.82rem;">Calculated BMI:</span>
                <span style="color: var(--accent-light); font-weight: 700; font-size: 1.1rem; margin-left: 0.5rem;">{bmi}</span>
            </div>
            """, unsafe_allow_html=True)

        if st.button("💾 Save Athlete Details", key="save_athlete", use_container_width=True):
            result = db.update_profile(
                u["id"],
                weight_kg=a_weight if a_weight > 0 else None,
                height_cm=a_height if a_height > 0 else None,
                experience_level=a_exp,
                preferred_lift=a_lift,
            )
            if result["success"]:
                st.success(result["message"])
                st.rerun()
            else:
                st.error(result["message"])
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("#### Profile Photo")

        # Show current photo
        if has_photo:
            st.image(full_photo, width=180, caption="Current profile photo")
        else:
            st.markdown("""
            <div class="empty-state" style="padding: 1.5rem;">
                <div class="empty-icon">📷</div>
                <div class="empty-text">No profile photo set</div>
                <div class="empty-hint">Upload a photo to personalize your profile</div>
            </div>
            """, unsafe_allow_html=True)

        uploaded_photo = st.file_uploader(
            "Upload a new photo",
            type=["png", "jpg", "jpeg", "webp"],
            key="photo_upload",
            help="Recommended: square image, at least 200×200 pixels"
        )
        if uploaded_photo:
            st.image(uploaded_photo, width=180, caption="Preview")
            if st.button("📸 Set as Profile Photo", key="save_photo", use_container_width=True):
                photo_bytes = uploaded_photo.read()
                saved_path = db.save_profile_photo(u["id"], photo_bytes, uploaded_photo.name)
                st.success("Profile photo updated!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab4:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("#### Change Password")
        old_pw = st.text_input("Current Password", type="password", key="old_pw")
        new_pw = st.text_input("New Password", type="password", key="new_pw", help="Minimum 6 characters")
        confirm_pw = st.text_input("Confirm New Password", type="password", key="confirm_pw")
        if st.button("🔒 Update Password", key="change_pw", use_container_width=True):
            if new_pw != confirm_pw:
                st.error("Passwords do not match.")
            elif not old_pw or not new_pw:
                st.warning("Please fill in all fields.")
            else:
                result = db.change_password(user["id"], old_pw, new_pw)
                if result["success"]:
                    st.success(result["message"])
                else:
                    st.error(result["message"])
        st.markdown('</div>', unsafe_allow_html=True)


def _profile_info_card(icon: str, label: str, value: str):
    """Render a small info card for the profile page."""
    st.markdown(f"""
    <div class="glass-card stat-card" style="padding: 0.9rem;">
        <div style="font-size: 1.3rem;">{icon}</div>
        <div style="font-family: var(--font-heading); font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin: 0.2rem 0;">{value}</div>
        <div class="stat-label" style="font-size: 0.72rem;">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def _img_to_base64(img_path: str) -> str:
    """Convert an image file to base64 for inline HTML embedding."""
    import base64
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ═══════════════════════════════════════════════════════════
#  PAGE: FORCED PASSWORD RESET (after admin reactivation)
# ═══════════════════════════════════════════════════════════

def page_force_reset_password():
    st.markdown('<div class="auth-container fade-in"><div class="auth-logo"><h1>🔐 Password Reset Required</h1><p>Your account was reactivated by an administrator. You must set a new password to continue.</p></div></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown("#### Set New Password")

        user = st.session_state.get("user")
        if not user:
            st.error("Session expired. Please log in again.")
            if st.button("Go to Login", use_container_width=True):
                navigate("login")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            return

        st.markdown(f'<div style="color:var(--text-muted);font-size:0.85rem;margin-bottom:1rem;">Logged in as <strong>@{user["username"]}</strong></div>', unsafe_allow_html=True)

        new_password = st.text_input("New Password", type="password", key="force_new_pw", placeholder="Minimum 6 characters")
        confirm_password = st.text_input("Confirm New Password", type="password", key="force_confirm_pw", placeholder="Re-enter your new password")

        if st.button("🔒 Set New Password", key="force_reset_btn", use_container_width=True):
            if not new_password or not confirm_password:
                st.warning("Please fill in both fields.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                result = db.force_reset_password(user["id"], new_password)
                if result["success"]:
                    st.success(result["message"])
                    updated_user = db.get_user(user["id"])
                    st.session_state["user"] = dict(updated_user)
                    if user["role"] == "admin":
                        navigate("admin_dashboard")
                    else:
                        navigate("home")
                    st.rerun()
                else:
                    st.error(result["message"])

        st.markdown("---")
        if st.button("🚪 Log Out Instead", key="force_reset_logout", use_container_width=True):
            logout()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  PAGE: ADMIN DASHBOARD
# ═══════════════════════════════════════════════════════════

def page_admin_dashboard():
    render_navbar()
    st.markdown("""
    <div class="fade-in">
        <div class="page-title">📊 Admin Dashboard</div>
        <div class="page-subtitle">System overview and analytics</div>
    </div>
    """, unsafe_allow_html=True)

    stats = db.get_admin_stats()

    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, str(stats["total_users"]), "Total Users", ""),
        (c2, str(stats["active_users"]), "Active Users", "success"),
        (c3, str(stats["total_sessions"]), "Analyses Run", ""),
        (c4, str(stats["good_lifts"]), "Good Lifts", "success"),
        (c5, str(stats["bad_lifts"]), "Bad Lifts", "danger"),
    ]
    for col, val, label, cls in metrics:
        with col:
            st.markdown(f"""<div class="glass-card stat-card">
                <div class="stat-value {cls}">{val}</div>
                <div class="stat-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Recent sessions
    st.markdown('<div class="page-title" style="font-size:1.2rem;">📋 Recent Analyses (All Users)</div>', unsafe_allow_html=True)
    if stats["recent_sessions"]:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        for s in stats["recent_sessions"]:
            verdict_class = "verdict-good" if s["verdict"] == "Good Lift" else "verdict-bad"
            st.markdown(f"""
            <div class="user-row">
                <div>
                    <strong>@{s['username']}</strong>
                    <span style="color: var(--text-muted); margin-left: 0.5rem;">{s['lift_type']}</span>
                    <span style="color: var(--text-muted); font-size: 0.8rem; margin-left: 0.5rem;">{str(s['created_at'])[:16]}</span>
                </div>
                <span class="{verdict_class}">{s['verdict']}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No analyses have been run yet.")


# ═══════════════════════════════════════════════════════════
#  PAGE: ADMIN USER MANAGEMENT
# ═══════════════════════════════════════════════════════════

def page_admin_users():
    render_navbar()
    st.markdown("""
    <div class="fade-in">
        <div class="page-title">👥 User Management</div>
        <div class="page-subtitle">Manage registered users — activate, deactivate, or remove accounts</div>
    </div>
    """, unsafe_allow_html=True)

    users = db.get_all_users()

    st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
    for u in users:
        status_class = "status-active" if u["is_active"] else "status-inactive"
        status_text = "Active" if u["is_active"] else "Inactive"
        role_badge = "👑 Admin" if u["role"] == "admin" else "👤 User"

        c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 2])
        with c1:
            st.markdown(f"""
            <div style="padding: 0.5rem 0;">
                <strong>@{u['username']}</strong>
                <span style="color: var(--text-muted); font-size: 0.82rem; margin-left: 0.5rem;">{u['email']}</span>
                <div style="color: var(--text-muted); font-size: 0.78rem;">{u.get('full_name', '')}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='padding: 0.75rem 0;'>{role_badge}</div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div style='padding: 0.75rem 0;'><span class='{status_class}'>● {status_text}</span></div>", unsafe_allow_html=True)
            if not u["is_active"] and u.get("deactivation_reason"):
                st.markdown(f"<div style='color: var(--danger); font-size: 0.75rem; margin-top: -0.5rem;'>⚠️ {u['deactivation_reason']}</div>", unsafe_allow_html=True)
        with c4:
            if u["role"] != "admin":
                bc1, bc2 = st.columns(2)
                with bc1:
                    label = "Deactivate" if u["is_active"] else "Activate"
                    if st.button(label, key=f"toggle_{u['id']}", use_container_width=True):
                        db.toggle_user_active(u["id"])
                        admin_user = st.session_state.get("user")
                        if admin_user:
                            db.log_action(admin_user["id"], "toggle_user", u["username"], f"{'Deactivated' if u['is_active'] else 'Activated'} user @{u['username']}")
                        st.rerun()
                with bc2:
                    if st.button("Delete", key=f"delete_{u['id']}", use_container_width=True):
                        db.soft_delete_user(u["id"])
                        admin_user = st.session_state.get("user")
                        if admin_user:
                            db.log_action(admin_user["id"], "delete_user", u["username"], f"Soft-deleted user @{u['username']}")
                        st.rerun()
        st.markdown("<hr style='margin: 0; opacity: 0.2;'>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  PAGE: ADMIN CONTENT / SETTINGS
# ═══════════════════════════════════════════════════════════

def page_admin_content():
    render_navbar()
    st.markdown("""
    <div class="fade-in">
        <div class="page-title">⚙️ App Settings</div>
        <div class="page-subtitle">Content management — configure application settings</div>
    </div>
    """, unsafe_allow_html=True)

    settings = db.get_all_settings()

    st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
    st.markdown("#### General")
    app_name = st.text_input("App Name", value=settings.get("app_name", "LiftCoach AI"), key="set_name")
    tagline = st.text_input("Tagline", value=settings.get("tagline", ""), key="set_tagline")

    st.markdown("#### Analysis Configuration")
    complexity = st.selectbox("Model Complexity", ["0 (Lite)", "1 (Full)", "2 (Heavy)"],
                              index=int(settings.get("model_complexity", "1")), key="set_complexity")
    confidence = st.slider("Detection Confidence", 0.1, 1.0,
                            float(settings.get("detection_confidence", "0.5")), 0.05, key="set_confidence")

    if st.button("💾 Save Settings", key="save_settings", use_container_width=True):
        db.set_setting("app_name", app_name)
        db.set_setting("tagline", tagline)
        db.set_setting("model_complexity", complexity[0])
        db.set_setting("detection_confidence", str(confidence))
        admin_user = st.session_state.get("user")
        if admin_user:
            db.log_action(admin_user["id"], "update_settings", "app_settings", "Updated app name, tagline, model complexity, and detection confidence")
        st.success("Settings saved!")
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  PAGE: SUPER ADMIN
# ═══════════════════════════════════════════════════════════

def page_super_admin():
    render_navbar()
    st.markdown("""
    <div class="fade-in">
        <div class="page-title">🛡️ Super Admin Panel</div>
        <div class="page-subtitle">System-wide administration, audit trails, and database management</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🔧 Admin Management", "⚙️ System Configuration", "📋 Audit Trails", "🗄️ Database Management"])

    # ── Tab 1: Admin Management ──
    with tab1:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("#### Administrator Accounts")
        st.markdown('<div style="color:var(--text-muted);font-size:0.85rem;margin-bottom:1rem;">Manage administrator accounts and permissions. Promote users to admin or revoke admin access.</div>', unsafe_allow_html=True)

        admins = db.get_all_admins()
        for a in admins:
            c1, c2, c3 = st.columns([3, 1.5, 2])
            with c1:
                role_icon = "🛡️" if a["role"] == "super_admin" else "👑"
                st.markdown(f'<div style="padding:0.5rem 0;"><strong>{role_icon} @{a["username"]}</strong> <span style="color:var(--text-muted);font-size:0.82rem;margin-left:0.5rem;">{a["email"]}</span><br><span style="color:var(--text-muted);font-size:0.78rem;">{a.get("full_name", "")}</span></div>', unsafe_allow_html=True)
            with c2:
                role_label = "Super Admin" if a["role"] == "super_admin" else "Admin"
                st.markdown(f'<div style="padding:0.75rem 0;"><span style="background:rgba(124,58,237,0.15);color:var(--accent-light);padding:0.3rem 0.7rem;border-radius:20px;font-size:0.8rem;font-weight:600;">{role_label}</span></div>', unsafe_allow_html=True)
            with c3:
                if a["role"] != "super_admin":
                    if st.button("Demote to User", key=f"demote_{a['id']}", use_container_width=True):
                        db.set_user_role(a["id"], "user")
                        me = st.session_state.get("user")
                        if me:
                            db.log_action(me["id"], "demote_admin", a["username"], f"Demoted @{a['username']} from admin to user")
                        st.rerun()
            st.markdown("<hr style='margin:0;opacity:0.2;'>", unsafe_allow_html=True)

        # Promote a user to admin
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Promote User to Admin")
        all_users = db.get_all_users()
        regular_users = [u for u in all_users if u["role"] == "user" and u["is_active"]]
        if regular_users:
            user_options = {f"@{u['username']} ({u['email']})": u["id"] for u in regular_users}
            selected = st.selectbox("Select a user to promote", list(user_options.keys()), key="promote_select")
            if st.button("👑 Promote to Admin", key="promote_btn", use_container_width=True):
                uid = user_options[selected]
                db.set_user_role(uid, "admin")
                me = st.session_state.get("user")
                if me:
                    db.log_action(me["id"], "promote_admin", selected.split(" ")[0][1:], f"Promoted user to admin")
                st.success(f"Promoted {selected} to Admin.")
                st.rerun()
        else:
            st.info("No regular users available to promote.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Tab 2: System Configuration ──
    with tab2:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("#### Global System Settings")

        settings = db.get_all_settings()

        st.markdown("##### Application")
        sa_app_name = st.text_input("App Name", value=settings.get("app_name", "LiftCoach AI"), key="sa_app_name")
        sa_tagline = st.text_input("Tagline", value=settings.get("tagline", ""), key="sa_tagline")

        st.markdown("##### Analysis Engine")
        sa_complexity = st.selectbox("Model Complexity", ["0 (Lite)", "1 (Full)", "2 (Heavy)"],
                                     index=int(settings.get("model_complexity", "1")), key="sa_complexity")
        sa_confidence = st.slider("Detection Confidence", 0.1, 1.0,
                                   float(settings.get("detection_confidence", "0.5")), 0.05, key="sa_confidence")

        st.markdown("##### Security")
        sa_max_attempts = st.number_input("Max Login Attempts", min_value=1, max_value=20,
                                           value=int(settings.get("max_login_attempts", "5")), step=1, key="sa_max_attempts")

        st.markdown("##### Storage")
        stor = storage.storage_status()
        if stor["r2_enabled"]:
            st.markdown(f'<div style="background:var(--success-bg);border:1px solid rgba(16,185,129,0.3);border-radius:var(--radius);padding:0.75rem 1rem;"><span style="color:var(--success);font-weight:600;">☁️ Cloudflare R2 Connected</span><br><span style="color:var(--text-muted);font-size:0.82rem;">Bucket: {stor["r2_bucket"]} · URL: {stor["r2_public_url"]}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:var(--warning-bg);border:1px solid rgba(245,158,11,0.3);border-radius:var(--radius);padding:0.75rem 1rem;"><span style="color:var(--warning);font-weight:600;">📁 Local Storage Mode</span><br><span style="color:var(--text-muted);font-size:0.82rem;">Configure R2 credentials in .env to enable cloud storage</span></div>', unsafe_allow_html=True)

        if st.button("💾 Save Configuration", key="sa_save_config", use_container_width=True):
            db.set_setting("app_name", sa_app_name)
            db.set_setting("tagline", sa_tagline)
            db.set_setting("model_complexity", sa_complexity[0])
            db.set_setting("detection_confidence", str(sa_confidence))
            db.set_setting("max_login_attempts", str(sa_max_attempts))
            me = st.session_state.get("user")
            if me:
                db.log_action(me["id"], "update_settings", "system_config", "Updated system configuration via Super Admin panel")
            st.success("Configuration saved!")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Tab 3: Audit Trails ──
    with tab3:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("#### Complete Audit Trail")
        st.markdown('<div style="color:var(--text-muted);font-size:0.85rem;margin-bottom:1rem;">All system actions are logged here for security and compliance tracking.</div>', unsafe_allow_html=True)

        log_limit = st.selectbox("Show recent", [50, 100, 250, 500], index=1, key="audit_limit")
        logs = db.get_audit_logs(limit=log_limit)

        if logs:
            # Action filter
            all_actions = sorted(set(l["action"] for l in logs))
            selected_actions = st.multiselect("Filter by action", all_actions, default=all_actions, key="audit_filter")
            filtered = [l for l in logs if l["action"] in selected_actions]

            action_colors = {
                "login": "var(--success)", "logout": "var(--text-muted)",
                "toggle_user": "var(--warning)", "delete_user": "var(--danger)",
                "promote_admin": "var(--accent-light)", "demote_admin": "var(--warning)",
                "update_settings": "var(--accent-light)", "save_session": "var(--success)",
            }

            for log in filtered:
                color = action_colors.get(log["action"], "var(--text-secondary)")
                ts = str(log["created_at"])[:19]
                st.markdown(f"""
                <div style="display:flex;align-items:center;padding:0.5rem 0;border-bottom:1px solid var(--border-color);">
                    <div style="min-width:140px;color:var(--text-muted);font-size:0.78rem;">{str(log['created_at'])[:19]}</div>
                    <div style="min-width:100px;"><span style="background:rgba(124,58,237,0.1);color:{color};padding:0.2rem 0.6rem;border-radius:12px;font-size:0.78rem;font-weight:600;">{log['action']}</span></div>
                    <div style="min-width:100px;color:var(--text-primary);font-weight:500;font-size:0.85rem;">@{log['username']}</div>
                    <div style="flex:1;color:var(--text-muted);font-size:0.82rem;">{log.get('details', '')}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f'<div style="margin-top:0.75rem;text-align:center;color:var(--text-muted);font-size:0.8rem;">Showing {len(filtered)} of {len(logs)} entries</div>', unsafe_allow_html=True)
        else:
            st.info("No audit logs recorded yet. Actions will appear here as users interact with the system.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Tab 4: Database Management ──
    with tab4:
        st.markdown('<div class="glass-card-static">', unsafe_allow_html=True)
        st.markdown("#### Database Overview")
        st.markdown('<div style="color:var(--text-muted);font-size:0.85rem;margin-bottom:1rem;">Monitor database table sizes and data integrity.</div>', unsafe_allow_html=True)

        stats = db.get_db_table_stats()
        total_rows = sum(s["rows"] for s in stats)

        # Summary row
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.markdown(f'<div class="glass-card stat-card"><div class="stat-value">{len(stats)}</div><div class="stat-label">Tables</div></div>', unsafe_allow_html=True)
        with mc2:
            st.markdown(f'<div class="glass-card stat-card"><div class="stat-value">{total_rows}</div><div class="stat-label">Total Rows</div></div>', unsafe_allow_html=True)
        with mc3:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "liftcoach.db")
            db_size = os.path.getsize(db_path) / 1024 if os.path.exists(db_path) else 0
            size_str = f"{db_size:.1f} KB" if db_size < 1024 else f"{db_size/1024:.1f} MB"
            st.markdown(f'<div class="glass-card stat-card"><div class="stat-value">{size_str}</div><div class="stat-label">Database Size</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Table Details")

        hs = "padding:0.65rem 0.75rem;color:var(--accent-light);font-size:0.78rem;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid var(--border-color);"
        rows_html = ""
        for s in stats:
            pct = round(s["rows"] / total_rows * 100, 1) if total_rows > 0 else 0
            rows_html += f'<tr><td style="padding:0.7rem 0.75rem;border-bottom:1px solid var(--border-color);color:var(--text-primary);font-weight:500;font-size:0.9rem;">📋 {s["table"]}</td><td style="padding:0.7rem 0.75rem;border-bottom:1px solid var(--border-color);text-align:center;color:var(--accent-light);font-weight:700;font-size:0.9rem;">{s["rows"]}</td><td style="padding:0.7rem 0.75rem;border-bottom:1px solid var(--border-color);text-align:center;color:var(--text-muted);font-size:0.85rem;">{pct}%</td></tr>'

        table_html = f'<table style="width:100%;border-collapse:collapse;border-radius:var(--radius);overflow:hidden;border:1px solid var(--border-color);"><thead><tr style="background:rgba(124,58,237,0.12);"><th style="text-align:left;{hs}">Table Name</th><th style="text-align:center;{hs}">Row Count</th><th style="text-align:center;{hs}">% of Total</th></tr></thead><tbody>{rows_html}</tbody></table>'
        st.markdown(table_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Data Integrity Check")
        if st.button("🔍 Run Integrity Check", key="integrity_check", use_container_width=True):
            try:
                conn = db.get_connection()
                result = conn.execute("PRAGMA integrity_check").fetchone()
                fk_result = conn.execute("PRAGMA foreign_key_check").fetchall()
                conn.close()

                if result[0] == "ok" and not fk_result:
                    st.markdown('<div style="background:var(--success-bg);border:1px solid rgba(16,185,129,0.3);border-radius:var(--radius);padding:1rem;"><span style="color:var(--success);font-weight:700;">✅ Database integrity check passed</span><br><span style="color:var(--text-muted);font-size:0.85rem;">All tables and foreign key constraints are valid.</span></div>', unsafe_allow_html=True)
                else:
                    issues = result[0] if result[0] != "ok" else f"{len(fk_result)} foreign key violation(s)"
                    st.markdown(f'<div style="background:var(--danger-bg);border:1px solid rgba(239,68,68,0.3);border-radius:var(--radius);padding:1rem;"><span style="color:var(--danger);font-weight:700;">⚠️ Issues detected</span><br><span style="color:var(--text-muted);font-size:0.85rem;">{issues}</span></div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Integrity check failed: {e}")
        st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  ROUTER
# ═══════════════════════════════════════════════════════════

def main():
    user = st.session_state.get("user")
    page = st.session_state.get("page", "login")

    # Auth guard: redirect to login if not authenticated
    if user is None and page not in ("login", "register"):
        navigate("login")
        page = "login"

    # Password reset guard: force reset if flagged
    if user and user.get("must_reset_password") and page != "force_reset_password":
        navigate("force_reset_password")
        page = "force_reset_password"

    # Role guard: prevent regular users from admin pages
    if user and user.get("role") not in ("admin", "super_admin") and page.startswith("admin"):
        navigate("home")
        page = "home"

    # Role guard: prevent non-super-admins from super admin page
    if user and user.get("role") != "super_admin" and page == "super_admin":
        navigate("home")
        page = "home"

    # Route to page
    routes = {
        "login": page_login,
        "register": page_register,
        "force_reset_password": page_force_reset_password,
        "home": page_home,
        "analyze": page_analyze,
        "gallery": page_gallery,
        "profile": page_profile,
        "admin_dashboard": page_admin_dashboard,
        "admin_users": page_admin_users,
        "admin_content": page_admin_content,
        "super_admin": page_super_admin,
    }

    handler = routes.get(page, page_login)
    handler()


if __name__ == "__main__":
    main()
else:
    main()
