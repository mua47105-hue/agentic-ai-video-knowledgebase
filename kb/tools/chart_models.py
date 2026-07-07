#!/usr/bin/env python3
"""Generate AI video models comparison chart."""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

models = {
    "Runway Gen-4.5": {"quality": 1247, "speed": 75, "cost": 12, "size": 200},
    "Pika 2.5":       {"quality": 1100, "speed": 12, "cost": 8,  "size": 180},
    "Google Veo 3.1": {"quality": 1226, "speed": 25, "cost": 8,  "size": 190},
    "Kling 3.0":      {"quality": 1180, "speed": 40, "cost": 7,  "size": 170},
    "Sora 2 (RIP)":   {"quality": 1206, "speed": 3000, "cost": 20, "size": 160},
}

fig, ax = plt.subplots(figsize=(12, 7))

colors = {"Runway Gen-4.5": "#2563eb", "Pika 2.5": "#ec4899",
          "Google Veo 3.1": "#10b981", "Kling 3.0": "#f59e0b",
          "Sora 2 (RIP)": "#ef4444"}

for name, data in models.items():
    ax.scatter(data["speed"], data["quality"], s=data["size"] * 2,
               c=colors[name], alpha=0.7, edgecolors="black", linewidth=0.5,
               label=name, zorder=5)
    offset_x = 8 if name != "Sora 2 (RIP)" else -8
    va = "bottom" if name != "Pika 2.5" else "top"
    ax.annotate(name, (data["speed"], data["quality"]),
                xytext=(offset_x, 5), textcoords="offset points",
                fontsize=10, fontweight="bold", va=va,
                color=colors[name])

ax.set_xscale("log")
ax.set_xlabel("Generation Speed (seconds per clip) → faster ←", fontsize=11)
ax.set_ylabel("Quality (Artificial Analysis Elo Score)", fontsize=11)
ax.set_title("AI Video Models 2026: Quality vs Speed\nBubble size ≈ entry price", fontsize=14, fontweight="bold")

ax.set_xticks([10, 30, 60, 120, 300, 600, 1800, 3600])
ax.set_xticklabels(["10s", "30s", "1min", "2min", "5min", "10min", "30min", "60min"])

ax.legend(loc="lower left", framealpha=0.9)
ax.grid(True, alpha=0.3)
ax.set_ylim(1050, 1280)

plt.tight_layout()
import pathlib
out = pathlib.Path(__file__).resolve().parent.parent / "wiki" / "charts"
out.mkdir(parents=True, exist_ok=True)
png_path = str(out / "ai-video-models-2026.png")
webp_path = str(out / "ai-video-models-2026.webp")
plt.savefig(png_path, dpi=150)
# Convert to lossless WebP (~68% smaller, mathematically lossless)
from PIL import Image
img = Image.open(png_path)
img.save(webp_path, format="WEBP", lossless=True)
print(f"Chart saved to {png_path}  ({os.path.getsize(png_path)/1024:.0f}K)")
print(f"Lossless WebP: {webp_path}  ({os.path.getsize(webp_path)/1024:.0f}K, {(1-os.path.getsize(webp_path)/os.path.getsize(png_path))*100:.0f}% smaller)")
