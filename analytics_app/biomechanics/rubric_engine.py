"""
Feature Extraction & Rubric Scoring Engine
Evaluates biomechanical features against declarative ShotRubric configs and emits structured scores and fault tags.
"""

import json
import os
from typing import Dict, List, Any, Optional
import numpy as np

from .signals import (
    wrist_height,
    knee_angle,
    elbow_angle,
    wrist_velocity,
    hip_shoulder_separation,
    center_of_mass_estimate
)

CONFIGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")

SIGNAL_MAP = {
    "wrist_height": wrist_height,
    "knee_angle": knee_angle,
    "elbow_angle": elbow_angle,
    "hip_shoulder_separation": hip_shoulder_separation,
    "center_of_mass_estimate": center_of_mass_estimate
}


class RubricEngine:
    def __init__(self, rubric_path: Optional[str] = None):
        if rubric_path is None:
            rubric_path = os.path.join(CONFIGS_DIR, "serve_rubric.json")

        self.rubric = self._load_rubric(rubric_path)

    def _load_rubric(self, path: str) -> Dict[str, Any]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"shot_type": "serve", "features": []}

    def evaluate_shot(
        self,
        shot_id: str,
        shot_type: str,
        detected_phases: Dict[str, Dict[str, Any]],
        keypoints_sequence: List[np.ndarray],
        side: str = "right"
    ) -> Dict[str, Any]:
        """
        Evaluates detected phase keypoints against rubric range rules.
        Returns structured shot evaluation JSON object.
        """
        features_config = self.rubric.get("features", [])
        evaluated_features = []
        emitted_fault_tags = []

        total_weight = 0.0
        weighted_score_sum = 0.0

        for f_cfg in features_config:
            name = f_cfg["name"]
            phase_name = f_cfg["phase"]
            sig_name = f_cfg["signal"]
            good_min, good_max = f_cfg["good_range"]
            bord_range = f_cfg.get("borderline_range", [good_min, good_max])
            bord_min, bord_max = bord_range[0], bord_range[1]
            fault_tag = f_cfg.get("fault_tag", "UNKNOWN_FAULT")
            fault_tag_high = f_cfg.get("fault_tag_high", fault_tag)
            weight = float(f_cfg.get("weight", 1.0))

            # Retrieve keypoints at the detected phase frame
            rel_idx = 0
            if phase_name in detected_phases:
                rel_idx = detected_phases[phase_name]["relative_idx"]

            if 0 <= rel_idx < len(keypoints_sequence):
                kpts = keypoints_sequence[rel_idx]
            elif keypoints_sequence:
                kpts = keypoints_sequence[-1]
            else:
                kpts = None

            # Measure value
            if sig_name in SIGNAL_MAP and kpts is not None:
                fn = SIGNAL_MAP[sig_name]
                if sig_name in ("knee_angle", "elbow_angle", "wrist_height"):
                    measured_val = fn(kpts, side=side)
                else:
                    measured_val = fn(kpts)
            else:
                measured_val = 0.0

            measured_val = round(float(measured_val), 1)

            # Determine status & score contribution
            status = "good"
            feature_score = 100.0
            tag_to_emit = None

            if good_min <= measured_val <= good_max:
                status = "good"
                feature_score = 100.0
            elif bord_min <= measured_val <= bord_max:
                status = "borderline"
                feature_score = 70.0
                if measured_val < good_min:
                    tag_to_emit = fault_tag
                else:
                    tag_to_emit = fault_tag_high
            else:
                status = "fault"
                feature_score = 40.0
                if measured_val < good_min:
                    tag_to_emit = fault_tag
                else:
                    tag_to_emit = fault_tag_high

            if tag_to_emit and tag_to_emit not in emitted_fault_tags:
                emitted_fault_tags.append(tag_to_emit)

            total_weight += weight
            weighted_score_sum += (feature_score * weight)

            evaluated_features.append({
                "name": name,
                "phase": phase_name,
                "value": measured_val,
                "status": status,
                "good_range": [good_min, good_max],
                "fault_tag": tag_to_emit if tag_to_emit else fault_tag
            })

        overall_score = int(round(weighted_score_sum / max(1.0, total_weight)))

        return {
            "shot_id": shot_id,
            "shot_type": shot_type,
            "overall_score": overall_score,
            "features": evaluated_features,
            "fault_tags": emitted_fault_tags,
            "phases": detected_phases
        }
