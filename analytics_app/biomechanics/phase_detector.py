"""
Generic Phase Segmentation Engine
Segments biomechanical sub-phases over pose keypoint time-series based on declarative PhaseDetectorConfig rules.
"""

from typing import List, Dict, Any, Optional
import numpy as np

from .signals import (
    wrist_height,
    knee_angle,
    elbow_angle,
    wrist_velocity,
    hip_shoulder_separation,
    center_of_mass_estimate
)

SIGNAL_FUNCTIONS = {
    "wrist_height": wrist_height,
    "knee_angle": knee_angle,
    "elbow_angle": elbow_angle,
    "hip_shoulder_separation": hip_shoulder_separation,
    "center_of_mass_estimate": center_of_mass_estimate
}

class PhaseDetectorConfig:
    def __init__(
        self,
        phase_name: str,
        signal: str,
        extremum: str, # "min" | "max" | "velocity_peak"
        search_window: List[float], # Relative frame ratios [start_ratio, end_ratio], e.g. [0.0, 0.4]
        constraint: Optional[str] = None # e.g. "must_occur_after:ball_toss"
    ):
        self.phase_name = phase_name
        self.signal = signal
        self.extremum = extremum
        self.search_window = search_window
        self.constraint = constraint

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_name": self.phase_name,
            "signal": self.signal,
            "extremum": self.extremum,
            "search_window": self.search_window,
            "constraint": self.constraint
        }


SERVE_PHASE_CONFIGS = [
    PhaseDetectorConfig(
        phase_name="stance",
        signal="wrist_velocity",
        extremum="min",
        search_window=[0.0, 0.25],
        constraint=None
    ),
    PhaseDetectorConfig(
        phase_name="ball_toss",
        signal="wrist_height",
        extremum="max",
        search_window=[0.1, 0.45],
        constraint="must_occur_after:stance"
    ),
    PhaseDetectorConfig(
        phase_name="trophy_load",
        signal="knee_angle",
        extremum="min",
        search_window=[0.25, 0.65],
        constraint="must_occur_after:ball_toss"
    ),
    PhaseDetectorConfig(
        phase_name="acceleration",
        signal="wrist_velocity",
        extremum="velocity_peak",
        search_window=[0.45, 0.85],
        constraint="must_occur_after:trophy_load"
    ),
    PhaseDetectorConfig(
        phase_name="contact",
        signal="wrist_height",
        extremum="max",
        search_window=[0.55, 0.90],
        constraint="must_occur_after:acceleration"
    ),
    PhaseDetectorConfig(
        phase_name="follow_through",
        signal="wrist_height",
        extremum="min",
        search_window=[0.75, 1.0],
        constraint="must_occur_after:contact"
    )
]


class PhaseDetectorEngine:
    def __init__(self, configs: List[PhaseDetectorConfig] = None):
        self.configs = configs if configs is not None else SERVE_PHASE_CONFIGS

    def detect_phases(
        self,
        keypoints_sequence: List[np.ndarray],
        start_frame: int = 0,
        fps: float = 30.0,
        side: str = "right"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Segments frame indices for each biomechanical phase over keypoints_sequence.
        Returns dict mapping phase_name -> {"frame_idx": int, "relative_idx": int, "signal_value": float}.
        """
        num_frames = len(keypoints_sequence)
        if num_frames == 0:
            return {}

        detected_phases = {}

        for cfg in self.configs:
            # 1. Compute search bounds
            w_start = int(np.clip(cfg.search_window[0] * num_frames, 0, num_frames - 1))
            w_end = int(np.clip(cfg.search_window[1] * num_frames, w_start + 1, num_frames))

            # Apply sequential constraints if specified
            if cfg.constraint and ":" in cfg.constraint:
                c_type, dep_phase = cfg.constraint.split(":", 1)
                if c_type == "must_occur_after" and dep_phase in detected_phases:
                    dep_rel_idx = detected_phases[dep_phase]["relative_idx"]
                    w_start = max(w_start, dep_rel_idx + 1)
                    if w_start >= num_frames:
                        w_start = num_frames - 1
                    if w_end <= w_start:
                        w_end = min(w_start + 1, num_frames)

            # 2. Extract signal values over search window
            values = []
            valid_rel_indices = list(range(w_start, w_end))

            if cfg.signal == "wrist_velocity":
                vels = wrist_velocity(keypoints_sequence, side=side, fps=fps)
                values = [vels[i] if i < len(vels) else 0.0 for i in valid_rel_indices]
            elif cfg.signal in SIGNAL_FUNCTIONS:
                fn = SIGNAL_FUNCTIONS[cfg.signal]
                for i in valid_rel_indices:
                    kpts = keypoints_sequence[i]
                    if cfg.signal in ("knee_angle", "elbow_angle", "wrist_height"):
                        val = fn(kpts, side=side)
                    else:
                        val = fn(kpts)
                    values.append(val)
            else:
                values = [0.0] * len(valid_rel_indices)

            if not values:
                best_rel_idx = w_start
                best_val = 0.0
            else:
                if cfg.extremum == "max" or cfg.extremum == "velocity_peak":
                    best_local_idx = int(np.argmax(values))
                else: # "min"
                    best_local_idx = int(np.argmin(values))

                best_rel_idx = valid_rel_indices[best_local_idx]
                best_val = float(values[best_local_idx])

            abs_frame_idx = start_frame + best_rel_idx
            detected_phases[cfg.phase_name] = {
                "phase_name": cfg.phase_name,
                "frame_idx": abs_frame_idx,
                "relative_idx": best_rel_idx,
                "signal_value": round(best_val, 2)
            }

        return detected_phases
