import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import scipy.stats as stats

from analytics_engine import AnalyticsEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "output", "tennis_match_analytics.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ARTIFACT_DIR = "/Users/raj/.gemini/antigravity/brain/7770b4a3-5797-4dd0-b8fc-a3bd57e9d416"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_heatmap_image(player_name, landing_coords, output_path):
    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")

    # Court Background (Royal Blue)
    court_rect = patches.Rectangle((0.08, 0.08), 0.84, 0.84, linewidth=0, facecolor="#1e3a8a")
    ax.add_patch(court_rect)

    # Outer Boundary (White)
    bound_rect = patches.Rectangle((0.08, 0.08), 0.84, 0.84, linewidth=3, edgecolor="#ffffff", facecolor="none")
    ax.add_patch(bound_rect)

    # Net Line (Vertical Center)
    ax.plot([0.5, 0.5], [0.06, 0.94], color="#cbd5e1", linewidth=4, zorder=5)

    # Singles Lines
    singles_offset = 0.84 * 0.12
    ax.plot([0.08, 0.92], [0.08 + singles_offset, 0.08 + singles_offset], color="#ffffff", linewidth=2)
    ax.plot([0.08, 0.92], [0.92 - singles_offset, 0.92 - singles_offset], color="#ffffff", linewidth=2)

    # Service Lines
    service_offset = 0.84 * 0.22
    ax.plot([0.08 + service_offset, 0.08 + service_offset], [0.08 + singles_offset, 0.92 - singles_offset], color="#ffffff", linewidth=2)
    ax.plot([0.92 - service_offset, 0.92 - service_offset], [0.08 + singles_offset, 0.92 - singles_offset], color="#ffffff", linewidth=2)

    # Center Service Line
    ax.plot([0.08 + service_offset, 0.92 - service_offset], [0.5, 0.5], color="#ffffff", linewidth=2)

    # Baseline Ticks
    ax.plot([0.08, 0.10], [0.5, 0.5], color="#ffffff", linewidth=2)
    ax.plot([0.90, 0.92], [0.5, 0.5], color="#ffffff", linewidth=2)

    xs = [pt["x"] for pt in landing_coords if pt and "x" in pt]
    ys = [pt["y"] for pt in landing_coords if pt and "y" in pt]

    court_xs = [0.08 + x * 0.84 for x in xs]
    court_ys = [0.08 + y * 0.84 for y in ys]

    # Gaussian KDE Heat Density Overlay
    if len(xs) > 3:
        try:
            k_x, k_y = np.mgrid[0.08:0.92:150j, 0.08:0.92:150j]
            positions = np.vstack([k_x.ravel(), k_y.ravel()])
            values = np.vstack([court_xs, court_ys])
            kernel = stats.gaussian_kde(values, bw_method=0.3)
            f = np.reshape(kernel(positions).T, k_x.shape)
            ax.contourf(k_x, k_y, f, levels=15, cmap="inferno", alpha=0.55, zorder=2)
        except Exception as e:
            print(f"KDE calculation note: {e}")

    # Scatter Neon Tennis Balls
    ax.scatter(court_xs, court_ys, c="#facc15", edgecolors="#000000", s=65, linewidths=1.2, zorder=10, label=f"Ball Landings ({len(xs)})")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    plt.title(f"2D Tennis Court Heatmap - {player_name.upper()} ({len(xs)} Landing Spots)", color="#f8fafc", fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="#0f172a")
    plt.close()
    print(f"✅ Generated court heatmap: {output_path}")

def run_standalone_analytics():
    print("=" * 60)
    print("🎾 DECOUPLED TENNIS AI MATCH ANALYTICS PIPELINE")
    print("=" * 60)

    if not os.path.exists(JSON_PATH):
        print(f"❌ Error: {JSON_PATH} not found!")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        events = json.load(f)

    print(f"📁 Loaded total match events: {len(events)}")

    engine = AnalyticsEngine()
    engine.records = events

    analytics_p1 = engine.compute_player_analytics("Player 1")
    analytics_p2 = engine.compute_player_analytics("Player 2")

    print("\n" + "-" * 60)
    print("📊 PLAYER 1 (NEAR) TELEMETRY SUMMARY")
    print("-" * 60)
    print(f" Total Shots Played    : {analytics_p1['total_shots']}")
    print(f" Total Distance Covered: {analytics_p1['distance_feet']} ft ({analytics_p1['distance_meters']} m)")
    print(f" Spin Breakdown       : Flat {analytics_p1['spin_distribution']['flat_pct']}% | Topspin {analytics_p1['spin_distribution']['topspin_pct']}% | Slice {analytics_p1['spin_distribution']['slice_pct']}%")
    print(f" Ball Speeds           : Avg {analytics_p1['ball_speed']['avg_mph']} MPH | Max {analytics_p1['ball_speed']['max_mph']} MPH")
    print(f" Serves (In Pct)       : Ad {analytics_p1['serves']['ad_serves_in_pct']}% | Deuce {analytics_p1['serves']['deuce_serves_in_pct']}%")
    print(f" Groundstrokes (In)    : Forehand {analytics_p1['groundstrokes']['forehands_in_pct']}% | Backhand {analytics_p1['groundstrokes']['backhands_in_pct']}%")

    print("\n" + "-" * 60)
    print("📊 PLAYER 2 (OPPONENT) TELEMETRY SUMMARY")
    print("-" * 60)
    print(f" Total Shots Played    : {analytics_p2['total_shots']}")
    print(f" Total Distance Covered: {analytics_p2['distance_feet']} ft ({analytics_p2['distance_meters']} m)")
    print(f" Spin Breakdown       : Flat {analytics_p2['spin_distribution']['flat_pct']}% | Topspin {analytics_p2['spin_distribution']['topspin_pct']}% | Slice {analytics_p2['spin_distribution']['slice_pct']}%")
    print(f" Ball Speeds           : Avg {analytics_p2['ball_speed']['avg_mph']} MPH | Max {analytics_p2['ball_speed']['max_mph']} MPH")
    print(f" Serves (In Pct)       : Ad {analytics_p2['serves']['ad_serves_in_pct']}% | Deuce {analytics_p2['serves']['deuce_serves_in_pct']}%")
    print(f" Groundstrokes (In)    : Forehand {analytics_p2['groundstrokes']['forehands_in_pct']}% | Backhand {analytics_p2['groundstrokes']['backhands_in_pct']}%")

    # Generate Heatmap Images
    img_p1_path = os.path.join(OUTPUT_DIR, "heatmap_player1_near.png")
    img_p2_path = os.path.join(OUTPUT_DIR, "heatmap_player2_far.png")

    generate_heatmap_image("Player 1 (Near)", analytics_p1["heatmap"]["landing_coords"], img_p1_path)
    generate_heatmap_image("Player 2 (Opponent)", analytics_p2["heatmap"]["landing_coords"], img_p2_path)

if __name__ == "__main__":
    run_standalone_analytics()
