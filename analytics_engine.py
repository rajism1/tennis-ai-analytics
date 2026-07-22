"""
Analytics Engine & Data Storage Module
Stores structured frame & event telemetry and exports to JSON, CSV, and SQLite DB.
"""

import json
import csv
import os
import sqlite3
import pandas as pd
from config import OUTPUT_DIR

class AnalyticsEngine:
    def __init__(self, output_dir=OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.records = []
        self.db_path = os.path.join(self.output_dir, "tennis_analytics.db")
        self._init_sqlite_db()

    def _init_sqlite_db(self):
        """Initializes SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_events (
                event_id TEXT PRIMARY KEY,
                timestamp_sec REAL,
                frame_idx INTEGER,
                player TEXT,
                event_type TEXT,
                stroke TEXT,
                speed_kmh REAL,
                spin TEXT,
                landing_x REAL,
                landing_y REAL,
                court_pos_x REAL,
                court_pos_y REAL,
                reaction_time_ms INTEGER,
                result TEXT,
                body_pose_json TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def log_event(self, event_data):
        """Logs a single event structured record."""
        if event_data is None:
            return

        self.records.append(event_data)
        
        # Save to SQLite DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        landing = event_data.get("landing_court_position_meters", (0.0, 0.0))
        court_pos = event_data.get("court_position_meters", (0.0, 0.0))
        pose_json = json.dumps(event_data.get("body_pose_angles", {}))

        cursor.execute('''
            INSERT OR REPLACE INTO analytics_events VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        ''', (
            event_data.get("event_id"),
            event_data.get("timestamp_sec"),
            event_data.get("frame_idx"),
            event_data.get("player"),
            event_data.get("event_type"),
            event_data.get("stroke"),
            event_data.get("speed_kmh"),
            event_data.get("spin"),
            landing[0], landing[1],
            court_pos[0], court_pos[1],
            event_data.get("reaction_time_ms", 0),
            event_data.get("result"),
            pose_json
        ))
        conn.commit()
        conn.close()

    def export_json(self, filename="tennis_match_analytics.json"):
        """Exports all logged records to a formatted JSON file."""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w") as f:
            json.dump(self.records, f, indent=2)
        print(f"[AnalyticsEngine] Exported {len(self.records)} events to JSON: {filepath}")
        return filepath

    def export_csv(self, filename="tennis_match_analytics.csv"):
        """Exports key metrics to CSV format for data science & ML pipelines."""
        filepath = os.path.join(self.output_dir, filename)
        if len(self.records) == 0:
            # Write empty dataframe with schema columns
            cols = ["event_id", "timestamp_sec", "frame_idx", "player", "event_type", "stroke", "speed_kmh", "spin", "result"]
            df = pd.DataFrame(columns=cols)
        else:
            df = pd.DataFrame(self.records)
            
        df.to_csv(filepath, index=False)
        print(f"[AnalyticsEngine] Exported {len(self.records)} events to CSV: {filepath}")
        return filepath

    def get_match_summary(self):
        """Generates statistical summary of match performance."""
        if len(self.records) == 0:
            return {"status": "No events recorded"}

        df = pd.DataFrame(self.records)
        summary = {
            "total_events": len(df),
            "max_ball_speed_kmh": float(df["speed_kmh"].max()) if "speed_kmh" in df else 0.0,
            "avg_ball_speed_kmh": float(df["speed_kmh"].mean()) if "speed_kmh" in df else 0.0,
            "players_detected": list(df["player"].unique()) if "player" in df else [],
            "strokes_breakdown": df["stroke"].value_counts().to_dict() if "stroke" in df else {}
        }
        return summary
