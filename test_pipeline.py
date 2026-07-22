"""
Synthetic Video Generator & End-to-End Test Suite for Tennis Analytics Pipeline
Generates a 60-frame synthetic tennis video clip, runs the pipeline, and validates all output schemas.
"""

import cv2
import numpy as np
import os
import json
import sqlite3
from main import run_tennis_pipeline
from config import OUTPUT_DIR

def create_synthetic_tennis_video(filename="synthetic_tennis.mp4", num_frames=60, fps=30):
    """Generates a synthetic tennis video with court lines, moving players, and a bouncing ball."""
    w, h = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (w, h))

    print(f"[Test Setup] Generating synthetic video: {filename} ({num_frames} frames)...")

    for i in range(num_frames):
        # Green court background
        frame = np.full((h, w, 3), (40, 120, 40), dtype=np.uint8)

        # Draw white court boundaries (Doubles & Baseline)
        tl, tr = (int(w * 0.25), int(h * 0.3)), (int(w * 0.75), int(h * 0.3))
        bl, br = (int(w * 0.10), int(h * 0.9)), (int(w * 0.90), int(h * 0.9))
        cv2.line(frame, tl, tr, (255, 255, 255), 3)
        cv2.line(frame, tr, br, (255, 255, 255), 3)
        cv2.line(frame, br, bl, (255, 255, 255), 3)
        cv2.line(frame, bl, tl, (255, 255, 255), 3)
        
        # Net line across middle
        net_l, net_r = (int(w * 0.175), int(h * 0.6)), (int(w * 0.825), int(h * 0.6))
        cv2.line(frame, net_l, net_r, (255, 255, 255), 4)

        # Moving Player 1 (Far Court)
        p1_x = int(w * (0.45 + 0.1 * np.sin(i / 10.0)))
        p1_y = int(h * 0.35)
        cv2.rectangle(frame, (p1_x - 20, p1_y - 50), (p1_x + 20, p1_y), (200, 50, 50), -1)

        # Moving Player 2 (Near Court)
        p2_x = int(w * (0.50 + 0.15 * np.cos(i / 8.0)))
        p2_y = int(h * 0.80)
        cv2.rectangle(frame, (p2_x - 25, p2_y - 80), (p2_x + 25, p2_y), (50, 50, 200), -1)

        # Parabolic Ball Trajectory with Bounce
        t = i / float(num_frames)
        ball_x = int(w * (0.45 + 0.1 * t))
        # Parabolic arc
        ball_y = int(h * (0.35 + 0.5 * t - 0.2 * np.sin(np.pi * t * 2)))
        
        # Tennis yellow ball HSV/BGR (BGR: 0, 240, 240)
        cv2.circle(frame, (ball_x, ball_y), 8, (0, 240, 240), -1)

        out.write(frame)

    out.release()
    print("[Test Setup] Synthetic video generated successfully.")
    return filename

def test_pipeline_execution():
    """Runs the end-to-end test and asserts all output files exist and contain valid data."""
    test_video = "synthetic_tennis.mp4"
    output_video = os.path.join(OUTPUT_DIR, "test_output.mp4")
    json_output = os.path.join(OUTPUT_DIR, "tennis_match_analytics.json")
    csv_output = os.path.join(OUTPUT_DIR, "tennis_match_analytics.csv")
    db_output = os.path.join(OUTPUT_DIR, "tennis_analytics.db")

    # Generate synthetic video
    create_synthetic_tennis_video(test_video, num_frames=45)

    # Execute main pipeline
    print("\n[Test Execution] Running Tennis Analytics Pipeline...")
    run_tennis_pipeline(test_video, output_video, max_frames=45, display=False)

    # Verification Assertions
    print("\n--- Running Verification Checks ---")
    assert os.path.exists(output_video), f"Output video missing: {output_video}"
    print(f"✔ Output video created: {output_video} ({os.path.getsize(output_video)} bytes)")

    assert os.path.exists(json_output), f"JSON analytics missing: {json_output}"
    with open(json_output) as f:
        events = json.load(f)
    print(f"✔ JSON analytics created: {json_output} ({len(events)} events logged)")

    assert os.path.exists(csv_output), f"CSV analytics missing: {csv_output}"
    print(f"✔ CSV analytics created: {csv_output}")

    assert os.path.exists(db_output), f"SQLite DB missing: {db_output}"
    conn = sqlite3.connect(db_output)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM analytics_events")
    count = cursor.fetchone()[0]
    conn.close()
    print(f"✔ SQLite Database verified: {db_output} ({count} rows in table)")

    print("\n✅ ALL PIPELINE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pipeline_execution()
