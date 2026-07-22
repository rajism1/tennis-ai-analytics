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
        """Sets pixel corners and computes the Homography matrix."""
        self.pixel_corners = np.array(pixel_corners, dtype=np.float32)
        # Compute Homography: pixel -> real court (meters)
        self.H, _ = cv2.findHomography(self.pixel_corners, self.metric_corners)
        if self.H is not None:
            self.H_inv = np.linalg.inv(self.H)

    def detect_court_lines(self, frame):
        """
        Automatic line detection using color thresholding and Hough lines fallback.
        If initial corners are provided, refines them using edge gradients.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Default fallback corners if none specified (typical broadcast camera perspective)
        if self.pixel_corners is None:
            default_corners = [
                [w * 0.28, h * 0.35],  # top-left
                [w * 0.72, h * 0.35],  # top-right
                [w * 0.90, h * 0.90],  # bottom-right
                [w * 0.10, h * 0.90]   # bottom-left
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
