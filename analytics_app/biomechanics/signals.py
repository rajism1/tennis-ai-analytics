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
    Returns interior joint angle between 0.0 and 180.0 degrees.
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
    Computes normalized wrist height relative to standing player height.
    Height above ground = (ankle_y - wrist_y) / (ankle_y - head_y)
    Returns positive value:
      ~0.7-0.8 at shoulder height
      ~1.0 at head height
      ~1.1-1.3 at full toss / contact reach
    """
    if keypoints is None or len(keypoints) < 17:
        return 1.0

    w_idx = COCO_KEYPOINTS["right_wrist"] if side == "right" else COCO_KEYPOINTS["left_wrist"]
    head_idx = COCO_KEYPOINTS["nose"]
    a_idx = COCO_KEYPOINTS["right_ankle"] if side == "right" else COCO_KEYPOINTS["left_ankle"]

    wrist_y = keypoints[w_idx][1]
    head_y = keypoints[head_idx][1]
    ankle_y = keypoints[a_idx][1]

    player_h = abs(ankle_y - head_y)
    if player_h < 1.0:
        s_idx = COCO_KEYPOINTS["right_shoulder"] if side == "right" else COCO_KEYPOINTS["left_shoulder"]
        h_idx = COCO_KEYPOINTS["right_hip"] if side == "right" else COCO_KEYPOINTS["left_hip"]
        sh_h = abs(keypoints[h_idx][1] - keypoints[s_idx][1])
        player_h = sh_h * 2.5 if sh_h > 1.0 else 200.0

    wrist_h_above_ground = ankle_y - wrist_y
    norm_h = wrist_h_above_ground / player_h

    return float(round(norm_h, 2))


def knee_angle(keypoints, side="right"):
    """
    Computes interior knee flexion angle (hip-knee-ankle) in degrees.
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
    Computes interior elbow joint angle (shoulder-elbow-wrist) in degrees.
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
    Computes rotational coil angle separation (in degrees) between hip line and shoulder line.
    Measures angle between 2D shoulder vector (R_shoulder - L_shoulder) and 2D hip vector (R_hip - L_hip).
    """
    if keypoints is None or len(keypoints) < 17:
        return 0.0

    ls, rs = keypoints[COCO_KEYPOINTS["left_shoulder"]], keypoints[COCO_KEYPOINTS["right_shoulder"]]
    lh, rh = keypoints[COCO_KEYPOINTS["left_hip"]], keypoints[COCO_KEYPOINTS["right_hip"]]

    s_vec = np.array([rs[0] - ls[0], rs[1] - ls[1]], dtype=np.float64)
    h_vec = np.array([rh[0] - lh[0], rh[1] - lh[1]], dtype=np.float64)

    norm_s = np.linalg.norm(s_vec)
    norm_h = np.linalg.norm(h_vec)

    if norm_s < 1e-6 or norm_h < 1e-6:
        return 0.0

    cosine_angle = np.dot(s_vec, h_vec) / (norm_s * norm_h)
    angle_deg = float(np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0))))

    return float(round(angle_deg, 1))


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
