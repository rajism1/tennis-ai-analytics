"""
Main Entry Point for Tennis AI Computer Vision & Analytics Pipeline
Orchestrates video ingestion, detection, tracking, homography mapping, event classification, and rendering.
"""

import cv2
import argparse
import time
import os
import json

from court_detector import CourtDetector
from player_tracker import PlayerTracker
from pose_estimator import PoseEstimator
from ball_tracker import BallTracker
from stroke_classifier import StrokeClassifier
from event_detector import EventDetector
from analytics_engine import AnalyticsEngine
from config import OUTPUT_DIR

def run_tennis_pipeline(video_source, output_video_path=None, max_frames=None, display=False, frame_stride=1, court_corners=None):
    """
    Runs end-to-end tennis analytics on video source.
    """
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"[Error] Could not open video source: {video_source}")
        return

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    raw_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    fps    = raw_fps / float(frame_stride)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[Pipeline] Video Loaded: {width}x{height} @ {raw_fps:.1f} FPS (Processing Stride: {frame_stride}x, Effective FPS: {fps:.1f})")

    # Output Video Writer
    writer = None
    if output_video_path is not None:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    # Initialize Modules
    court_detector    = CourtDetector()
    if court_corners:
        try:
            pts = [float(v) for v in court_corners.split(",")]
            if len(pts) == 8:
                parsed_corners = [
                    [pts[0], pts[1]], [pts[2], pts[3]],
                    [pts[4], pts[5]], [pts[6], pts[7]]
                ]
                court_detector.set_pixel_corners(parsed_corners)
                court_detector._corners_user_set = True
                print(f"[CourtDetector] Loaded custom calibrated court corners: {parsed_corners}")
        except Exception as e:
            print(f"[CourtDetector] Warning: Could not parse --court-corners ({e})")

    player_tracker    = PlayerTracker()
    pose_estimator    = PoseEstimator()
    ball_tracker      = BallTracker(fps=fps)
    stroke_classifier = StrokeClassifier()
    event_detector    = EventDetector(fps=fps)
    analytics_engine  = AnalyticsEngine()

    frame_idx = 0
    raw_frame_idx = 0
    start_time = time.time()

    print("[Pipeline] Processing video frames with Apple Silicon / Hardware Acceleration...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        raw_frame_idx += 1
        if frame_stride > 1 and (raw_frame_idx % frame_stride != 0):
            continue

        frame_idx += 1
        if max_frames and frame_idx > max_frames:
            break

        # 1. Court Detection & Homography
        court_detector.detect_court_lines(frame)

        # 2. Player Detection & Initial Bounding Boxes
        players = player_tracker.detect_and_track(frame, court_detector)

        # 3. Pose Estimation (COCO 17 Keypoints)
        poses = pose_estimator.estimate_pose(frame, players)

        # Refine player court coordinates using Pose Ankle Keypoints
        players = player_tracker.detect_and_track(frame, court_detector, poses)

        # 4. Ball Tracking & Physics (Speed, Height, Bounce)
        ball_info = ball_tracker.track_ball(frame, frame_idx, court_detector, poses)

        # 5. Event Detection & Stroke Classification
        event = event_detector.process_frame(frame_idx, players, ball_info, poses, stroke_classifier)
        if event is not None:
            analytics_engine.log_event(event)

        # 6. Visual Overlay Rendering
        frame = player_tracker.draw_players(frame, players)
        frame = pose_estimator.draw_poses(frame, poses)
        frame = ball_tracker.draw_ball(frame, ball_info)
        
        # Minimap Overlay
        player_court_positions = [p["court_pos_m"] for p in players]
        frame = court_detector.draw_minimap(
            frame, 
            player_positions=player_court_positions, 
            ball_position=ball_info["ball_court_m"]
        )

        # HUD Stats Banner
        cv2.rectangle(frame, (10, 10), (350, 70), (0, 0, 0), -1)
        cv2.putText(frame, f"Frame: {frame_idx} | Rally: {event_detector.rally_count}", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        cv2.putText(frame, f"Ball Speed: {ball_info['speed_kmh']} km/h", (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

        if writer is not None:
            writer.write(frame)

        if display:
            cv2.imshow("Tennis AI Analytics Pipeline", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    if writer:
        writer.release()
    if display:
        cv2.destroyAllWindows()

    elapsed = time.time() - start_time
    print(f"\n[Pipeline Complete] Processed {frame_idx} frames in {elapsed:.2f} seconds ({frame_idx/elapsed:.1f} FPS)")

    # Export Analytics
    json_path = analytics_engine.export_json()
    csv_path = analytics_engine.export_csv()
    summary = analytics_engine.get_match_summary()
    print("\n--- Match Analytics Summary ---")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tennis AI Computer Vision & Analytics Pipeline")
    parser.add_argument("--video", type=str, default="sample_tennis.mp4", help="Path to input tennis video")
    parser.add_argument("--output", type=str, default=os.path.join(OUTPUT_DIR, "output_analytics.mp4"), help="Path to output annotated video")
    parser.add_argument("--max-frames", type=int, default=None, help="Max frames to process")
    parser.add_argument("--frame-stride", type=int, default=1, help="Process every Nth frame (e.g. 2 for 2x speedup)")
    parser.add_argument("--court-corners", type=str, default=None, help="Comma-separated 4 court corner pixel coords: x1,y1,x2,y2,x3,y3,x4,y4")
    parser.add_argument("--display", action="store_true", help="Display output window")
    args = parser.parse_args()

    run_tennis_pipeline(args.video, args.output, args.max_frames, args.display, args.frame_stride, args.court_corners)
