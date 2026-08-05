"""
Fault Tag Feedback Formatter (Component 3)
Maps fault tags to 3-part structured corrective coaching feedback templates.
"""

import json
import os
from typing import Dict, Any, List

CONFIGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")

class FeedbackFormatter:
    def __init__(self, template_path: str = None):
        if template_path is None:
            template_path = os.path.join(CONFIGS_DIR, "fault_templates.json")

        self.templates = self._load_templates(template_path)

    def _load_templates(self, path: str) -> Dict[str, str]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def format_fault_feedback(self, fault_tag: str, feature_data: Dict[str, Any]) -> str:
        """
        Formats a fault tag into 3-part structured feedback using measured value and target range.
        """
        template = self.templates.get(
            fault_tag,
            "Fault detected: {fault_tag}. Measured value: {value} (target range: {range}). Focus on proper form execution."
        )

        val = feature_data.get("value", 0.0)
        if isinstance(val, float) and val.is_integer():
            val_str = str(int(val))
        else:
            val_str = str(val)

        target_range = feature_data.get("good_range", [0, 0])
        r0 = int(target_range[0]) if isinstance(target_range[0], (int, float)) and float(target_range[0]).is_integer() else target_range[0]
        r1 = int(target_range[1]) if isinstance(target_range[1], (int, float)) and float(target_range[1]).is_integer() else target_range[1]
        range_str = f"{r0}–{r1}"

        try:
            return template.format(
                value=val_str,
                range=range_str,
                fault_tag=fault_tag
            )
        except Exception:
            return f"Fault {fault_tag}: Measured {val} (target: {range_str})."

    def format_shot_feedback(self, evaluated_shot: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generates feedback messages for all faults in an evaluated shot.
        Returns list of dicts with fault_tag, feature_name, and feedback message.
        """
        feedback_list = []
        features = evaluated_shot.get("features", [])

        for feat in features:
            if feat.get("status") in ("borderline", "fault"):
                tag = feat.get("fault_tag")
                if tag:
                    msg = self.format_fault_feedback(tag, feat)
                    feedback_list.append({
                        "fault_tag": tag,
                        "feature_name": feat.get("name"),
                        "phase": feat.get("phase"),
                        "message": msg
                    })

        return feedback_list
