# 🎾 Tennis AI - Computer Vision & Analytics Pipeline

An end-to-end computer vision and SwingVision-inspired analytics platform for broadcast and camera tennis match recordings.

---

## 🏛️ Decoupled Modular Architecture

The codebase is split into **two completely independent modules**:

```
tennis_analytics_pipeline/
├── data_pipeline/                 # MODULE 1: Video Processing & Telemetry Generation
│   ├── config.py                  # Real-world metric settings & thresholds
│   ├── court_detector.py          # Court line detection & RANSAC homography mapping
│   ├── player_tracker.py         # YOLO11 person detection & EMA tracking
│   ├── ball_tracker.py           # Ball blob detection & speed/height trajectory
│   ├── stroke_classifier.py      # Swing kinematics classification
│   ├── event_detector.py         # Match event timeline extraction
│   ├── processor.py              # Main video pipeline orchestrator
│   └── cli.py                    # Module CLI entry point
│
├── analytics_app/                 # MODULE 2: Telemetry Analytics & Web Application
│   ├── engine.py                 # Telemetry & SwingVision metric engine
│   ├── reporter.py               # Standalone 2D heatmap generator & CLI summaries
│   ├── server.py                 # Multi-threaded HTTP server for dashboard
│   ├── web/                      # HTML, CSS, JS web application
│   └── cli.py                    # Module CLI entry point
│
├── output/                        # Decoupled Data Contract
│   └── tennis_match_analytics.json  # Exported Match Telemetry JSON
│
├── process_video.py               # Root shortcut to run Module 1
└── run_dashboard.py               # Root shortcut to run Module 2
```

---

## 🚀 Quickstart Guide

### 1️⃣ Run Data Processing Pipeline (Module 1)
To process a video file and extract telemetry data into `output/tennis_match_analytics.json`:

```bash
python process_video.py --video match2.mp4 --output output/tennis_match_analytics.json
```

### 2️⃣ Run Standalone Analytics Reporter (Module 2)
To compute SwingVision statistics and export 2D court heatmap graphics without running any video or web server:

```bash
python -m analytics_app.cli --reporter-only
```

### 3️⃣ Launch Web Dashboard (Module 2)
To launch the interactive web dashboard on `http://localhost:8080`:

```bash
python run_dashboard.py --port 8080
```
