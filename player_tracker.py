"""
Player Detection & Tracking Module
Uses YOLO11 for person detection and tracks players (Player 1 near, Player 2 far court).
"""

import cv2
import numpy as np

class PlayerTracker:
    def __init__(self, model_name="yolo11m.pt", conf_thresh=0.4):
        self.model_name = model_name
        self.conf_thresh = conf_thresh
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            import lap
            self.use_track = True
        except ImportError:
            self.use_track = False

        try:
            import torch
            from ultralytics import YOLO
            
            # Select MPS for M2 Mac GPU, CUDA for NVIDIA, or CPU fallback
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

            self.model = YOLO(self.model_name)
            print(f"[PlayerTracker] Loaded YOLO model on acceleration device: '{self.device}'")
        except Exception as e:
            print(f"[PlayerTracker] Warning: Could not load YOLO model ({e}). Using simulated detector fallback.")
            self.model = None

    def detect_and_track(self, frame, court_detector=None, poses=None):
        """
        Detects players in frame and returns structured tracking data with ankle anchoring and EMA position smoothing.
        """
        players = []
        h, w, _ = frame.shape

        if not hasattr(self, "ema_positions"):
            self.ema_positions = {}

        if self.model is not None:
            detected_boxes = []
            if getattr(self, "use_track", True):
                try:
                    # Try default Ultralytics tracking with hardware acceleration
                    results = self.model.track(frame, classes=[0], conf=self.conf_thresh, device=self.device, persist=True, verbose=False)
                    if len(results) > 0 and results[0].boxes is not None:
                        boxes = results[0].boxes
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = float(box.conf[0].cpu().numpy())
                            detected_boxes.append((x1, y1, x2, y2, conf))
                except Exception as e:
                    self.use_track = False
                    results = self.model.predict(frame, classes=[0], conf=self.conf_thresh, device=self.device, verbose=False)
                    if len(results) > 0 and results[0].boxes is not None:
                        boxes = results[0].boxes
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = float(box.conf[0].cpu().numpy())
                            detected_boxes.append((x1, y1, x2, y2, conf))
            else:
                results = self.model.predict(frame, classes=[0], conf=self.conf_thresh, device=self.device, verbose=False)
                if len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        detected_boxes.append((x1, y1, x2, y2, conf))

            # Sort detected players by vertical position y2 (top court vs bottom court)
            detected_boxes.sort(key=lambda b: b[3])

            for idx, (x1, y1, x2, y2, conf) in enumerate(detected_boxes[:2]):
                player_name = f"Player {idx + 1}"
                
                # Default feet position from bbox bottom-center
                feet_px = (float((x1 + x2) / 2.0), float(y2))
                
                # Pose Keypoint Ankle Anchoring (Prevents shadow/racket distortion)
                if poses and player_name in poses and "keypoints" in poses[player_name]:
                    kpts = poses[player_name]["keypoints"]
                    l_ankle = kpts.get("left_ankle", [0, 0])
                    r_ankle = kpts.get("right_ankle", [0, 0])
                    
                    ankles = []
                    if l_ankle[0] > 0 and l_ankle[1] > 0:
                        ankles.append(l_ankle)
                    if r_ankle[0] > 0 and r_ankle[1] > 0:
                        ankles.append(r_ankle)
                        
                    if len(ankles) > 0:
                        avg_ankle_x = float(np.mean([pt[0] for pt in ankles]))
                        avg_ankle_y = float(np.mean([pt[1] for pt in ankles]))
                        # Use ankle ground contact point
                        feet_px = (avg_ankle_x, avg_ankle_y)

                raw_court_m = (0.0, 0.0)
                if court_detector is not None:
                    raw_court_m = court_detector.pixel_to_court(feet_px)

                # Exponential Moving Average (EMA) Smoothing on Court Position (alpha = 0.35)
                alpha = 0.35
                if player_name in self.ema_positions:
                    prev_x, prev_y = self.ema_positions[player_name]
                    smooth_x = alpha * raw_court_m[0] + (1 - alpha) * prev_x
                    smooth_y = alpha * raw_court_m[1] + (1 - alpha) * prev_y
                    court_m = (smooth_x, smooth_y)
                else:
                    court_m = raw_court_m
                
                self.ema_positions[player_name] = court_m

                players.append({
                    "player_id": player_name,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "feet_pixel": feet_px,
                    "court_pos_m": court_m,
                    "confidence": conf
                })
        else:
            # Simulated fallback
            simulated_boxes = [
                [int(w * 0.45), int(h * 0.25), int(w * 0.52), int(h * 0.45)],
                [int(w * 0.42), int(h * 0.65), int(w * 0.55), int(h * 0.90)]
            ]
            for idx, bbox in enumerate(simulated_boxes):
                feet_px = (float((bbox[0] + bbox[2]) / 2.0), float(bbox[3]))
                court_m = court_detector.pixel_to_court(feet_px) if court_detector else (0.0, 0.0)
                players.append({
                    "player_id": f"Player {idx + 1}",
                    "bbox": bbox,
                    "feet_pixel": feet_px,
                    "court_pos_m": court_m,
                    "confidence": 0.95
                })

        return players

    def draw_players(self, frame, players):
        """Draws player bounding boxes and IDs on the frame."""
        colors = {"Player 1": (0, 0, 255), "Player 2": (255, 0, 0)}
        for p in players:
            p_id = p["player_id"]
            x1, y1, x2, y2 = p["bbox"]
            color = colors.get(p_id, (0, 255, 0))
            
            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Label banner
            label = f"{p_id} ({p['court_pos_m'][0]:.1f}m, {p['court_pos_m'][1]:.1f}m)"
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Feet location marker
            fx, fy = int(p["feet_pixel"][0]), int(p["feet_pixel"][1])
            cv2.circle(frame, (fx, fy), 5, (0, 255, 255), -1)
            
        return frame
