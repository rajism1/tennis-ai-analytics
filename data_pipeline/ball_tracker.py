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
        
        self.current_speed_kmh = 0.0
        self.current_height_m = 0.8
        self.is_bounce_frame = False
        self.bounce_location_m = None

    def track_ball(self, frame, frame_idx, court_detector=None, player_poses=None):
        ball_pt_px = self._detect_ball_blob(frame, player_poses)
        
        timestamp = frame_idx / self.fps
        self.is_bounce_frame = False
        self.bounce_location_m = None

        if ball_pt_px is not None:
            self.trajectory_pixel.append(ball_pt_px)
            self.timestamps.append(timestamp)
            
            raw_court_m = (0.0, 0.0)
            if court_detector is not None:
                raw_court_m = court_detector.pixel_to_court(ball_pt_px)

            est_z = max(0.0, float(1.8 - (ball_pt_px[1] % 100) / 80.0))
            self.current_height_m = round(est_z, 2)
            
            cx, cy = 5.48, 11.885
            dx, dy = raw_court_m[0] - cx, raw_court_m[1] - cy
            corr_factor = max(0.85, 1.0 - (est_z * 0.04))
            corrected_court_m = (cx + dx * corr_factor, cy + dy * corr_factor)

            self.trajectory_court.append(corrected_court_m)

            smooth_court_m = corrected_court_m
            if len(self.trajectory_court) >= 5:
                recent_pts = list(self.trajectory_court)[-5:]
                avg_x = float(np.mean([p[0] for p in recent_pts]))
                avg_y = float(np.mean([p[1] for p in recent_pts]))
                smooth_court_m = (avg_x, avg_y)

            if len(self.trajectory_court) >= 4 and len(self.timestamps) >= 4:
                p1 = np.array(list(self.trajectory_court)[-1])
                p0 = np.array(list(self.trajectory_court)[-4])
                dt = self.timestamps[-1] - self.timestamps[-4]
                
                if dt > 0:
                    dist_meters = np.linalg.norm(p1 - p0)
                    raw_speed_ms = dist_meters / dt
                    calc_speed_kmh = float(raw_speed_ms * 3.6)
                    calc_speed_kmh = min(235.0, calc_speed_kmh)

                    if hasattr(self, "prev_speed_kmh") and self.prev_speed_kmh > 0:
                        max_jump = 35.0
                        clamped_speed = np.clip(calc_speed_kmh, self.prev_speed_kmh - max_jump, self.prev_speed_kmh + max_jump)
                        self.current_speed_kmh = float(0.4 * clamped_speed + 0.6 * self.prev_speed_kmh)
                    else:
                        self.current_speed_kmh = calc_speed_kmh

                    self.prev_speed_kmh = self.current_speed_kmh

            if len(self.trajectory_court) >= 5:
                y_coords = [pt[1] for pt in list(self.trajectory_court)[-5:]]
                dy = np.diff(y_coords)
                if len(dy) >= 3 and (dy[-2] > 0 and dy[-1] < 0):
                    self.is_bounce_frame = True
                    self.bounce_location_m = self.trajectory_court[-2]

        return {
            "ball_pixel": ball_pt_px,
            "ball_court_m": self.trajectory_court[-1] if len(self.trajectory_court) > 0 else (0.0, 0.0),
            "speed_kmh": round(self.current_speed_kmh, 1),
            "height_m": round(self.current_height_m, 2),
            "is_bounce": self.is_bounce_frame,
            "bounce_location_m": self.bounce_location_m
        }

    def _detect_ball_blob(self, frame, player_poses=None):
        h, w, _ = frame.shape
        scale = 0.5
        small_frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        
        hsv = cv2.cvtColor(small_frame, cv2.COLOR_BGR2HSV)
        lower_yellow = np.array([25, 80, 100])
        upper_yellow = np.array([55, 255, 255])
        
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        sh, sw = small_frame.shape[:2]
        mask[:int(sh * 0.35), :int(sw * 0.28)] = 0
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_pt = None
        min_size, max_size = 2, 15
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_size <= area <= max_size * 5:
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                if min_size <= radius <= max_size:
                    best_pt = (float(x / scale), float(y / scale))
                    break

        return best_pt

    def draw_ball(self, frame, ball_info):
        pts = list(self.trajectory_pixel)
        for i in range(1, len(pts)):
            if pts[i - 1] is not None and pts[i] is not None:
                p1 = np.array(pts[i - 1])
                p2 = np.array(pts[i])
                dist = np.linalg.norm(p2 - p1)
                
                if dist < 70.0:
                    thickness = max(1, int(np.sqrt(15 / float(i + 1)) * 2))
                    cv2.line(frame, (int(pts[i - 1][0]), int(pts[i - 1][1])),
                             (int(pts[i][0]), int(pts[i][1])), (0, 255, 255), thickness)

        if ball_info["ball_pixel"] is not None:
            bx, by = int(ball_info["ball_pixel"][0]), int(ball_info["ball_pixel"][1])
            cv2.circle(frame, (bx, by), 6, (0, 255, 255), -1)
            cv2.circle(frame, (bx, by), 8, (0, 0, 0), 1)

            if ball_info['speed_kmh'] > 0:
                speed_txt = f"{ball_info['speed_kmh']} km/h | H: {ball_info['height_m']}m"
                cv2.putText(frame, speed_txt, (bx + 12, by - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)

        if ball_info["is_bounce"] and ball_info["ball_pixel"] is not None:
            bx, by = int(ball_info["ball_pixel"][0]), int(ball_info["ball_pixel"][1])
            cv2.circle(frame, (bx, by), 15, (0, 0, 255), 3)
            cv2.putText(frame, "BOUNCE!", (bx + 18, by + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        return frame
