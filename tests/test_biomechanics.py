"""
Unit Tests for Biomechanics Signal Extractors, Phase Segmentation, and Rubric Engines.
"""

import unittest
import numpy as np

from analytics_app.biomechanics.signals import (
    calculate_3point_angle,
    wrist_height,
    knee_angle,
    elbow_angle,
    wrist_velocity,
    hip_shoulder_separation,
    center_of_mass_estimate
)

class TestBiomechanicsSignals(unittest.TestCase):

    def setUp(self):
        # Create a standard 17 COCO keypoint array (X, Y)
        # 0: nose, 5: L_shoulder, 6: R_shoulder, 7: L_elbow, 8: R_elbow,
        # 9: L_wrist, 10: R_wrist, 11: L_hip, 12: R_hip, 13: L_knee, 14: R_knee,
        # 15: L_ankle, 16: R_ankle
        self.kpts = np.zeros((17, 2), dtype=np.float64)

        # Shoulders at Y = 200
        self.kpts[5] = [150, 200]  # L_shoulder
        self.kpts[6] = [250, 200]  # R_shoulder

        # Hips at Y = 400
        self.kpts[11] = [160, 400] # L_hip
        self.kpts[12] = [240, 400] # R_hip

        # Right arm: Elbow at [250, 280], Wrist at [250, 360] -> straight down
        self.kpts[8] = [250, 280]  # R_elbow
        self.kpts[10] = [250, 360] # R_wrist

        # Right leg: Knee at [240, 500], Ankle at [240, 600] -> straight down
        self.kpts[14] = [240, 500] # R_knee
        self.kpts[16] = [240, 600] # R_ankle

    def test_calculate_3point_angle_right_angle(self):
        a = [0.0, 1.0]
        b = [0.0, 0.0]
        c = [1.0, 0.0]
        angle = calculate_3point_angle(a, b, c)
        self.assertAlmostEqual(angle, 90.0, places=4)

    def test_calculate_3point_angle_straight_line(self):
        a = [0.0, 1.0]
        b = [0.0, 0.0]
        c = [0.0, -1.0]
        angle = calculate_3point_angle(a, b, c)
        self.assertAlmostEqual(angle, 180.0, places=4)

    def test_elbow_angle_straight_arm(self):
        # Shoulder [250, 200], Elbow [250, 280], Wrist [250, 360] -> straight line
        angle = elbow_angle(self.kpts, side="right")
        self.assertAlmostEqual(angle, 180.0, places=2)

    def test_elbow_angle_bent_arm(self):
        # Bend elbow to 90 degrees: Wrist at [330, 280]
        self.kpts[10] = [330, 280]
        angle = elbow_angle(self.kpts, side="right")
        self.assertAlmostEqual(angle, 90.0, places=2)

    def test_knee_angle_straight_leg(self):
        # Hip [240, 400], Knee [240, 500], Ankle [240, 600] -> straight leg
        angle = knee_angle(self.kpts, side="right")
        self.assertAlmostEqual(angle, 180.0, places=2)

    def test_knee_angle_bent_leg(self):
        # Bend knee forward: Ankle at [340, 500] -> 90 deg bend
        self.kpts[16] = [340, 500]
        angle = knee_angle(self.kpts, side="right")
        self.assertAlmostEqual(angle, 90.0, places=2)

    def test_wrist_height(self):
        # Wrist at Y=360, Shoulder at Y=200, Hip at Y=400 -> Wrist is lower than shoulder
        h_down = wrist_height(self.kpts, side="right")
        self.assertLess(h_down, 0.0)

        # Move wrist high above shoulder to Y=100
        self.kpts[10] = [250, 100]
        h_up = wrist_height(self.kpts, side="right")
        self.assertGreater(h_up, 0.0)

    def test_wrist_velocity(self):
        # Sequence of 3 frames where wrist moves 30 pixels right per frame at 30 fps
        seq = []
        for i in range(3):
            k = self.kpts.copy()
            k[10] = [250 + i * 30, 360]
            seq.append(k)

        vels = wrist_velocity(seq, side="right", fps=30.0)
        self.assertEqual(len(vels), 3)
        self.assertEqual(vels[0], 0.0)
        self.assertAlmostEqual(vels[1], 900.0, places=2) # 30 px * 30 fps = 900 px/sec

    def test_hip_shoulder_separation(self):
        # Parallel hips & shoulders -> 0 deg separation
        sep_zero = hip_shoulder_separation(self.kpts)
        self.assertAlmostEqual(sep_zero, 0.0, places=2)

        # Rotate shoulders 45 degrees
        self.kpts[5] = [150, 160]
        self.kpts[6] = [250, 240]
        sep_rotated = hip_shoulder_separation(self.kpts)
        self.assertGreater(sep_rotated, 30.0)

    def test_center_of_mass_estimate(self):
        com = center_of_mass_estimate(self.kpts)
        self.assertEqual(len(com), 2)
        self.assertGreater(com[0], 0.0)
        self.assertGreater(com[1], 0.0)


from analytics_app.biomechanics.phase_detector import PhaseDetectorEngine, SERVE_PHASE_CONFIGS

class TestPhaseDetector(unittest.TestCase):

    def test_serve_phase_detection(self):
        # Create a sequence of 20 frames representing a serve
        seq = []
        base_kpts = np.zeros((17, 2), dtype=np.float64)
        base_kpts[5] = [150, 200] # L_shoulder
        base_kpts[6] = [250, 200] # R_shoulder
        base_kpts[11] = [160, 400] # L_hip
        base_kpts[12] = [240, 400] # R_hip
        base_kpts[14] = [240, 500] # R_knee
        base_kpts[16] = [240, 600] # R_ankle

        for i in range(20):
            k = base_kpts.copy()
            # Ball toss: wrist height peaks around frame 5
            wrist_y = 350 - (150 * np.exp(-((i - 5)**2) / 4.0))
            k[10] = [250, wrist_y]

            # Trophy load: knee bend peaks around frame 9
            knee_bend = 50 * np.exp(-((i - 9)**2) / 4.0)
            k[16] = [240 + knee_bend, 600]

            seq.append(k)

        engine = PhaseDetectorEngine(configs=SERVE_PHASE_CONFIGS)
        phases = engine.detect_phases(seq, start_frame=100, fps=30.0)

        self.assertIn("stance", phases)
        self.assertIn("ball_toss", phases)
        self.assertIn("trophy_load", phases)
        self.assertIn("contact", phases)

from analytics_app.biomechanics.rubric_engine import RubricEngine
from analytics_app.biomechanics.feedback_formatter import FeedbackFormatter

class TestRubricAndFeedback(unittest.TestCase):

    def test_rubric_evaluation(self):
        engine = RubricEngine()
        phases = {
            "ball_toss": {"relative_idx": 5, "frame_idx": 105},
            "trophy_load": {"relative_idx": 10, "frame_idx": 110},
            "contact": {"relative_idx": 15, "frame_idx": 115}
        }
        seq = [np.zeros((17, 2), dtype=np.float64) for _ in range(20)]
        for k in seq:
            k[5] = [150, 200]
            k[6] = [250, 200]
            k[11] = [160, 400]
            k[12] = [240, 400]

        eval_res = engine.evaluate_shot("event_001", "serve", phases, seq)
        self.assertEqual(eval_res["shot_id"], "event_001")
        self.assertEqual(eval_res["shot_type"], "serve")
        self.assertIn("overall_score", eval_res)
        self.assertIn("fault_tags", eval_res)

    def test_feedback_formatter(self):
        formatter = FeedbackFormatter()
        msg = formatter.format_fault_feedback("DROPPED_ELBOW", {"value": 82.0, "good_range": [90.0, 120.0]})
        self.assertIn("82", msg)
        self.assertIn("90–120", msg)
        self.assertIn("elbow", msg)


if __name__ == "__main__":
    unittest.main()
