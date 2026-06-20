"""
03_basic_plotting.py
====================
Author: Emmanuel Oyekanlu — Principal Data Engineer

PURPOSE:
    Demonstrate how to create publication-quality static maps using GeoPandas'
    built-in .plot() method combined with matplotlib customization. We produce
    a multi-panel figure that could appear in an agricultural operations report
    or an AGV fleet audit deck.

REAL-WORLD CONTEXT:
    Static maps are essential for:
      - PDF reports delivered to farm managers or logistics supervisors
      - Slide deck visuals for stakeholder presentations
      - Automated monitoring emails (attach PNG map of daily AGV coverage)
      - CI/CD artifacts — generate a map PNG on every pipeline run and post
        it to Slack/Teams as a data quality visual

    GeoPandas' .plot() returns a standard matplotlib Axes object, so every
    matplotlib trick you already know (annotations, legends, titles, color maps,
    figure sizing) applies directly.

OUTPUTS:
    output_map.png — a 4-panel figure saved to the same directory as this script

USAGE:
    python 03_basic_plotting.py
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")          # Non-interactive backend — works on servers with no display
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import geopandas as gpd
from shapely.geometry import Point

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_PATH = os.path.join(SCRIPT_DIR, "data", "sample_fields.geojson")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "output_map.png")

# Load in WGS84 for geographic display, then also prepare a UTM version
gdf_wgs84 = gpd.read_file(GEOJSON_PATH)
gdf_utm = gdf_wgs84.to_crs("EPSG:32610")
gdf_utm['area_ha_computed'] = gdf_utm.geometry.area / 10_000

# Create synthetic AGV track points in the same region for Panel 4
np.random.seed(42)
n_points = 40
# Scatter points around the centroid of the field dataset
center_lon, center_lat = -121.628, 36.617
agv_lons = center_lon + np.random.uniform(-0.025, 0.025, n_points)
agv_lats = center_lat + np.random.uniform(-0.015, 0.015, n_points)
agv_speeds = np.random.uniform(1.5, 5.5, n_points)

agv_gdf = gpd.GeoDataFrame(
    {"speed_kmh": agv_speeds},
    geometry=[Point(lo, la) for lo, la in zip(agv_lons, agv_lats)],
    crs="EPSG:4326",
)

# ---------------------------------------------------------------------------
# Color setup for crop types (categorical)
# ---------------------------------------------------------------------------
# Assign a consistent color to each unique crop type
crop_types = gdf_wgs84['crop_type'].unique()
crop_colors = {
    "lettuce":    "#4CAF50",   # green — leafy crop
    "strawberry": "#E91E63",   # pink/red — berry
    "broccoli":   "#1B5E20",   # dark green — brassica
    "spinach":    "#76FF03",   # lime green — leafy
    "celery":     "#AED581",   # light green — stalk crop
}
# Map each row to its color
gdf_wgs84['plot_color'] = gdf_wgs84['crop_type'].map(crop_colors)

# ---------------------------------------------------------------------------
# Build the 2×2 multi-panel figure
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(
    nrows=2, ncols=2,
    figsize=(16, 13),
    facecolor='#F8F9FA',
)
fig.suptitle(
    "Salinas Valley Agricultural Fields — Geospatial Analysis\n"
    "GeoPandas Fundamentals Demo | Emmanuel Oyekanlu",
    fontsize=14,
    fontweight='bold',
    y=0.98,
    color='#1A237E',
)

# ─── PANEL 1 (top-left): Color-coded by crop type ─────────────────────────
ax1 = axes[0, 0]
ax1.set_facecolor('#E3F2FD')   # light blue background to suggest land/sky

# Plot each crop type separately so we can build a clean legend
for crop, color in crop_colors.items():
    subset = gdf_wgs84[gdf_wgs84['crop_type'] == crop]
    if len(subset) > 0:
        subset.plot(ax=ax1, color=color, edgecolor='#333333',
                    linewidth=1.2, alpha=0.85, label=crop.capitalize())

# Add field ID labels at each polygon centroid
for _, row in gdf_wgs84.iterrows():
    cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
    ax1.annotate(
        row['field_id'],
        xy=(cx, cy),
        ha='center', va='center',
        fontsize=7.5, fontweight='bold', color='white',
        bbox=dict(boxstyle='round,pad=0.2', facecolor='#1A237E',
                  alpha=0.6, edgecolor='none'),
    )

ax1.set_title("Panel 1: Fields by Crop Type", fontsize=11, fontweight='bold', pad=8)
ax1.set_xlabel("Longitude (°)", fontsize=9)
ax1.set_ylabel("Latitude (°)", fontsize=9)
ax1.legend(
    title="Crop Type",
    loc='upper right',
    fontsize=8,
    title_fontsize=8.5,
    framealpha=0.9,
)
ax1.tick_params(labelsize=8)
ax1.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)

# ─── PANEL 2 (top-right): Choropleth by area_ha ───────────────────────────
ax2 = axes[0, 1]
ax2.set_facecolor('#F1F8E9')

# .plot() with `column=` creates a choropleth. `legend=True` adds a colorbar.
# We use the UTM GeoDataFrame here so geometries are in meters, but we'll
# convert x-tick labels back to approximate degrees for readability.
plot2 = gdf_utm.plot(
    ax=ax2,
    column='area_ha_computed',
    cmap='YlOrRd',             # Yellow → Orange → Red (light = small, dark = large)
    edgecolor='#555555',
    linewidth=1.0,
    legend=True,
    legend_kwds={
        'label': 'Area (hectares)',
        'orientation': 'vertical',
        'shrink': 0.7,
        'pad': 0.02,
    },
)

# Annotate with area value
for _, row in gdf_utm.iterrows():
    cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
    ax2.annotate(
        f"{row['area_ha_computed']:.1f} ha",
        xy=(cx, cy),
        ha='center', va='center',
        fontsize=7.5, color='#1A237E', fontweight='bold',
    )

ax2.set_title("Panel 2: Field Area Choropleth (ha)", fontsize=11, fontweight='bold', pad=8)
ax2.set_xlabel("Easting (m, UTM Zone 10N)", fontsize=9)
ax2.set_ylabel("Northing (m, UTM Zone 10N)", fontsize=9)
ax2.tick_params(labelsize=7, labelrotation=30)
ax2.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)

# ─── PANEL 3 (bottom-left): Field boundaries + 50m buffer overlay ─────────
ax3 = axes[1, 0]
ax3.set_facecolor('#FFF8E1')

# Buffer each field by 50 meters to show a proximity zone
gdf_utm['buffer_50m'] = gdf_utm.geometry.buffer(50)

# Plot buffers first (underneath), then original polygons on top
buffer_series = gpd.GeoSeries(gdf_utm['buffer_50m'], crs="EPSG:32610")
buffer_series.plot(
    ax=ax3,
    color='#FFF176',       # pale yellow
    edgecolor='#F9A825',
    linewidth=1.0,
    alpha=0.5,
    label='50 m buffer zone',
)

gdf_utm.plot(
    ax=ax3,
    color='#66BB6A',
    edgecolor='#2E7D32',
    linewidth=1.5,
    alpha=0.8,
    label='Field boundary',
)

# Plot centroids as markers
centroids = gdf_utm.geometry.centroid
centroids.plot(
    ax=ax3,
    color='#B71C1C',
    markersize=40,
    marker='*',
    label='Field centroid',
    zorder=5,
)

ax3.set_title("Panel 3: Field Boundaries + 50 m Buffer Zones", fontsize=11,
              fontweight='bold', pad=8)
ax3.set_xlabel("Easting (m)", fontsize=9)
ax3.set_ylabel("Northing (m)", fontsize=9)
ax3.legend(loc='upper right', fontsize=8, framealpha=0.9)
ax3.tick_params(labelsize=7, labelrotation=30)
ax3.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)

# ─── PANEL 4 (bottom-right): AGV track + fields overlay ───────────────────
ax4 = axes[1, 1]
ax4.set_facecolor('#E8EAF6')

# Plot field outlines in WGS84 as reference layer
gdf_wgs84.plot(
    ax=ax4,
    color='none',         # transparent fill — just show the outline
    edgecolor='#1565C0',
    linewidth=2.0,
    label='Field boundary',
)

# Plot AGV positions colored by speed (continuous colormap)
speed_norm = mcolors.Normalize(vmin=agv_speeds.min(), vmax=agv_speeds.max())
speed_cmap = cm.plasma

scatter = ax4.scatter(
    agv_gdf.geometry.x,
    agv_gdf.geometry.y,
    c=agv_speeds,
    cmap=speed_cmap,
    norm=speed_norm,
    s=60,
    alpha=0.85,
    edgecolors='white',
    linewidths=0.5,
    zorder=5,
    label='AGV positions',
)

# Add colorbar for speed
cbar = fig.colorbar(scatter, ax=ax4, shrink=0.65, pad=0.02)
cbar.set_label('AGV Speed (km/h)', fontsize=8)
cbar.ax.tick_params(labelsize=7)

# Annotate field IDs
for _, row in gdf_wgs84.iterrows():
    cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
    ax4.text(cx, cy, row['field_id'],
             ha='center', va='center', fontsize=7,
             color='#1A237E', fontweight='bold')

ax4.set_title("Panel 4: AGV Track Over Field Layout\n(color = speed km/h)",
              fontsize=11, fontweight='bold', pad=8)
ax4.set_xlabel("Longitude (°)", fontsize=9)
ax4.set_ylabel("Latitude (°)", fontsize=9)
ax4.tick_params(labelsize=8)
ax4.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)

# ---------------------------------------------------------------------------
# Final layout adjustments and save
# ---------------------------------------------------------------------------
plt.tight_layout(rect=[0, 0, 1, 0.96])

plt.savefig(
    OUTPUT_PATH,
    dpi=150,                # 150 DPI → good quality for reports
    bbox_inches='tight',    # prevent axis labels from being clipped
    facecolor=fig.get_facecolor(),
)
plt.close(fig)

print(f"[SUCCESS] 4-panel map saved to: {OUTPUT_PATH}")
print()
print("Map panels:")
print("  Panel 1 (top-left)    — Categorical color by crop type + field ID labels")
print("  Panel 2 (top-right)   — Choropleth: field area in hectares (YlOrRd)")
print("  Panel 3 (bottom-left) — Field boundaries + 50 m buffer zones + centroids")
print("  Panel 4 (bottom-right)— Synthetic AGV track colored by speed (plasma cmap)")
print()
print("PRODUCTION TIP:")
print("  Set DPI=300 for print-quality output.")
print("  Use matplotlib.use('Agg') when running on headless servers (no display).")
print("  Pipe the figure to an S3 upload or email attachment in your data pipeline.")
