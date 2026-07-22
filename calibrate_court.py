"""
Interactive Court Calibration Tool
Displays the first frame of your video and lets you click 4 court corners:
1. Top-Left doubles corner
2. Top-Right doubles corner
3. Bottom-Right doubles corner
4. Bottom-Left doubles corner
"""

import cv2
import argparse
import sys

def calibrate(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[Error] Could not open video: {video_path}")
        return

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("[Error] Could not read frame from video.")
        return

    points = []
    labels = ["1. Top-Left Corner", "2. Top-Right Corner", "3. Bottom-Right Corner", "4. Bottom-Left Corner"]
    clone = frame.copy()

    def click_event(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) < 4:
                points.append((x, y))
                cv2.circle(clone, (x, y), 6, (0, 255, 255), -1)
                cv2.putText(clone, f"P{len(points)}", (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                if len(points) < 4:
                    cv2.putText(clone, f"Click: {labels[len(points)]}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("Court Calibration - Click 4 Corners", clone)

    cv2.namedWindow("Court Calibration - Click 4 Corners")
    cv2.setMouseCallback("Court Calibration - Click 4 Corners", click_event)
    
    cv2.putText(clone, f"Click: {labels[0]}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imshow("Court Calibration - Click 4 Corners", clone)

    print("\n--- Court Calibration ---")
    print("Click 4 corners in order:")
    print(" 1. Top-Left Corner (Far Baseline Left)")
    print(" 2. Top-Right Corner (Far Baseline Right)")
    print(" 3. Bottom-Right Corner (Near Baseline Right)")
    print(" 4. Bottom-Left Corner (Near Baseline Left)")
    print("Press 'r' to reset, 'q' to quit.")

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            points = []
            clone = frame.copy()
            cv2.putText(clone, f"Click: {labels[0]}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Court Calibration - Click 4 Corners", clone)
        elif key == ord('q') or len(points) == 4:
            break

    cv2.destroyAllWindows()

    if len(points) == 4:
        corner_str = ",".join([f"{pt[0]},{pt[1]}" for pt in points])
        print("\n✅ CALIBRATION COMPLETE!")
        print(f"Points selected: {points}")
        print("\nRun main.py with your calibrated corners:")
        print(f"python3 main.py --video {video_path} --output output/analyzed.mp4 --court-corners \"{corner_str}\" --frame-stride 2\n")
        return corner_str
    else:
        print("\nCalibration cancelled or incomplete.")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive Tennis Court Calibration Tool")
    parser.add_argument("--video", type=str, required=True, help="Path to input tennis video")
    args = parser.parse_args()

    calibrate(args.video)
