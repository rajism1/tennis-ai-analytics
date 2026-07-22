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

    def detect_and_track(self, frame, court_detector=None):
        """
        Detects players in frame and returns structured tracking data.
        Returns:
            list of dicts: [
                {
                    "player_id": "Player 1",
                    "bbox": [x1, y1, x2, y2],
                    "feet_pixel": (x, y),
                    "court_pos_m": (X, Y)
                }, ...
            ]
        """
        players = []
        h, w, _ = frame.shape

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

            # Sort detected players by vertical position y2 (bottom of bounding box)
            detected_boxes.sort(key=lambda b: b[3]) # Top court first (Player 1), bottom court second (Player 2)

            for idx, (x1, y1, x2, y2, conf) in enumerate(detected_boxes[:2]):
                player_name = f"Player {idx + 1}"
                feet_px = (float((x1 + x2) / 2.0), float(y2))
                
                court_m = (0.0, 0.0)
                if court_detector is not None:
                    court_m = court_detector.pixel_to_court(feet_px)

                players.append({
                    "player_id": player_name,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "feet_pixel": feet_px,
                    "court_pos_m": court_m,
                    "confidence": conf
                })
        else:
            # Simulated fallback for testing without GPU/YOLO weights loaded
            simulated_boxes = [
                [int(w * 0.45), int(h * 0.25), int(w * 0.52), int(h * 0.45)], # Far player (P1)
                [int(w * 0.42), int(h * 0.65), int(w * 0.55), int(h * 0.90)]  # Near player (P2)
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
