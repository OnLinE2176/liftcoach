# LiftCoach AI - YOLOv8 vs MediaPipe BlazePose Comparison

## Overview

This project now includes two versions of the LiftCoach AI application:

1. **app.py** - YOLOv8 Pose Detection (Original)
2. **app_mediapipe.py** - MediaPipe BlazePose Detection (New)

Both applications analyze weightlifting technique (Snatch and Clean & Jerk) but use different pose estimation models under the hood.

---

## Comparison Table

| Aspect | YOLOv8 | MediaPipe BlazePose |
|--------|--------|-------------------|
| **Model Type** | Real-time object detection + pose | Lightweight pose estimation |
| **Keypoints** | 17 (COCO format) | 33 (Full body landmarks) |
| **Detection Confidence** | Generally higher precision | Faster, lower latency |
| **Model Size** | ~44 MB (yolov8n-pose.pt) | ~4 MB on-device |
| **Inference Speed** | Moderate (GPU optimal) | Very fast (CPU sufficient) |
| **Person Tracking** | Manual (IoU-based tracking) | Built-in smoothing |
| **GPU Requirement** | Optional (benefits greatly) | Not required |
| **Setup** | Requires pre-trained .pt file | Auto-downloads models |
| **Best For** | Frames with multiple people | Single person focus |
| **Accuracy** | Higher multi-person accuracy | Excellent single-person |

---

## Keypoint Mapping Differences

### YOLOv8 (17 Keypoints - COCO Format)

```
0: nose
1: left_eye
2: right_eye
3: left_ear
4: right_ear
5: left_shoulder
6: right_shoulder
7: left_elbow
8: right_elbow
9: left_wrist
10: right_wrist
11: left_hip
12: right_hip
13: left_knee
14: right_knee
15: left_ankle
16: right_ankle
```

### MediaPipe Pose (33 Landmarks)

```
0: nose
1-4: left eye region
5-8: right eye region
7: left_ear
8: right_ear
9-10: mouth
11: left_shoulder
12: right_shoulder
13: left_elbow
14: right_elbow
15: left_wrist
16: right_wrist
17-22: left hand (pinky, index, thumb)
23: right hand (pinky, index, thumb)
24: right_hip
25: left_knee
26: right_knee
27: left_ankle
28: right_ankle
29-32: left/right foot (heel, foot_index)
```

---

## Code Differences

### Model Loading

**YOLOv8:**
```python
from ultralytics import YOLO
model = YOLO('yolov8n-pose.pt')
results = model.predict(frame, verbose=False)
```

**MediaPipe:**
```python
import mediapipe as mp
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    smooth_landmarks=True,
    min_detection_confidence=0.5
)
results = pose.process(frame_rgb)
```

### Keypoint Extraction

**YOLOv8:**
```python
# Access from results object
detections = []
for box, kps in zip(results[0].boxes, results[0].keypoints):
    detections.append({
        'box': box.xyxy[0].cpu().numpy(),
        'kps': kps.data[0].cpu().numpy()  # Direct numpy array
    })
```

**MediaPipe:**
```python
# Access from landmarks object
if results.pose_landmarks:
    landmarks = []
    for landmark in results.pose_landmarks.landmark:
        landmarks.append([landmark.x, landmark.y, landmark.visibility])
    landmarks = np.array(landmarks)
```

### Person Tracking

**YOLOv8:**
- Manual tracking using Intersection over Union (IoU)
- Follows the largest detected person frame-to-frame
- Better for scenes with multiple people

**MediaPipe:**
- Automatic temporal smoothing
- Single-person focus but very smooth
- Built-in state management

---

## Installation

### Option 1: Install Both

```bash
pip install ultralytics mediapipe opencv-python torch
```

### Option 2: MediaPipe Only (Smaller footprint)

```bash
pip install mediapipe opencv-python streamlit
```

---

## Running the Applications

### YOLOv8 Version
```bash
streamlit run app.py
```

### MediaPipe Version
```bash
streamlit run app_mediapipe.py
```

---

## Performance Characteristics

### YOLOv8 Advantages
- ✅ Better accuracy with multiple people in frame
- ✅ Stronger bounding box detection
- ✅ Better performance with partial occlusions
- ✅ Established sports analysis ecosystem

### YOLOv8 Disadvantages
- ❌ Requires YOLO model file (44 MB)
- ❌ Slower on CPU
- ❌ Manual person tracking needed
- ❌ GPU beneficial but not required

### MediaPipe Advantages
- ✅ Extremely fast on CPU
- ✅ Auto-downloads models (~4 MB)
- ✅ 33 keypoints (more detail)
- ✅ Built-in smoothing/stabilization
- ✅ Lower latency

### MediaPipe Disadvantages
- ❌ Optimized for single person
- ❌ Less accurate with multiple people
- ❌ History available only within framework

---

## Lift Analysis Logic

Both versions implement the same lift analysis algorithm:

1. **Bar Position Tracking**: Estimates barbell height from wrist positions
2. **Lift Phase Detection**: Identifies start and end of pull
3. **Hip Angle Analysis**: Checks for hip extension completeness
4. **Elbow Bend Analysis**: Detects early arm bending during pull
5. **Fault Detection**: Identifies common technique errors

### Key Metrics

```python
# Both versions track:
- Hip angles (extension analysis)
- Elbow angles (arm bend detection)
- Bar trajectory (vertical path)
- Lift phases (start, peak, finish)
```

---

## Analysis Outputs

### Both Versions Output

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

### Video Output

- Original detected poses overlaid
- Verdict displayed (Good/Bad)
- Phase markers (LIFT START, END OF PULL)
- Full skeleton visualization

---

## Recommendations

### Use YOLOv8 (app.py) when:

- 📺 Video contains multiple people
- 🎯 You need highest accuracy
- 💪 Analyzing group training sessions
- 🖥️ You have GPU available
- 📊 You need established sports benchmarks

### Use MediaPipe (app_mediapipe.py) when:

- 📱 Deploying on resource-constrained devices
- ⚡ Speed is critical (real-time feedback)
- 🏋️ Single lifter focus (typical scenario)
- 💾 Storage/bandwidth limited
- 🔥 Want to run on CPU only
- 🎥 Prefer better temporal smoothness

---

## Future Enhancements

Both versions can be enhanced with:

- [ ] Confidence threshold UI controls
- [ ] Real-time angle visualization
- [ ] Multi-lift pipeline
- [ ] Form comparison (user vs reference)
- [ ] Progressive overload tracking
- [ ] Coach feedback generation
- [ ] Mobile app deployment

---

## Technical Notes

### Frame Rate Handling

Both versions support variable frame rates:

```python
frame_rate = cap.get(cv2.CAP_PROP_FPS)
analyzer = LiftAnalysis(keypoints/landmarks, frame_rate)
```

### Keypoint Confidence

Both use confidence/visibility thresholds:

```python
if landmark[2] > 0.1:  # confidence > 10%
    # Use landmark
```

### Video Encoding

Output videos use H.264 (AVC1) codec for compatibility:

```python
fourcc = cv2.VideoWriter_fourcc(*'avc1')
```

---

## Troubleshooting

### YOLOv8 Issues

| Issue | Solution |
|-------|----------|
| Model not found | Download yolov8n-pose.pt to repo root |
| Out of memory (GPU) | Use yolov8n instead of yolov8m |
| Slow inference | Check CUDA availability |

### MediaPipe Issues

| Issue | Solution |
|-------|----------|
| Models not downloading | Check internet connection |
| Poor detection | Increase model_complexity (0, 1, or 2) |
| Jittery output | model_complexity already enables smoothing |

---

## References

- [YOLOv8 Docs](https://docs.ultralytics.com/)
- [MediaPipe Pose](https://mediapipe.dev/solutions/pose)
- [OpenCV Documentation](https://docs.opencv.org/)

---

## Version History

- **v1.0** (app.py): YOLOv8 implementation
- **v2.0** (app_mediapipe.py): MediaPipe BlazePose implementation
- Both versions available for comparative analysis

---

## License & Attribution

LiftCoach AI - Educational Project
- YOLOv8: Ultralytics
- MediaPipe: Google
- OpenCV: Intel, Willow Garage, etc.
