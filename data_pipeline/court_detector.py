"""
Court Detection & Homography Transformation Module
Maps pixel coordinates in broadcast/camera frames to real-world meters on a standard tennis court.
"""

import cv2
import numpy as np
from .config import REAL_COURT_POINTS, COURT_WIDTH_M, COURT_LENGTH_M

class CourtDetector:
    def __init__(self, default_pixel_corners=None):
        self.H = None
        self.H_inv = None
        self.pixel_corners = default_pixel_corners
        
        self.metric_corners = np.array([
            REAL_COURT_POINTS["top_left_doubles"],
            REAL_COURT_POINTS["top_right_doubles"],
            REAL_COURT_POINTS["bottom_right_doubles"],
            REAL_COURT_POINTS["bottom_left_doubles"]
        ], dtype=np.float32)

        if default_pixel_corners is not None:
            self.set_pixel_corners(default_pixel_corners)

    def set_pixel_corners(self, pixel_corners):
        self.pixel_corners = np.array(pixel_corners, dtype=np.float32)
        self.H, _ = cv2.findHomography(self.pixel_corners, self.metric_corners, cv2.RANSAC, 5.0)
        if self.H is not None:
            self.H_inv = np.linalg.inv(self.H)

    def detect_court_lines(self, frame):
        self._frame_count = getattr(self, "_frame_count", 0) + 1

        if self.pixel_corners is not None and (self._frame_count % 30 != 0):
            return self.pixel_corners

        if hasattr(self, "_corners_user_set") and self._corners_user_set:
            return self.pixel_corners

        h, w, _ = frame.shape
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        edges = cv2.Canny(mask, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80, minLineLength=int(w*0.15), maxLineGap=20)

        horizontal_lines = []
        vertical_lines = []

        if lines is not None:
            for line in lines:
                l = line[0] if (isinstance(line, np.ndarray) and line.ndim > 0 and len(line) == 1) else line
                if len(l) == 4:
                    x1, y1, x2, y2 = int(l[0]), int(l[1]), int(l[2]), int(l[3])
                    angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
                    if angle < 25 or angle > 155:
                        horizontal_lines.append((x1, y1, x2, y2))
                    elif 35 < angle < 145:
                        vertical_lines.append((x1, y1, x2, y2))

        horizontal_lines.sort(key=lambda l: (l[1] + l[3]) / 2.0)
        
        if len(horizontal_lines) >= 2 and len(vertical_lines) >= 2:
            top_line = horizontal_lines[0]
            bottom_line = horizontal_lines[-1]
            vertical_lines.sort(key=lambda l: (l[0] + l[2]) / 2.0)
            left_line = vertical_lines[0]
            right_line = vertical_lines[-1]

            def line_intersection(line1, line2):
                x1, y1, x2, y2 = line1
                x3, y3, x4, y4 = line2
                denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
                if abs(denom) < 1e-5:
                    return None
                px = ((x1*y2 - y1*x2)*(x3 - x4) - (x1 - x2)*(x3*y4 - y3*x4)) / denom
                py = ((x1*y2 - y1*x2)*(y3 - y4) - (y1 - y2)*(x3*y4 - y3*x4)) / denom
                return [float(px), float(py)]

            tl = line_intersection(top_line, left_line)
            tr = line_intersection(top_line, right_line)
            br = line_intersection(bottom_line, right_line)
            bl = line_intersection(bottom_line, left_line)

            if all(pt is not None for pt in [tl, tr, br, bl]):
                if (0 < tl[0] < w and 0 < tl[1] < h) and (0 < br[0] < w and 0 < br[1] < h):
                    self.set_pixel_corners([tl, tr, br, bl])
                    return self.pixel_corners

        if self.pixel_corners is None:
            default_corners = [
                [w * 0.30, h * 0.38],
                [w * 0.70, h * 0.38],
                [w * 0.92, h * 0.92],
                [w * 0.08, h * 0.92]
            ]
            self.set_pixel_corners(default_corners)
            
        return self.pixel_corners

    def pixel_to_court(self, pixel_point):
        if self.H is None:
            return (0.0, 0.0)
            
        pt = np.array([pixel_point[0], pixel_point[1], 1.0], dtype=np.float32).reshape(3, 1)
        res = np.dot(self.H, pt)
        res /= res[2]
        return float(res[0]), float(res[1])

    def court_to_pixel(self, court_point):
        if self.H_inv is None:
            return (0, 0)
            
        pt = np.array([court_point[0], court_point[1], 1.0], dtype=np.float32).reshape(3, 1)
        res = np.dot(self.H_inv, pt)
        res /= res[2]
        return int(res[0]), int(res[1])
