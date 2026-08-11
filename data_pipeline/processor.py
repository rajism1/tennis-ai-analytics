"""
Main Entry Point for Data Processing & Video Generation Pipeline
Orchestrates video ingestion, detection, tracking, homography mapping, and JSON telemetry export.
"""

import cv2
import time
import os
import json

from .court_detector import CourtDetector
from .player_tracker import PlayerTracker
from .pose_estimator import PoseEstimator
from .ball_tracker import BallTracker
from .stroke_classifier import StrokeClassifier
from .event_detector import EventDetector
from .config import OUTPUT_DIR

def run_tennis_pipeline(video_source, json_output_path=None, output_video_path=None, max_frames=None, display=False, frame_stride=1, court_corners=None):
    if json_output_path is None:
        json_output_path = os.path.join(OUTPUT_DIR, "tennis_match_analytics.json")

    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"[Error] Could not open video source: {video_source}")
        return None

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    raw_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    fps    = raw_fps / float(frame_stride)

    print(f"[DataPipeline] Processing Video: {video_source} ({width}x{height} @ {raw_fps:.1f} FPS)")

    writer = None
    if output_video_path is not None:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

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
                print(f"[CourtDetector] Loaded custom court corners: {parsed_corners}")
        except Exception as e:
            print(f"[CourtDetector] Warning: Could not parse court corners ({e})")

    player_tracker    = PlayerTracker()
    pose_estimator    = PoseEstimator()
    ball_tracker      = BallTracker(fps=fps)
    stroke_classifier = StrokeClassifier()
    event_detector    = EventDetector(fps=fps)

    events_list = []
    frame_idx = 0
    raw_frame_idx = 0
    start_time = time.time()

    snapshots_dir = os.path.join(OUTPUT_DIR, "snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)

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

        court_detector.detect_court_lines(frame)
        players = player_tracker.detect_and_track(frame, court_detector)
        poses = pose_estimator.estimate_pose(frame, players)

        for p in players:
            p_id = p["player_id"]
            if p_id in poses and "keypoints" in poses[p_id] and "left_ankle" in poses[p_id]["keypoints"]:
                l_ank = poses[p_id]["keypoints"]["left_ankle"]
                r_ank = poses[p_id]["keypoints"]["right_ankle"]
                if l_ank[0] > 0 and r_ank[0] > 0:
                    ank_x = (l_ank[0] + r_ank[0]) / 2.0
                    ank_y = (l_ank[1] + r_ank[1]) / 2.0
                    p["feet_pixel"] = (ank_x, ank_y)
                    if court_detector is not None:
                        p["court_pos_m"] = court_detector.pixel_to_court((ank_x, ank_y))

        ball_info = ball_tracker.track_ball(frame, frame_idx, court_detector, poses)
        event = event_detector.process_frame(frame_idx, players, ball_info, poses, stroke_classifier)
        
        if event is not None:
            snapshot_filename = f"snapshot_frame_{frame_idx:06d}.jpg"
            snapshot_filepath = os.path.join(snapshots_dir, snapshot_filename)
            cv2.imwrite(snapshot_filepath, frame)
            event["snapshot_filename"] = snapshot_filename
            events_list.append(event)

        if writer is not None:
            frame = player_tracker.draw_players(frame, players)
            frame = pose_estimator.draw_poses(frame, poses)
            frame = ball_tracker.draw_ball(frame, ball_info)
            
            player_court_positions = [p["court_pos_m"] for p in players]
            frame = court_detector.draw_minimap(
                frame, 
                player_positions=player_court_positions, 
                ball_position=ball_info["ball_court_m"]
            )

            cv2.rectangle(frame, (10, 10), (350, 70), (0, 0, 0), -1)
            cv2.putText(frame, f"Frame: {frame_idx} | Rally: {event_detector.rally_count}", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
            cv2.putText(frame, f"Ball Speed: {ball_info['speed_kmh']} km/h", (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
            writer.write(frame)

        if display:
            cv2.imshow("Tennis AI Video Processing Pipeline", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    if writer:
        writer.release()
    if display:
        cv2.destroyAllWindows()

    elapsed = time.time() - start_time
    print(f"\n[DataPipeline Complete] Processed {frame_idx} frames in {elapsed:.2f} seconds ({frame_idx/max(elapsed, 0.001):.1f} FPS)")

    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(events_list, f, indent=2)

    print(f"✅ Exported {len(events_list)} extracted event records to: {json_output_path}")
    return json_output_path
