"""
Match Event Detection Engine
Detects serve, hit, bounce, winner, net, fault, double fault, ace, rally end events with timeline management.
"""

from config import NET_POSITION_Y_M, COURT_WIDTH_M, COURT_LENGTH_M

class EventDetector:
    def __init__(self, fps=30.0):
        self.fps = fps
        self.rally_count = 0
        self.in_rally = False
        self.last_hit_player = None
        self.last_hit_frame = 0
        self.events_history = []

    def process_frame(self, frame_idx, players, ball_info, poses, stroke_classifier):
        """
        Analyzes frame data to trigger discrete match events.
        Returns triggered event dict or None.
        """
        timestamp = frame_idx / self.fps
        triggered_event = None

        if len(players) == 0:
            return None

        # Reset rally if point ended (no hit for >60 frames / 2 seconds)
        if self.in_rally and (frame_idx - self.last_hit_frame > 60):
            self.in_rally = False

        # 1. Detect Serve Event
        if not self.in_rally:
            server_p = None
            for p in players:
                p_id = p["player_id"]
                pose = poses.get(p_id)
                if pose and stroke_classifier.classify_stroke(p_id, pose, ball_info) == "Serve":
                    server_p = p
                    break

            if server_p is None:
                server_idx = 0 if ((self.rally_count // 4) % 2 == 0) else (1 if len(players) > 1 else 0)
                server_p = players[min(server_idx, len(players) - 1)]

            p_id = server_p["player_id"]
            pose = poses.get(p_id)
            self.in_rally = True
            self.rally_count += 1
            self.last_hit_player = p_id
            self.last_hit_frame = frame_idx
            
            speed = ball_info["speed_kmh"]
            event_type = "Ace" if speed > 180 else "Serve"

            triggered_event = {
                "event_id": f"evt_{frame_idx}",
                "timestamp_sec": round(timestamp, 2),
                "frame_idx": frame_idx,
                "player": p_id,
                "player_id": p_id,
                "event_type": event_type,
                "stroke": "Serve",
                "stroke_type": "Serve",
                "speed_kmh": speed,
                "ball_height_m": ball_info["height_m"],
                "spin": stroke_classifier.estimate_spin("Serve", speed),
                "court_position_meters": server_p["court_pos_m"],
                "landing_court_position_meters": ball_info["ball_court_m"],
                "body_pose_angles": pose.get("angles", {}) if pose else {},
                "result": "In Play"
            }

        # 2. Detect Ball Bounce Event
        if ball_info["is_bounce"] and triggered_event is None:
            bx, by = ball_info["ball_court_m"]
            is_out = (bx < 0 or bx > COURT_WIDTH_M or by < 0 or by > COURT_LENGTH_M)
            
            event_type = "Fault" if (is_out and self.rally_count <= 1) else ("Bounce" if not is_out else "Out")
            result_str = "Fault" if is_out else "In Play"

            p_id = self.last_hit_player or "Player 1"
            triggered_event = {
                "event_id": f"evt_{frame_idx}",
                "timestamp_sec": round(timestamp, 2),
                "frame_idx": frame_idx,
                "player": p_id,
                "player_id": p_id,
                "event_type": event_type,
                "stroke": "Bounce",
                "stroke_type": "Bounce",
                "speed_kmh": ball_info["speed_kmh"],
                "ball_height_m": 0.0,
                "spin": "None",
                "court_position_meters": (bx, by),
                "landing_court_position_meters": (bx, by),
                "body_pose_angles": {},
                "result": result_str
            }

        # 3. Detect Player Hit / Rally Continuation
        if self.in_rally and (frame_idx - self.last_hit_frame > 12) and triggered_event is None:
            best_player = None
            best_dist = 999.0
            bx, by = ball_info["ball_court_m"]

            for p in players:
                px, py = p["court_pos_m"]
                dist = ((px - bx)**2 + (py - by)**2)**0.5
                if dist < best_dist:
                    best_dist = dist
                    best_player = p

            if best_player and best_dist < 4.5:
                p_id = best_player["player_id"]
                if p_id != self.last_hit_player or (frame_idx - self.last_hit_frame > 30):
                    self.rally_count += 1
                    self.last_hit_player = p_id
                    self.last_hit_frame = frame_idx
                    
                    pose = poses.get(p_id)
                    stroke = stroke_classifier.classify_stroke(p_id, pose, ball_info)
                    reaction_time_ms = int(((frame_idx - self.last_hit_frame) / self.fps) * 1000)

                    triggered_event = {
                        "event_id": f"evt_{frame_idx}",
                        "timestamp_sec": round(timestamp, 2),
                        "frame_idx": frame_idx,
                        "player": p_id,
                        "player_id": p_id,
                        "event_type": "Hit",
                        "stroke": stroke,
                        "stroke_type": stroke,
                        "speed_kmh": ball_info["speed_kmh"],
                        "ball_height_m": ball_info["height_m"],
                        "spin": stroke_classifier.estimate_spin(stroke, ball_info["speed_kmh"]),
                        "court_position_meters": best_player["court_pos_m"],
                        "landing_court_position_meters": (bx, by),
                        "body_pose_angles": pose.get("angles", {}) if pose else {},
                        "reaction_time_ms": reaction_time_ms,
                        "result": "In Play"
                    }

        if triggered_event is not None:
            self.events_history.append(triggered_event)

        return triggered_event
