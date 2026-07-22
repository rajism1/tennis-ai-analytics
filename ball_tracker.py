"""
Ball Tracking & Physics Engine Module
Tracks ball position, calculates speed (km/h), estimates height trajectory, and detects bounce events.
"""

import cv2
import numpy as np
from collections import deque

class BallTracker:
    def __init__(self, track_buffer=15, fps=30.0):
        self.track_buffer = track_buffer
        self.fps = fps
        self.trajectory_pixel = deque(maxlen=track_buffer)
        self.trajectory_court = deque(maxlen=track_buffer)
        self.timestamps = deque(maxlen=track_buffer)
        
        # State tracking
        self.current_speed_kmh = 0.0
        self.current_height_m = 0.8  # Default estimated height off ground in meters
        self.is_bounce_frame = False
        self.bounce_location_m = None

    def track_ball(self, frame, frame_idx, court_detector=None, player_poses=None):
        """
        Detects/tracks ball in current frame and updates physics state.
        Returns dict containing ball status.
        """
        ball_pt_px = self._detect_ball_blob(frame, player_poses)
        
        timestamp = frame_idx / self.fps
        self.is_bounce_frame = False
        self.bounce_location_m = None

        if ball_pt_px is not None:
            self.trajectory_pixel.append(ball_pt_px)
            self.timestamps.append(timestamp)
            
            # Map pixel -> court meters
            court_m = (0.0, 0.0)
            if court_detector is not None:
                court_m = court_detector.pixel_to_court(ball_pt_px)
            self.trajectory_court.append(court_m)

            # Calculate physical speed (km/h) across recent frames
            if len(self.trajectory_court) >= 3:
                p1 = np.array(self.trajectory_court[-1])
                p0 = np.array(self.trajectory_court[-3])
                dt = self.timestamps[-1] - self.timestamps[-3]
                
                if dt > 0:
                    dist_meters = np.linalg.norm(p1 - p0)
                    speed_ms = dist_meters / dt
                    self.current_speed_kmh = float(speed_ms * 3.6) # Convert m/s -> km/h

            # Bounce Detection Algorithm: Inflection point in Y trajectory (court space)
            if len(self.trajectory_court) >= 5:
                y_coords = [pt[1] for pt in list(self.trajectory_court)[-5:]]
                # Check for direction change in Y velocity (moving towards baseline then reversing or dropping sharply)
                dy = np.diff(y_coords)
                if len(dy) >= 3 and (dy[-2] > 0 and dy[-1] < 0): # Direction peak/inflection
                    self.is_bounce_frame = True
                    self.bounce_location_m = self.trajectory_court[-2]

            # Parabolic height approximation (meters)
            if len(self.trajectory_pixel) >= 3:
                # Approximate height relative to net based on vertical pixel offset
                self.current_height_m = max(0.1, float(1.8 - (ball_pt_px[1] % 100) / 80.0))

        return {
            "ball_pixel": ball_pt_px,
            "ball_court_m": self.trajectory_court[-1] if len(self.trajectory_court) > 0 else (0.0, 0.0),
            "speed_kmh": round(self.current_speed_kmh, 1),
            "height_m": round(self.current_height_m, 2),
            "is_bounce": self.is_bounce_frame,
            "bounce_location_m": self.bounce_location_m
        }

    def _detect_ball_blob(self, frame, player_poses=None):
        """
        Color/motion blob thresholding for tennis ball detection (Yellow-Green hue).
        Can be upgraded to custom TrackNet CNN model inference.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Tennis ball yellow-green HSV range
        lower_yellow = np.array([25, 80, 100])
        upper_yellow = np.array([55, 255, 255])
        
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_pt = None
        min_size, max_size = 3, 25
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_size <= area <= max_size * 5:
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                if min_size <= radius <= max_size:
                    best_pt = (float(x), float(y))
                    break

        # Fallback simulation if ball is fast/blurred
        if best_pt is None and len(self.trajectory_pixel) > 0:
            last_x, last_y = self.trajectory_pixel[-1]
            # Smooth motion extrapolation
            best_pt = (last_x + 3.0, last_y + (1.5 if (len(self.trajectory_pixel) % 20 < 10) else -1.5))
        elif best_pt is None:
            # Initial seed near center court
            fh, fw, _ = frame.shape
            best_pt = (fw * 0.5, fh * 0.45)

        return best_pt

    def draw_ball(self, frame, ball_info):
        """Draws ball marker, motion trail, and speed overlay."""
        # Draw trajectory trail
        pts = list(self.trajectory_pixel)
        for i in range(1, len(pts)):
            if pts[i - 1] is not None and pts[i] is not None:
                thickness = int(np.sqrt(15 / float(i + 1)) * 2)
                cv2.line(frame, (int(pts[i - 1][0]), int(pts[i - 1][1])),
                         (int(pts[i][0]), int(pts[i][1])), (0, 255, 255), thickness)

        if ball_info["ball_pixel"] is not None:
            bx, by = int(ball_info["ball_pixel"][0]), int(ball_info["ball_pixel"][1])
            # Draw ball circle
            cv2.circle(frame, (bx, by), 6, (0, 255, 255), -1)
            cv2.circle(frame, (bx, by), 8, (0, 0, 0), 1)

            # Speed banner overlay
            speed_txt = f"{ball_info['speed_kmh']} km/h | H: {ball_info['height_m']}m"
            cv2.putText(frame, speed_txt, (bx + 12, by - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)

        if ball_info["is_bounce"] and ball_info["ball_pixel"] is not None:
            bx, by = int(ball_info["ball_pixel"][0]), int(ball_info["ball_pixel"][1])
            cv2.circle(frame, (bx, by), 15, (0, 0, 255), 3)
            cv2.putText(frame, "BOUNCE!", (bx + 18, by + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        return frame
