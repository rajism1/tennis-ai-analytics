"""
Standalone Telemetry Reporter & Matplotlib Heatmap Renderer (Module 2)
Generates high-resolution 2D court heatmap images and prints markdown summary metrics.
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import scipy.stats as stats

from .engine import AnalyticsEngine

def generate_heatmap_image(player_name, landing_coords, output_path):
    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")

    court_rect = patches.Rectangle((0.08, 0.08), 0.84, 0.84, linewidth=0, facecolor="#1e3a8a")
    ax.add_patch(court_rect)

    bound_rect = patches.Rectangle((0.08, 0.08), 0.84, 0.84, linewidth=3, edgecolor="#ffffff", facecolor="none")
    ax.add_patch(bound_rect)

    ax.plot([0.5, 0.5], [0.06, 0.94], color="#cbd5e1", linewidth=4, zorder=5)

    singles_offset = 0.84 * 0.12
    ax.plot([0.08, 0.92], [0.08 + singles_offset, 0.08 + singles_offset], color="#ffffff", linewidth=2)
    ax.plot([0.08, 0.92], [0.92 - singles_offset, 0.92 - singles_offset], color="#ffffff", linewidth=2)

    service_offset = 0.84 * 0.22
    ax.plot([0.08 + service_offset, 0.08 + service_offset], [0.08 + singles_offset, 0.92 - singles_offset], color="#ffffff", linewidth=2)
    ax.plot([0.92 - service_offset, 0.92 - service_offset], [0.08 + singles_offset, 0.92 - singles_offset], color="#ffffff", linewidth=2)

    ax.plot([0.08 + service_offset, 0.92 - service_offset], [0.5, 0.5], color="#ffffff", linewidth=2)

    ax.plot([0.08, 0.10], [0.5, 0.5], color="#ffffff", linewidth=2)
    ax.plot([0.90, 0.92], [0.5, 0.5], color="#ffffff", linewidth=2)

    xs = [pt["x"] for pt in landing_coords if pt and "x" in pt]
    ys = [pt["y"] for pt in landing_coords if pt and "y" in pt]

    court_xs = [0.08 + x * 0.84 for x in xs]
    court_ys = [0.08 + y * 0.84 for y in ys]

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

    ax.scatter(court_xs, court_ys, c="#facc15", edgecolors="#000000", s=65, linewidths=1.2, zorder=10, label=f"Ball Landings ({len(xs)})")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    plt.title(f"2D Tennis Court Heatmap - {player_name.upper()} ({len(xs)} Landing Spots)", color="#f8fafc", fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="#0f172a")
    plt.close()
    print(f"✅ Generated court heatmap: {output_path}")

def run_standalone_reporter(json_path, output_dir=None):
    if output_dir is None:
        output_dir = os.path.dirname(json_path)

    print("=" * 60)
    print("🎾 STANDALONE TENNIS AI TELEMETRY REPORTER")
    print("=" * 60)

    if not os.path.exists(json_path):
        print(f"❌ Error: {json_path} not found!")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    print(f"📁 Loaded total match events: {len(events)}")

    engine = AnalyticsEngine(output_dir=output_dir)
    engine.records = events

    p1 = engine.compute_player_analytics("Player 1")
    p2 = engine.compute_player_analytics("Player 2")

    print("\n" + "-" * 60)
    print("📊 PLAYER 1 (NEAR) TELEMETRY SUMMARY")
    print("-" * 60)
    print(f" Total Shots Played    : {p1['total_shots']}")
    print(f" Total Distance Covered: {p1['distance_feet']} ft ({p1['distance_meters']} m)")
    print(f" Spin Breakdown       : Flat {p1['spin_distribution']['flat_pct']}% | Topspin {p1['spin_distribution']['topspin_pct']}% | Slice {p1['spin_distribution']['slice_pct']}%")
    print(f" Ball Speeds           : Avg {p1['ball_speed']['avg_mph']} MPH | Max {p1['ball_speed']['max_mph']} MPH")

    print("\n" + "-" * 60)
    print("📊 PLAYER 2 (OPPONENT) TELEMETRY SUMMARY")
    print("-" * 60)
    print(f" Total Shots Played    : {p2['total_shots']}")
    print(f" Total Distance Covered: {p2['distance_feet']} ft ({p2['distance_meters']} m)")
    print(f" Spin Breakdown       : Flat {p2['spin_distribution']['flat_pct']}% | Topspin {p2['spin_distribution']['topspin_pct']}% | Slice {p2['spin_distribution']['slice_pct']}%")
    print(f" Ball Speeds           : Avg {p2['ball_speed']['avg_mph']} MPH | Max {p2['ball_speed']['max_mph']} MPH")

    img_p1_path = os.path.join(output_dir, "heatmap_player1_near.png")
    img_p2_path = os.path.join(output_dir, "heatmap_player2_far.png")

    generate_heatmap_image("Player 1 (Near)", p1["heatmap"]["landing_coords"], img_p1_path)
    generate_heatmap_image("Player 2 (Opponent)", p2["heatmap"]["landing_coords"], img_p2_path)
