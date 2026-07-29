"""
Player Body Pose Estimation Module
Extracts 17 COCO keypoints (Shoulders, Hips, Knees, Ankles, Wrists, Elbows) and computes joint angles.
"""

import cv2
import numpy as np
import math
from config import COCO_KEYPOINTS

class PoseEstimator:
    def __init__(self, model_name="yolo11m-pose.pt"):
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            import torch
            from ultralytics import YOLO
            
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

            self.model = YOLO(self.model_name)
            print(f"[PoseEstimator] Loaded Pose YOLO model on acceleration device: '{self.device}'")
        except Exception as e:
            print(f"[PoseEstimator] Warning: Could not load Pose YOLO model ({e}). Using keypoint estimator fallback.")
            self.model = None

    def calculate_angle(self, a, b, c):
        """Calculates 2D joint angle in degrees between three points (a-b-c with b as vertex)."""
        ba = np.array([a[0] - b[0], a[1] - b[1]])
        bc = np.array([c[0] - b[0], c[1] - b[1]])
        
        norm_ba = np.linalg.norm(ba)
        norm_bc = np.linalg.norm(bc)
        if norm_ba == 0 or norm_bc == 0:
            return 0.0
            
        cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        return float(np.degrees(angle))

    def estimate_pose(self, frame, player_bboxes):
        """
        Estimates pose for each detected player bounding box.
        Returns dict mapping player_id -> keypoint dictionary and joint angles.
        """
        poses = {}
        
        if self.model is not None:
            results = self.model(frame, imgsz=640, device=self.device, verbose=False)
            if len(results) > 0 and results[0].keypoints is not None:
                kpts_data = results[0].keypoints.xy.cpu().numpy() # [N, 17, 2]
                
                # Match keypoint sets to players based on bounding box proximity
                for p in player_bboxes:
                    p_id = p["player_id"]
                    px1, py1, px2, py2 = p["bbox"]
                    
                    best_kpts = None
                    best_dist = float("inf")
                    p_center = ((px1 + px2) / 2.0, (py1 + py2) / 2.0)
                    
                    for kpts in kpts_data:
                        valid_pts = kpts[kpts[:, 0] > 0]
                        if len(valid_pts) > 0:
                            center = np.mean(valid_pts, axis=0)
                            dist = np.linalg.norm(center - p_center)
                            if dist < best_dist:
                                best_dist = dist
                                best_kpts = kpts

                    if best_kpts is not None:
                        poses[p_id] = self._process_keypoints(best_kpts)
        else:
            # Simulated fallback keypoints matching player position
            for p in player_bboxes:
                p_id = p["player_id"]
                x1, y1, x2, y2 = p["bbox"]
                w, h = x2 - x1, y2 - y1
                
                # Generate synthetic keypoint coordinates relative to bounding box
                syn_kpts = np.zeros((17, 2), dtype=np.float32)
                syn_kpts[0] = [x1 + w*0.5, y1 + h*0.1]  # Nose
                syn_kpts[5] = [x1 + w*0.3, y1 + h*0.25] # Left Shoulder
                syn_kpts[6] = [x1 + w*0.7, y1 + h*0.25] # Right Shoulder
                syn_kpts[7] = [x1 + w*0.2, y1 + h*0.4]  # Left Elbow
                syn_kpts[8] = [x1 + w*0.8, y1 + h*0.35] # Right Elbow
                syn_kpts[9] = [x1 + w*0.1, y1 + h*0.5]  # Left Wrist
                syn_kpts[10] = [x1 + w*0.85, y1 + h*0.2] # Right Wrist (Racket hand up)
                syn_kpts[11] = [x1 + w*0.35, y1 + h*0.55] # Left Hip
                syn_kpts[12] = [x1 + w*0.65, y1 + h*0.55] # Right Hip
                syn_kpts[13] = [x1 + w*0.35, y1 + h*0.75] # Left Knee
                syn_kpts[14] = [x1 + w*0.65, y1 + h*0.75] # Right Knee
                syn_kpts[15] = [x1 + w*0.35, y1 + h*0.95] # Left Ankle
                syn_kpts[16] = [x1 + w*0.65, y1 + h*0.95] # Right Ankle

                poses[p_id] = self._process_keypoints(syn_kpts)

        return poses

    def _process_keypoints(self, kpts):
        """Builds named keypoint dict and calculates biomechanical joint angles."""
        named_kpts = {}
        for idx, name in COCO_KEYPOINTS.items():
            named_kpts[name] = [float(kpts[idx][0]), float(kpts[idx][1])]

        # Compute key angles
        angles = {}
        # Right elbow flexion (Shoulder -> Elbow -> Wrist)
        angles["right_elbow_angle"] = self.calculate_angle(named_kpts["right_shoulder"], named_kpts["right_elbow"], named_kpts["right_wrist"])
        # Left elbow flexion
        angles["left_elbow_angle"] = self.calculate_angle(named_kpts["left_shoulder"], named_kpts["left_elbow"], named_kpts["left_wrist"])
        # Right knee flexion (Hip -> Knee -> Ankle)
        angles["right_knee_angle"] = self.calculate_angle(named_kpts["right_hip"], named_kpts["right_knee"], named_kpts["right_ankle"])
        # Shoulder tilt relative to horizontal
        rs, ls = named_kpts["right_shoulder"], named_kpts["left_shoulder"]
        angles["shoulder_tilt_deg"] = float(np.degrees(np.arctan2(rs[1] - ls[1], rs[0] - ls[0])))

        return {
            "keypoints": named_kpts,
            "angles": angles
        }

    def draw_poses(self, frame, poses):
        """Draws skeleton lines and keypoints on frame."""
        skeleton_pairs = [
            ("left_shoulder", "right_shoulder"),
            ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
            ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
            ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
            ("left_hip", "right_hip"),
            ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
            ("right_hip", "right_knee"), ("right_knee", "right_ankle")
        ]

        for p_id, p_data in poses.items():
            kpts = p_data["keypoints"]
            # Draw skeleton connections
            for p1_name, p2_name in skeleton_pairs:
                pt1 = kpts[p1_name]
                pt2 = kpts[p2_name]
                if pt1[0] > 0 and pt2[0] > 0:
                    cv2.line(frame, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), (0, 255, 255), 2)
            
            # Draw keypoints
            for name, pt in kpts.items():
                if pt[0] > 0 and pt[1] > 0:
                    cv2.circle(frame, (int(pt[0]), int(pt[1])), 4, (0, 165, 255), -1)

        return frame
