"""
Court Detection & Homography Transformation Module
Maps pixel coordinates in broadcast/camera frames to real-world meters on a standard tennis court.
"""

import cv2
import numpy as np
from config import REAL_COURT_POINTS, COURT_WIDTH_M, COURT_LENGTH_M

class CourtDetector:
    def __init__(self, default_pixel_corners=None):
        """
        :param default_pixel_corners: List of 4 (x,y) pixel points corresponding to court corners:
                                       [top-left, top-right, bottom-right, bottom-left]
        """
        self.H = None
        self.H_inv = None
        self.pixel_corners = default_pixel_corners
        
        # Standard metric target corners corresponding to 4 doubles corners
        self.metric_corners = np.array([
            REAL_COURT_POINTS["top_left_doubles"],
            REAL_COURT_POINTS["top_right_doubles"],
            REAL_COURT_POINTS["bottom_right_doubles"],
            REAL_COURT_POINTS["bottom_left_doubles"]
        ], dtype=np.float32)

        if default_pixel_corners is not None:
            self.set_pixel_corners(default_pixel_corners)

    def set_pixel_corners(self, pixel_corners):
        """Sets pixel corners and computes the robust RANSAC Homography matrix."""
        self.pixel_corners = np.array(pixel_corners, dtype=np.float32)
        # Compute Homography with RANSAC robust estimator: pixel -> real court (meters)
        self.H, _ = cv2.findHomography(self.pixel_corners, self.metric_corners, cv2.RANSAC, 5.0)
        if self.H is not None:
            self.H_inv = np.linalg.inv(self.H)

    def detect_court_lines(self, frame):
        """
        Automatic white court line detection using HSV thresholding and Hough line intersections.
        Refines court corners dynamically if default corners do not align with actual court.
        """
        self._frame_count = getattr(self, "_frame_count", 0) + 1

        # Cache court lines: re-detect only once every 30 frames
        if self.pixel_corners is not None and (self._frame_count % 30 != 0):
            return self.pixel_corners

        if hasattr(self, "_corners_user_set") and self._corners_user_set:
            return self.pixel_corners

        h, w, _ = frame.shape
        
        # 1. Isolate white court lines using HSV thresholding
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # White color range
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # 2. Canny Edge Detection & Hough Lines
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

        # Sort horizontal lines by Y (top baseline vs bottom baseline)
        horizontal_lines.sort(key=lambda l: (l[1] + l[3]) / 2.0)
        
        # If strong court lines found, update corners
        if len(horizontal_lines) >= 2 and len(vertical_lines) >= 2:
            top_line = horizontal_lines[0]
            bottom_line = horizontal_lines[-1]
            
            # Sort vertical lines by X
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
                # Validate reasonable screen bounds
                if (0 < tl[0] < w and 0 < tl[1] < h) and (0 < br[0] < w and 0 < br[1] < h):
                    self.set_pixel_corners([tl, tr, br, bl])
                    return self.pixel_corners

        # Default fallback corners if line detection is ambiguous
        if self.pixel_corners is None:
            default_corners = [
                [w * 0.30, h * 0.38],  # top-left
                [w * 0.70, h * 0.38],  # top-right
                [w * 0.92, h * 0.92],  # bottom-right
                [w * 0.08, h * 0.92]   # bottom-left
            ]
            self.set_pixel_corners(default_corners)
            
        return self.pixel_corners

    def pixel_to_court(self, pixel_point):
        """
        Converts pixel coordinates (x, y) into real court metric coordinates (X, Y).
        """
        if self.H is None:
            return (0.0, 0.0)
            
        pt = np.array([pixel_point[0], pixel_point[1], 1.0], dtype=np.float32).reshape(3, 1)
        res = np.dot(self.H, pt)
        res /= res[2]
        return float(res[0]), float(res[1])

    def court_to_pixel(self, court_point):
        """
        Converts real court metric coordinates (X, Y) back into pixel coordinates (x, y).
        """
        if self.H_inv is None:
            return (0, 0)
            
        pt = np.array([court_point[0], court_point[1], 1.0], dtype=np.float32).reshape(3, 1)
        res = np.dot(self.H_inv, pt)
        res /= res[2]
        return int(res[0]), int(res[1])

    def draw_minimap(self, frame, player_positions=[], ball_position=None, minimap_w=200, minimap_h=350):
        """
        Draws a top-down 2D court minimap with live player and ball markers overlay on the frame.
        """
        # Create court canvas
        minimap = np.full((minimap_h, minimap_w, 3), (34, 139, 34), dtype=np.uint8) # Green court
        
        # Scale factors: Real court (10.97m x 23.77m) -> Minimap (w, h)
        pad = 20
        cw = minimap_w - 2 * pad
        ch = minimap_h - 2 * pad

        def to_map(mx, my):
            px = int(pad + (mx / COURT_WIDTH_M) * cw)
            py = int(pad + (my / COURT_LENGTH_M) * ch)
            return px, py

        # Draw lines
        tl = to_map(*REAL_COURT_POINTS["top_left_doubles"])
        tr = to_map(*REAL_COURT_POINTS["top_right_doubles"])
        br = to_map(*REAL_COURT_POINTS["bottom_right_doubles"])
        bl = to_map(*REAL_COURT_POINTS["bottom_left_doubles"])

        # Outer boundary
        cv2.rectangle(minimap, tl, br, (255, 255, 255), 2)

        # Net line
        nl = to_map(*REAL_COURT_POINTS["net_left"])
        nr = to_map(*REAL_COURT_POINTS["net_right"])
        cv2.line(minimap, nl, nr, (255, 255, 255), 2)

        # Singles lines
        stl = to_map(*REAL_COURT_POINTS["top_left_singles"])
        sbl = to_map(*REAL_COURT_POINTS["bottom_left_singles"])
        str_pt = to_map(*REAL_COURT_POINTS["top_right_singles"])
        sbr = to_map(*REAL_COURT_POINTS["bottom_right_singles"])
        cv2.line(minimap, stl, sbl, (255, 255, 255), 1)
        cv2.line(minimap, str_pt, sbr, (255, 255, 255), 1)

        # Service lines
        tsc = to_map(*REAL_COURT_POINTS["top_service_center"])
        bsc = to_map(*REAL_COURT_POINTS["bottom_service_center"])
        # Top service line across singles court
        cv2.line(minimap, (stl[0], tsc[1]), (str_pt[0], tsc[1]), (255, 255, 255), 1)
        # Bottom service line across singles court
        cv2.line(minimap, (sbl[0], bsc[1]), (sbr[0], bsc[1]), (255, 255, 255), 1)
        # Center service line
        cv2.line(minimap, tsc, bsc, (255, 255, 255), 1)

        # Draw players on minimap
        colors = [(0, 0, 255), (255, 0, 0)] # Red for P1, Blue for P2
        for i, (mx, my) in enumerate(player_positions):
            px, py = to_map(mx, my)
            c = colors[i % len(colors)]
            cv2.circle(minimap, (px, py), 6, c, -1)
            cv2.putText(minimap, f"P{i+1}", (px - 6, py - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Draw ball on minimap
        if ball_position is not None:
            bx, by = to_map(ball_position[0], ball_position[1])
            cv2.circle(minimap, (bx, by), 4, (0, 255, 255), -1)

        # Overlay minimap onto top-right of main frame
        fh, fw, _ = frame.shape
        ox, oy = fw - minimap_w - 20, 20
        frame[oy:oy+minimap_h, ox:ox+minimap_w] = minimap
        cv2.rectangle(frame, (ox, oy), (ox+minimap_w, oy+minimap_h), (255, 255, 255), 1)
        return frame
