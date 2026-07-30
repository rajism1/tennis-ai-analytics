"""
CLI Entry Point for Module 1: Video Processing & Data Generation Pipeline
"""

import argparse
import os
from .processor import run_tennis_pipeline
from .config import OUTPUT_DIR, VIDEO_PATH

def main():
    parser = argparse.ArgumentParser(description="Module 1: Video Processing & Telemetry Generation Pipeline")
    parser.add_argument("--video", type=str, default=VIDEO_PATH, help="Path to input tennis match video")
    parser.add_argument("--output", type=str, default=os.path.join(OUTPUT_DIR, "tennis_match_analytics.json"), help="Path to export extracted JSON telemetry")
    parser.add_argument("--output-video", type=str, default=None, help="Path to export optional annotated MP4 video")
    parser.add_argument("--max-frames", type=int, default=None, help="Max video frames to process")
    parser.add_argument("--frame-stride", type=int, default=1, help="Process every Nth frame")
    parser.add_argument("--court-corners", type=str, default=None, help="Comma-separated 4 court corner pixel coords")
    parser.add_argument("--display", action="store_true", help="Display live rendering window")
    args = parser.parse_args()

    run_tennis_pipeline(
        video_source=args.video,
        json_output_path=args.output,
        output_video_path=args.output_video,
        max_frames=args.max_frames,
        display=args.display,
        frame_stride=args.frame_stride,
        court_corners=args.court_corners
    )

if __name__ == "__main__":
    main()
