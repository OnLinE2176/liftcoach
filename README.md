# 🏋️ LiftCoach AI

LiftCoach AI is a web application designed to analyze powerlifting form using computer vision. Built with Streamlit and MediaPipe's BlazePose model, it provides fast, lightweight, and highly accurate pose estimation to help athletes improve their technique.

---

## 🎯 Key Features

### Analysis Capabilities
- 🎬 Upload MP4, MOV, or AVI videos
- 🧑 Detect and track athlete pose using MediaPipe BlazePose (33 full-body landmarks)
- 📊 Analyze lift technique (Squat, Bench Press, Deadlift)
- 🔍 Identify faults (e.g., Incomplete Hip Extension, Early Arm Bend)
- 📈 Generate analyzed video with pose overlay and automated feedback
- 📥 Download results and raw kinematic data (JSON)

### Dashboard
- 📊 Overview of recent analyses
- 📋 Verdict tracking (Good/Bad Lift)
- 📉 Fault distribution and historical statistics

---

## ⚡ Why MediaPipe BlazePose?

LiftCoach AI uses MediaPipe BlazePose as its analysis engine because of its incredible efficiency and performance:
- **Lightning Fast**: Real-time performance on CPU (30+ FPS)
- **High Detail**: 33 full-body landmarks including fingers and foot positions
- **Lightweight**: Model size is ~4 MB and auto-downloads on first run
- **Smooth Tracking**: Built-in temporal smoothing for less jitter
- **Accessible**: Runs perfectly on edge devices without needing a GPU!

---

## 🔧 Installation & Setup

### Prerequisites
- Python 3.11+
- Virtual environment (recommended)

### Step 1: Install Dependencies
```bash
# Install all required packages
pip install -r requirements.txt
```

### Step 2: Environment Variables
Copy `.env.example` to `.env` and fill in your Supabase and Cloudflare R2 credentials.

### Step 3: Run Application
```bash
# Start the web app
streamlit run app_mediapipe.py
```
The application will open in your default web browser (usually at `http://localhost:8501`). The MediaPipe models will automatically download on the first run.

---

## 📈 Analysis Flow

```
1. VIDEO UPLOAD
   └─→ Temporary file created
                ↓
2. FRAME PROCESSING
   └─→ MediaPipe Pose estimation
                ↓
3. LANDMARK EXTRACTION
   └─→ 33 full-body landmarks identified
                ↓
4. LIFT ANALYSIS
   ├─ Calculate angles (hip, knee, elbow)
   ├─ Track bar position
   ├─ Identify lift phases
   └─ Detect faults
                ↓
5. VIDEO GENERATION
   ├─ Overlay pose skeleton
   ├─ Add verdict banner
   ├─ Mark lift phases
   └─ Encode to output video
                ↓
6. RESULTS OUTPUT
   ├─ Video preview (Streamlit)
   ├─ Verdict badge
   ├─ Fault list
   └─ JSON data export & Download button
```

---

## 🎬 Output Examples

### Analyzed Video Contains:
- ✅ **Pose skeleton** overlaid on the original video
- ✅ **Verdict badge** at the top-left (Good/Bad - green/red)
- ✅ **Phase markers** (e.g., "LIFT START", "END OF PULL")
- ✅ **Smooth tracking** powered by MediaPipe

### JSON Output Includes:
```json
{
  "verdict": "Good Lift",
  "faults_found": [],
  "phases": {
    "start_frame": 12,
    "end_of_pull_frame": 45
  },
  "kinematic_data": {
    "peak_hip_angle": 178.5
  }
}
```

---

## 🚀 Deployment Options

LiftCoach AI is designed to be easily deployable:

### Local Desktop
```bash
streamlit run app_mediapipe.py
```

### Cloud Deployment
A `Dockerfile` is provided for containerized deployment (e.g., on Railway, Render, GCP, AWS).
```bash
docker build -t liftcoach-ai .
docker run -p 8501:8501 liftcoach-ai
```

---

## 📝 Notes

**Technical Highlights:**
- Uses a robust object-oriented analysis pipeline for technique assessment
- Hip angle calculation for extension analysis
- Elbow angle tracking for early arm bend detection
- Bar position estimation from wrist landmarks
- Integrated with Supabase for robust user authentication and real-time database management
- Utilizes Cloudflare R2 for reliable and scalable video storage

---

**Last Updated:** March 2026
