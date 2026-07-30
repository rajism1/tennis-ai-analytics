"""
Analytics Engine & Data Storage Module (Module 2)
Stores structured frame & event telemetry and exports JSON, CSV, SQLite DB, and computes player analytics.
"""

import json
import csv
import os
import sqlite3
import pandas as pd
import numpy as np

class AnalyticsEngine:
    def __init__(self, output_dir=None):
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.records = []
        self.db_path = os.path.join(self.output_dir, "tennis_analytics.db")

    def log_event(self, event_data):
        if event_data is None:
            return
        self.records.append(event_data)

    def export_json(self, filename="tennis_match_analytics.json"):
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2)
        print(f"[AnalyticsEngine] Exported {len(self.records)} events to JSON: {filepath}")
        return filepath

    def export_csv(self, filename="tennis_match_analytics.csv"):
        filepath = os.path.join(self.output_dir, filename)
        if len(self.records) == 0:
            cols = ["event_id", "timestamp_sec", "frame_idx", "player", "event_type", "stroke", "speed_kmh", "spin", "result"]
            df = pd.DataFrame(columns=cols)
        else:
            df = pd.DataFrame(self.records)
        df.to_csv(filepath, index=False)
        print(f"[AnalyticsEngine] Exported {len(self.records)} events to CSV: {filepath}")

    def get_match_summary(self):
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

    def compute_player_analytics(self, target_player="Player 1"):
        if len(self.records) == 0:
            return self._empty_analytics_response(target_player)

        df = pd.DataFrame(self.records)
        if len(df) == 0:
            return self._empty_analytics_response(target_player)

        # 1. Separate actual racket strokes from ball bounces
        strokes_df = df[df['stroke'].isin(['Forehand', 'Backhand', 'Serve', 'Volley', 'Slice', 'Drop']) | (df['event_type'] == 'Hit')].copy()
        strokes_df = strokes_df.sort_values('frame_idx')

        # 2. Match Rally Detection & Serve re-labeling (Rally gap threshold = 1.8s)
        match_rallies = []
        curr_rally = 0
        last_t = -10.0

        for idx, row in strokes_df.iterrows():
            t = float(row.get('timestamp_sec', 0.0))
            if t - last_t > 1.8:
                strokes_df.loc[idx, 'stroke'] = 'Serve'
                if curr_rally > 0:
                    match_rallies.append(curr_rally)
                curr_rally = 1
            else:
                curr_rally += 1
            last_t = t

        if curr_rally > 0:
            match_rallies.append(curr_rally)

        longest_rally = max(match_rallies) if len(match_rallies) > 0 else 1
        rallies_gt_5 = [r for r in match_rallies if r >= 5]
        rallies_above_5_pct = round((len(rallies_gt_5) / max(1, len(match_rallies))) * 100, 1) if len(match_rallies) > 0 else 0.0

        # 3. Filter for target_player's actual racket shots
        player_df = strokes_df[strokes_df['player'] == target_player].copy()
        total_shots = len(player_df)

        if total_shots == 0:
            return self._empty_analytics_response(target_player)

        # 4. Movement Distance (Feet & Meters for target_player ONLY)
        raw_player_events = df[df['player'] == target_player]
        total_dist_meters = 0.0
        player_coords = []
        for _, row in raw_player_events.iterrows():
            pt = row.get("court_position_meters", None)
            if pt and isinstance(pt, (list, tuple, np.ndarray)) and len(pt) == 2 and not any(pd.isna(x) for x in pt):
                player_coords.append((float(pt[0]), float(pt[1])))

        for i in range(1, len(player_coords)):
            p1 = np.array(player_coords[i-1])
            p2 = np.array(player_coords[i])
            d = np.linalg.norm(p2 - p1)
            if 0.1 <= d <= 12.0:
                total_dist_meters += d

        total_dist_feet = total_dist_meters * 3.28084

        # 5. Outlier Speed Treatment (25 mph <= speed <= 115 mph)
        player_df['speed_mph'] = player_df['speed_kmh'] * 0.621371
        valid_speeds = player_df[(player_df['speed_mph'] >= 25.0) & (player_df['speed_mph'] <= 115.0)]['speed_mph']

        avg_speed_mph = round(float(valid_speeds.mean()), 1) if len(valid_speeds) > 0 else 0.0
        max_speed_mph = round(float(valid_speeds.max()), 1) if len(valid_speeds) > 0 else 0.0
        avg_speed_kmh = round(avg_speed_mph * 1.60934, 1)
        max_speed_kmh = round(max_speed_mph * 1.60934, 1)

        speed_history = [
            {"frame": int(row.get("frame_idx", 0)), "speed_mph": round(float(row.get("speed_mph", 0)), 1)}
            for _, row in player_df.iterrows()
            if 25.0 <= row.get("speed_mph", 0) <= 115.0
        ]

        # 6. Spin Distribution
        spin_counts = player_df["spin"].value_counts().to_dict() if "spin" in player_df else {}
        flat_cnt = spin_counts.get("Flat", 0)
        topspin_cnt = spin_counts.get("Topspin", 0)
        slice_cnt = spin_counts.get("Backspin", 0) + spin_counts.get("Slice", 0)
        
        flat_pct = round((flat_cnt / total_shots) * 100, 1)
        topspin_pct = round((topspin_cnt / total_shots) * 100, 1)
        slice_pct = round((slice_cnt / total_shots) * 100, 1)

        tot_spin = flat_pct + topspin_pct + slice_pct
        if tot_spin > 0:
            flat_pct = round((flat_pct / tot_spin) * 100, 1)
            topspin_pct = round((topspin_pct / tot_spin) * 100, 1)
            slice_pct = round(100.0 - flat_pct - topspin_pct, 1)

        # 7. Shot Type Distribution
        stroke_counts = player_df["stroke"].value_counts().to_dict() if "stroke" in player_df else {}
        shot_dist = {
            "Forehand": round((stroke_counts.get("Forehand", 0) / total_shots) * 100, 1),
            "Backhand": round((stroke_counts.get("Backhand", 0) / total_shots) * 100, 1),
            "Serve": round((stroke_counts.get("Serve", 0) / total_shots) * 100, 1),
            "Volley": round((stroke_counts.get("Volley", 0) / total_shots) * 100, 1),
            "Slice": round((stroke_counts.get("Slice", 0) / total_shots) * 100, 1)
        }

        # 8. Shots In % and Match Duration Pace
        in_shots = player_df[~player_df["result"].isin(["Out", "Fault"])] if "result" in player_df else player_df
        shots_in_pct = round((len(in_shots) / max(1, total_shots)) * 100, 1)

        match_duration_sec = 342.0
        shots_per_hour = int((total_shots / match_duration_sec) * 3600)

        # 9. Serves (Ad vs Deuce) with Outlier Filtering
        serves_df = player_df[player_df["stroke"] == "Serve"].copy()
        ad_serves, deuce_serves = [], []
        
        for _, row in serves_df.iterrows():
            pos = row.get("landing_court_position_meters", [0, 0])
            if pos and len(pos) == 2:
                if pos[0] < 5.48:
                    ad_serves.append(row)
                else:
                    deuce_serves.append(row)

        ad_df = pd.DataFrame(ad_serves) if len(ad_serves) > 0 else pd.DataFrame()
        deuce_df = pd.DataFrame(deuce_serves) if len(deuce_serves) > 0 else pd.DataFrame()

        ad_serves_in_pct = round((len(ad_df[~ad_df["result"].isin(["Fault", "Out"])]) / max(1, len(ad_df)) * 100), 1) if len(ad_df) > 0 else 0.0
        deuce_serves_in_pct = round((len(deuce_df[~deuce_df["result"].isin(["Fault", "Out"])]) / max(1, len(deuce_df)) * 100), 1) if len(deuce_df) > 0 else 0.0

        ad_valid_spd = ad_df[(ad_df['speed_mph']>=25.0)&(ad_df['speed_mph']<=115.0)]['speed_mph'] if len(ad_df) > 0 and 'speed_mph' in ad_df else pd.Series()
        deuce_valid_spd = deuce_df[(deuce_df['speed_mph']>=25.0)&(deuce_df['speed_mph']<=115.0)]['speed_mph'] if len(deuce_df) > 0 and 'speed_mph' in deuce_df else pd.Series()

        ad_avg_serve_speed_mph = round(float(ad_valid_spd.mean()), 1) if len(ad_valid_spd) > 0 else 0.0
        deuce_avg_serve_speed_mph = round(float(deuce_valid_spd.mean()), 1) if len(deuce_valid_spd) > 0 else 0.0

        # 10. Groundstrokes (Forehand vs Backhand) with Outlier Filtering
        fh_df = player_df[player_df["stroke"] == "Forehand"].copy()
        bh_df = player_df[player_df["stroke"] == "Backhand"].copy()

        fh_in_pct = round((len(fh_df[~fh_df["result"].isin(["Out"])]) / max(1, len(fh_df))) * 100, 1) if len(fh_df) > 0 else 0.0
        bh_in_pct = round((len(bh_df[~bh_df["result"].isin(["Out"])]) / max(1, len(bh_df))) * 100, 1) if len(bh_df) > 0 else 0.0

        fh_valid_spd = fh_df[(fh_df['speed_mph']>=25.0)&(fh_df['speed_mph']<=115.0)]['speed_mph'] if len(fh_df) > 0 else pd.Series()
        bh_valid_spd = bh_df[(bh_df['speed_mph']>=25.0)&(bh_df['speed_mph']<=115.0)]['speed_mph'] if len(bh_df) > 0 else pd.Series()

        fh_avg_speed = round(float(fh_valid_spd.mean()), 1) if len(fh_valid_spd) > 0 else avg_speed_mph
        bh_avg_speed = round(float(bh_valid_spd.mean()), 1) if len(bh_valid_spd) > 0 else avg_speed_mph

        # 11. Heatmap Coordinates & Tactical Insights
        hit_coords = []
        landing_coords = []

        def normalize_m_to_court(mx, my):
            try:
                val_x = float(mx)
                val_y = float(my)
                if val_x < 0 or val_x > 10.97:
                    val_x = abs(val_x) % 10.97
                if val_y < 0 or val_y > 23.77:
                    val_y = abs(val_y) % 23.77
                
                nx = float(np.clip(val_x / 10.97, 0.08, 0.92))
                ny = float(np.clip(val_y / 23.77, 0.08, 0.92))
                return (round(nx, 3), round(ny, 3))
            except (ValueError, TypeError):
                return (0.5, 0.5)

        deep_cnt, mid_cnt = 0, 0
        ad_bounce_cnt, deuce_bounce_cnt = 0, 0
        fh_dtl_cnt, fh_cc_cnt = 0, 0
        wide_serve_cnt, t_serve_cnt = 0, 0

        for _, row in player_df.iterrows():
            pos = row.get("court_position_meters", None)
            land = row.get("landing_court_position_meters", None)
            stroke = str(row.get("stroke", "Hit"))

            pos_valid = isinstance(pos, (list, tuple, np.ndarray)) and len(pos) == 2 and not any(pd.isna(x) for x in pos)
            land_valid = isinstance(land, (list, tuple, np.ndarray)) and len(land) == 2 and not any(pd.isna(x) for x in land)

            if pos_valid:
                c = normalize_m_to_court(pos[0], pos[1])
                hit_coords.append({"x": c[0], "y": c[1], "stroke": stroke})

            if land_valid:
                c = normalize_m_to_court(land[0], land[1])
                landing_coords.append({"x": c[0], "y": c[1], "stroke": stroke})

                if c[0] <= 0.5:
                    ad_bounce_cnt += 1
                else:
                    deuce_bounce_cnt += 1

                if c[1] < 0.35 or c[1] > 0.65:
                    deep_cnt += 1
                else:
                    mid_cnt += 1

                if stroke == "Forehand":
                    if (c[0] <= 0.35 and pos_valid and pos[0] <= 5.48) or (c[0] >= 0.65 and pos_valid and pos[0] > 5.48):
                        fh_dtl_cnt += 1
                    else:
                        fh_cc_cnt += 1

                if stroke == "Serve":
                    if c[0] < 0.25 or c[0] > 0.75:
                        wide_serve_cnt += 1
                    else:
                        t_serve_cnt += 1

        tot_landings = max(1, len(landing_coords))
        deep_pct = round((deep_cnt / tot_landings) * 100)
        mid_pct = 100 - deep_pct

        ad_pct = round((ad_bounce_cnt / tot_landings) * 100)
        deuce_pct = 100 - ad_pct

        tot_fh = max(1, len(fh_df))
        fh_dtl_pct = round((fh_dtl_cnt / tot_fh) * 100) if len(fh_df) > 0 else 0
        fh_cc_pct = 100 - fh_dtl_pct if len(fh_df) > 0 else 0

        tot_serves = max(1, len(serves_df))
        wide_serve_pct = round((wide_serve_cnt / tot_serves) * 100) if len(serves_df) > 0 else 0
        t_serve_pct = 100 - wide_serve_pct if len(serves_df) > 0 else 0

        dominant_zone = f"Ad Court ({ad_pct}%)" if ad_pct > deuce_pct else f"Deuce Court ({deuce_pct}%)"
        target_weakness = f"Deep Ad Corner ({ad_pct}%)" if ad_pct > deuce_pct else f"Deep Deuce Corner ({deuce_pct}%)"

        return {
            "player": target_player,
            "total_shots": total_shots,
            "distance_feet": int(total_dist_feet),
            "distance_meters": round(total_dist_meters, 1),
            "spin_distribution": {
                "flat_pct": flat_pct,
                "topspin_pct": topspin_pct,
                "slice_pct": slice_pct
            },
            "ball_speed": {
                "avg_mph": avg_speed_mph,
                "max_mph": max_speed_mph,
                "avg_kmh": avg_speed_kmh,
                "max_kmh": max_speed_kmh,
                "history": speed_history
            },
            "shot_distribution": shot_dist,
            "overall": {
                "shots_in_pct": shots_in_pct,
                "shots_per_hour": shots_per_hour,
                "longest_rally": longest_rally,
                "rallies_above_5_pct": rallies_above_5_pct
            },
            "serves": {
                "ad_serves_in_pct": ad_serves_in_pct,
                "deuce_serves_in_pct": deuce_serves_in_pct,
                "ad_avg_speed_mph": ad_avg_serve_speed_mph,
                "deuce_avg_speed_mph": deuce_avg_serve_speed_mph
            },
            "groundstrokes": {
                "forehands_in_pct": fh_in_pct,
                "backhands_in_pct": bh_in_pct,
                "avg_forehand_speed_mph": fh_avg_speed,
                "avg_backhand_speed_mph": bh_avg_speed
            },
            "tactical_insights": {
                "dominant_zone": dominant_zone,
                "target_weakness": target_weakness,
                "ball_usage": f"Deep Baseline {deep_pct}%",
                "fh_dtl_pct": fh_dtl_pct,
                "fh_cc_pct": fh_cc_pct,
                "wide_serve_pct": wide_serve_pct,
                "t_serve_pct": t_serve_pct,
                "deep_baseline_pct": deep_pct,
                "mid_court_pct": mid_pct
            },
            "heatmap": {
                "hit_coords": hit_coords,
                "landing_coords": landing_coords
            }
        }

    def _empty_analytics_response(self, player_id):
        return {
            "player": player_id,
            "total_shots": 0,
            "distance_feet": 0,
            "distance_meters": 0.0,
            "spin_distribution": {"flat_pct": 0.0, "topspin_pct": 0.0, "slice_pct": 0.0},
            "ball_speed": {"avg_mph": 0.0, "max_mph": 0.0, "avg_kmh": 0.0, "max_kmh": 0.0, "history": []},
            "shot_distribution": {"Forehand": 0.0, "Serve": 0.0, "Backhand": 0.0, "Volley": 0.0, "Slice": 0.0},
            "overall": {"shots_in_pct": 0.0, "shots_per_hour": 0, "longest_rally": 0, "rallies_above_5_pct": 0.0},
            "serves": {"ad_serves_in_pct": 0.0, "deuce_serves_in_pct": 0.0, "ad_avg_speed_mph": 0.0, "deuce_avg_speed_mph": 0.0},
            "groundstrokes": {"forehands_in_pct": 0.0, "backhands_in_pct": 0.0, "avg_forehand_speed_mph": 0.0, "avg_backhand_speed_mph": 0.0},
            "tactical_insights": {
                "dominant_zone": "-",
                "target_weakness": "-",
                "ball_usage": "-",
                "fh_dtl_pct": 0,
                "fh_cc_pct": 0,
                "wide_serve_pct": 0,
                "t_serve_pct": 0,
                "deep_baseline_pct": 0,
                "mid_court_pct": 0
            },
            "heatmap": {"hit_coords": [], "landing_coords": []}
        }
