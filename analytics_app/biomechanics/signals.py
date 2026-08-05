"""
Kinematic Signal Extractors for Biomechanical Pose Telemetry
Implements core joint angle, velocity, and rotational separation functions.
"""

import numpy as np
import math

COCO_KEYPOINTS = {
    "nose": 0, "left_eye": 1, "right_eye": 2, "left_ear": 3, "right_ear": 4,
    "left_shoulder": 5, "right_shoulder": 6, "left_elbow": 7, "right_elbow": 8,
    "left_wrist": 9, "right_wrist": 10, "left_hip": 11, "right_hip": 12,
    "left_knee": 13, "right_knee": 14, "left_ankle": 15, "right_ankle": 16
}

def calculate_3point_angle(a, b, c):
    """
    Computes 2D angle (in degrees) at joint vertex 'b' formed by vectors ba and bc.
    Returns angle between 0.0 and 180.0 degrees.
    """
    if a is None or b is None or c is None:
        return 0.0
    
    ba = np.array([a[0] - b[0], a[1] - b[1]], dtype=np.float64)
    bc = np.array([c[0] - b[0], c[1] - b[1]], dtype=np.float64)

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba < 1e-6 or norm_bc < 1e-6:
        return 0.0

    cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return float(np.degrees(angle))


def wrist_height(keypoints, side="right"):
    """
    Computes vertical wrist height relative to shoulder height, normalized by torso length.
    In image space (Y grows downwards), higher wrist in physical space yields higher positive values.
    """
    if keypoints is None or len(keypoints) < 17:
        return 0.0

    w_idx = COCO_KEYPOINTS["right_wrist"] if side == "right" else COCO_KEYPOINTS["left_wrist"]
    s_idx = COCO_KEYPOINTS["right_shoulder"] if side == "right" else COCO_KEYPOINTS["left_shoulder"]
    h_idx = COCO_KEYPOINTS["right_hip"] if side == "right" else COCO_KEYPOINTS["left_hip"]

    wrist = keypoints[w_idx]
    shoulder = keypoints[s_idx]
    hip = keypoints[h_idx]

    torso_len = abs(hip[1] - shoulder[1])
    if torso_len < 1e-3:
        torso_len = 100.0

    # Inverted Y: (shoulder_y - wrist_y) / torso_length
    norm_h = (shoulder[1] - wrist[1]) / torso_len
    return float(norm_h)


def knee_angle(keypoints, side="right"):
    """
    Computes knee flexion angle (hip-knee-ankle) in degrees.
    Fully extended leg ~ 180 deg, bent knee ~ 110-130 deg.
    """
    if keypoints is None or len(keypoints) < 17:
        return 180.0

    h_idx = COCO_KEYPOINTS["right_hip"] if side == "right" else COCO_KEYPOINTS["left_hip"]
    k_idx = COCO_KEYPOINTS["right_knee"] if side == "right" else COCO_KEYPOINTS["left_knee"]
    a_idx = COCO_KEYPOINTS["right_ankle"] if side == "right" else COCO_KEYPOINTS["left_ankle"]

    return calculate_3point_angle(keypoints[h_idx], keypoints[k_idx], keypoints[a_idx])


def elbow_angle(keypoints, side="right"):
    """
    Computes elbow joint angle (shoulder-elbow-wrist) in degrees.
    Fully extended arm ~ 160-180 deg, trophy load angle ~ 90-120 deg.
    """
    if keypoints is None or len(keypoints) < 17:
        return 180.0

    s_idx = COCO_KEYPOINTS["right_shoulder"] if side == "right" else COCO_KEYPOINTS["left_shoulder"]
    e_idx = COCO_KEYPOINTS["right_elbow"] if side == "right" else COCO_KEYPOINTS["left_elbow"]
    w_idx = COCO_KEYPOINTS["right_wrist"] if side == "right" else COCO_KEYPOINTS["left_wrist"]

    return calculate_3point_angle(keypoints[s_idx], keypoints[e_idx], keypoints[w_idx])


def wrist_velocity(keypoints_sequence, side="right", fps=30.0):
    """
    Computes instantaneous wrist velocity series (in pixels/sec) over a time-series of keypoints.
    """
    if not keypoints_sequence:
        return []

    w_idx = COCO_KEYPOINTS["right_wrist"] if side == "right" else COCO_KEYPOINTS["left_wrist"]
    dt = 1.0 / float(fps)
    velocities = [0.0]

    for i in range(1, len(keypoints_sequence)):
        k1 = keypoints_sequence[i - 1]
        k2 = keypoints_sequence[i]

        if k1 is None or k2 is None or len(k1) < 17 or len(k2) < 17:
            velocities.append(0.0)
            continue

        p1 = k1[w_idx]
        p2 = k2[w_idx]
        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        velocities.append(float(dist / dt))

    return velocities


def hip_shoulder_separation(keypoints):
    """
    Computes rotational angle separation (in degrees) between hip line and shoulder line.
    Measures torso coil / separation angle.
    """
    if keypoints is None or len(keypoints) < 17:
        return 0.0

    ls, rs = keypoints[COCO_KEYPOINTS["left_shoulder"]], keypoints[COCO_KEYPOINTS["right_shoulder"]]
    lh, rh = keypoints[COCO_KEYPOINTS["left_hip"]], keypoints[COCO_KEYPOINTS["right_hip"]]

    shoulder_angle = math.atan2(rs[1] - ls[1], rs[0] - ls[0])
    hip_angle = math.atan2(rh[1] - lh[1], rh[0] - lh[0])

    diff_deg = abs(math.degrees(shoulder_angle - hip_angle)) % 360.0
    if diff_deg > 180.0:
        diff_deg = 360.0 - diff_deg

    return float(diff_deg)


def center_of_mass_estimate(keypoints):
    """
    Estimates 2D Center of Mass [X, Y] as weighted average of major torso/leg joints.
    """
    if keypoints is None or len(keypoints) < 17:
        return [0.0, 0.0]

    indices = [
        COCO_KEYPOINTS["left_shoulder"], COCO_KEYPOINTS["right_shoulder"],
        COCO_KEYPOINTS["left_hip"], COCO_KEYPOINTS["right_hip"],
        COCO_KEYPOINTS["left_knee"], COCO_KEYPOINTS["right_knee"]
    ]

    pts = [keypoints[i] for i in indices if keypoints[i] is not None]
    if not pts:
        return [0.0, 0.0]

    arr = np.array(pts, dtype=np.float64)
    com = np.mean(arr, axis=0)
    return [float(com[0]), float(com[1])]
