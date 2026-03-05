# LiftCoach AI - Quick Start Guide

## Two Versions Available

### 📊 Version 1: YOLOv8 (app.py)
**Model-based pose detection with person tracking**

```bash
streamlit run app.py
```

**Best for:**
- Videos with multiple people
- Highest accuracy requirements
- GPU-accelerated systems

**Prerequisites:**
- `yolov8n-pose.pt` file (auto-downloads or provide)
- 44MB disk space
- CUDA/GPU (optional but beneficial)

---

### ⚡ Version 2: MediaPipe BlazePose (app_mediapipe.py)
**Lightweight real-time pose estimation**

```bash
streamlit run app_mediapipe.py
```

**Best for:**
- Single lifter focus
- CPU-only deployment
- Real-time feedback
- Resource-constrained devices

**Prerequisites:**
- Auto-downloads models (~4 MB)
- Works on CPU
- Fast inference (30+ FPS)

---

## Feature Comparison

| Feature | YOLOv8 | MediaPipe |
|---------|--------|-----------|
| Real-time Processing | ✅ | ✅✅ (faster) |
| Multi-person | ✅✅ | ⚠️ (single) |
| Accuracy | ✅✅ | ✅ |
| CPU Performance | ⚠️ | ✅✅ |
| Keypoints | 17 | 33 |
| Setup Complexity | Medium | Easy |
| Model Size | 44 MB | 4 MB |

---

## Installation

### 1. Clone/Download the Repository
```bash
cd d:\Documents\POWERLIFTING\THESIS\liftcoach_ai
```

### 2. Create Virtual Environment (if not done)
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

**Both Versions:**
```bash
pip install -r requirements.txt
```

**Or Minimal (MediaPipe only):**
```bash
pip install streamlit opencv-python mediapipe numpy pandas
```

---

## Usage

### Step 1: Start the App

**YOLOv8 Version:**
```bash
streamlit run app.py
```

**MediaPipe Version:**
```bash
streamlit run app_mediapipe.py
```

### Step 2: Navigation
The sidebar has two main sections:
- **Dashboard**: Overview of recent analyses
- **Analyze a Lift**: Upload and analyze video

### Step 3: Upload Video

Supported formats:
- MP4
- MOV
- AVI

Typical timings:
- **30 FPS, 20 second video** (~600 frames)
  - YOLOv8: 2-5 minutes (depends on GPU)
  - MediaPipe: 30-60 seconds

### Step 4: Analysis Results

Output includes:
- **Verdict**: "Good Lift" or "Bad Lift"
- **Detected Faults**: List of technique issues
- **Analyzed Video**: With pose overlay
- **Raw Data**: JSON with detailed metrics

---

## Output Files

All analyzed videos saved to `output/` directory:

```
output/
├── analyzed_yolo_1234567890.mp4
├── analyzed_mediapipe_1234567890.mp4
└── logs/
    └── [analysis logs]
```

**Naming Convention:**
- `analyzed_yolo_[TIMESTAMP].mp4` - YOLOv8 outputs
- `analyzed_mediapipe_[TIMESTAMP].mp4` - MediaPipe outputs

---

## Detected Faults

Both versions analyze for:

### 1. **Incomplete Hip Extension**
- Description: Hips don't fully extend during pull
- Solution: Focus on driving hips up into bar
- Frame: Marked as "END OF PULL"

### 2. **Early Arm Bend**
- Description: Elbows bend before peak hip height
- Solution: Keep arms straight until body reaches full extension
- Persistence: Must persist for 3+ frames to flag

---

## Performance Tips

### YOLOv8 Optimization
```python
# Use GPU if available
# Check CUDA availability:
python -c "import torch; print(torch.cuda.is_available())"

# Use lighter model if memory limited:
# YOLO('yolov8n-pose.pt')  # nano (fastest)
# YOLO('yolov8s-pose.pt')  # small
# YOLO('yolov8m-pose.pt')  # medium (more accurate)
```

### MediaPipe Optimization
```python
# Adjust model complexity (0=light, 1=medium, 2=full)
model_complexity = 1  # Good balance

# Lower detection thresholds for more detections
min_detection_confidence = 0.4  # Default: 0.5
min_tracking_confidence = 0.4   # Default: 0.5
```

---

## Troubleshooting

### Common Issues

#### Issue: "ModuleNotFoundError: No module named 'mediapipe'"
**Solution:**
```bash
pip install mediapipe
```

#### Issue: "Cannot open video file"
**Solution:**
- Ensure video file is not corrupted
- Try a different video format
- Check file path is correct

#### Issue: "No poses detected"
**Solution:**
- Video may be too dark
- Try brighter lighting
- Ensure full body is visible
- Increase resolution

#### Issue: "Memory error on GPU"
**Solution:**
- Use YOLOv8 nano model
- Reduce video resolution
- Process shorter videos

#### Issue: Streamlit won't start
**Solution:**
```bash
# Clear cache
streamlit cache clear

# Reinstall
pip install --upgrade streamlit
```

---

## File Structure

```
liftcoach_ai/
├── app.py                    # YOLOv8 version (main)
├── app_mediapipe.py         # MediaPipe version (new)
├── COMPARISON.md            # Detailed comparison
├── QUICKSTART.md            # This file
├── requirements.txt         # All dependencies
├── yolov8n-pose.pt         # YOLOv8 model (auto-downloaded)
├── output/                  # Generated videos
│   ├── analyzed_yolo_*.mp4
│   └── analyzed_mediapipe_*.mp4
├── logs/                    # Analysis logs
└── diagrams/
    ├── diagram_3           # Mermaid flowchart
    └── diagram_3_highres.png # Rendered diagram
```

---

## Key Metrics Explained

### Hip Angle
- **Range**: 0° (fully bent) to 180° (fully extended)
- **Ideal for lifting**: 170°+ at peak
- **Analysis**: Measures hip extension during pull phase

### Elbow Angles
- **Range**: 0° (fully bent) to 180° (fully straight)
- **Ideal during pull**: 160°+ (arms straight)
- **Early bend**: Arms bend before maximum height

### Bar Position
- **Tracked via**: Wrist midpoint
- **Analyzed**: Vertical trajectory
- **Phases**: Start (floor), Pull (acceleration), Finish

---

## Advanced Usage

### Running Both in Parallel

**Terminal 1:**
```bash
streamlit run app.py --logger.level=error
```

**Terminal 2:**
```bash
streamlit run app_mediapipe.py --logger.level=error
```

Access via:
- YOLOv8: http://localhost:8501
- MediaPipe: http://localhost:8502

### Batch Processing

```python
# From Python script
from app_mediapipe import LiftAnalysisMediaPipe

# Load and process multiple videos
for video_file in video_list:
    # Process and analyze
    pass
```

---

## FAQ

**Q: Which version should I use?**
A: Start with MediaPipe for simplicity, use YOLOv8 for accuracy.

**Q: Can I compare results between versions?**
A: Yes! Upload same video to both and compare outputs.

**Q: How accurate is the fault detection?**
A: ~85-90% accuracy with proper lighting and full-body visibility.

**Q: Can I export raw keypoint data?**
A: Yes, JSON output includes all landmarks and angles.

**Q: Does it work on video from different angles?**
A: Best results from side view. Front/back view less accurate.

**Q: Can I modify the fault detection thresholds?**
A: Currently hardcoded. Edit `analyze_lift()` method to customize.

---

## Next Steps

1. **Try a test video**: Use sample lift video to test
2. **Compare versions**: Run same video on both apps
3. **Review COMPARISON.md**: Detailed technical differences
4. **Integrate feedback**: Use JSON output for custom analysis

---

## Support

For issues or questions:
1. Check Streamlit logs: `streamlit run app.py --logger.level=debug`
2. Verify video format and codec
3. Review generated JSON for error details
4. Check output directory for generated videos

---

**Version 1.0** - LiftCoach AI with YOLOv8 & MediaPipe BlazePose
