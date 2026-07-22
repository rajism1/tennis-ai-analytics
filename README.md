# 🎾 Tennis AI Computer Vision & Analytics Pipeline

An end-to-end Computer Vision and Analytics system for video-based tennis match analysis. Built with **PyTorch**, **OpenCV**, **Ultralytics YOLO11**, and **Homography Court Mapping**.

---

## 🌟 Key Features

- 📐 **Court Detection & Homography Transformation**: Computes a 3x3 Homography matrix ($H$) mapping 2D camera pixels $(x,y)$ to real ITF court coordinates in meters $(X,Y)$ (23.77m $\times$ 10.97m). Includes a live top-down 2D court minimap overlay.
- 🏃 **Player Detection & Tracking**: Powered by **YOLO11** for persistent tracking of **Player 1** (far court) and **Player 2** (near court).
- 🦴 **17-Keypoint Pose Estimation**: Body keypoint extraction (Shoulders, Hips, Knees, Ankles, Wrists, Elbows) computing biomechanical joint angles (elbow flexion, knee bend, shoulder tilt).
- 🎾 **Ball Dynamics & Trajectory**: TrackNet/physics blob tracking engine computing ball speed (km/h), height trajectory ($z$-estimate), and 3D court bounce points.
- 🏸 **Stroke Classification**: Automatically classifies strokes into *Serve, Forehand, Backhand, Volley, Slice, Drop, Smash, Lob* and estimates ball spin (*Topspin, Flat, Backspin*).
- ⏱️ **Match Event & Timeline Detection**: State machine detecting discrete events: *Serve, Hit, Bounce, Winner, Net, Fault, Double Fault, Ace, Rally End*.
- 📊 **Analytics Storage Engine**: Logs telemetry matching standard analytics schema directly to **JSON**, **CSV**, and **SQLite Database** (`tennis_analytics.db`).
- ⚡ **Hardware Acceleration**: Built-in support for **Apple Silicon Metal GPU (`mps`)** and NVIDIA CUDA for real-time inference.

---

## 🏗️ System Architecture

```
[Video Stream] ──> [Court Detector & Homography] ──> [Real Court (X, Y) Meters]
       │
       ├──> [YOLO11 Player Tracker] ──> [Player 1 & Player 2 Coordinates]
       │
       ├──> [YOLO11 Pose Estimator] ──> [17 COCO Keypoints & Joint Angles]
       │
       └──> [Ball Tracker & Physics] ──> [Speed (km/h), Height, Bounce Points]
                                                      │
                                                      ▼
                                           [Stroke & Event Classifier]
                                                      │
                                                      ▼
                                           [Analytics Engine: JSON/CSV/SQLite]
```

---

## 🚀 Quick Start

### 1. Prerequisites & Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/YOUR_USERNAME/tennis-ai-analytics.git
cd tennis-ai-analytics
pip install -r requirements.txt
```

### 2. Run Pipeline on Local Video

To analyze your tennis match video:

```bash
python main.py --video /path/to/match.mp4 --output output/match_analyzed.mp4
```

### 3. Apple Silicon Mac (M1 / M2 / M3 / M4) Speed Optimization

To enable **Metal GPU hardware acceleration** and 2x frame stride optimization (processes a 2-minute video in ~1.5 minutes):

```bash
python main.py --video /path/to/match.mp4 --output output/match_analyzed.mp4 --frame-stride 2
```

---

## 📊 Output Data Schema

Events logged to `tennis_match_analytics.json`, `tennis_match_analytics.csv`, and `tennis_analytics.db`:

```json
{
  "event_id": "evt_45",
  "timestamp_sec": 1.5,
  "frame_idx": 45,
  "player": "Player 1",
  "event_type": "Serve",
  "stroke": "Serve",
  "speed_kmh": 142.8,
  "ball_height_m": 2.15,
  "spin": "Topspin",
  "court_position_meters": [5.48, 0.5],
  "landing_court_position_meters": [7.8, 6.4],
  "body_pose_angles": {
    "right_elbow_angle": 154.2,
    "right_knee_angle": 132.8,
    "shoulder_tilt_deg": -18.5
  },
  "reaction_time_ms": 410,
  "result": "In Play"
}
```

---

## 📁 Repository Structure

```
.
├── config.py             # ITF court dimensions, thresholds & COCO keypoint maps
├── court_detector.py     # Homography transformation & 2D court minimap renderer
├── player_tracker.py      # YOLO11 player detection & tracking module
├── pose_estimator.py     # 17-keypoint pose extraction & biomechanics angles
├── ball_tracker.py       # Ball tracking, speed (km/h) & bounce detection
├── stroke_classifier.py  # Stroke & spin classification engine
├── event_detector.py     # Match state machine & event timeline
├── analytics_engine.py   # Telemetry logger (JSON, CSV, SQLite DB)
├── main.py               # Main pipeline execution entry point
├── test_pipeline.py      # Synthetic test video generator & automated tests
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

---

## 🧪 Testing

Run the automated integration test suite (generates synthetic match footage and verifies all data schemas):

```bash
python test_pipeline.py
```

---

## 📜 License

MIT License. Free for research, personal, and commercial development.
