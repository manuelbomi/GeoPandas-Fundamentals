"""
02_geodataframe_operations.py
==============================
Author: Emmanuel Oyekanlu — Principal Data Engineer

PURPOSE:
    Demonstrate how to create GeoDataFrames programmatically from Shapely
    geometries and Python dictionaries, set and verify CRS, reproject between
    coordinate systems, and perform spatial filtering operations.

REAL-WORLD CONTEXT:
    In precision agriculture and AGV data pipelines, you frequently need to
    BUILD GeoDataFrames from scratch — not just read from files. For example:
      - Convert AGV GPS position logs (lat/lon lists) into a spatial layer
      - Construct field boundary polygons from digitized corner points
      - Build zone polygons programmatically from warehouse layout specs
      - Create point layers from IoT sensor locations stored in a database

    This script covers those construction patterns plus the critical skill of
    CRS management and reprojection.

USAGE:
    python 02_geodataframe_operations.py
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, box
from shapely import wkt


def print_section(title: str) -> None:
    """Print a formatted section header."""
    width = 65
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


# ---------------------------------------------------------------------------
# SECTION 1: Creating a GeoDataFrame from Shapely Polygons + a dict
# ---------------------------------------------------------------------------
print_section("SECTION 1: Building a GeoDataFrame from Scratch")

# Scenario: You have digitized 4 agricultural field polygons by clicking
# corners in a CAD or GIS tool. The corners were recorded in WGS84
# (lon/lat degrees). Now you want to bring them into a GeoPandas workflow.

# Step 1: Define Shapely Polygon objects from corner coordinate lists.
# Note: Shapely Polygon expects (x, y) = (longitude, latitude) for WGS84.
# List coordinates in order (counter-clockwise for exterior rings).

field_polygons = {
    "FLD-A": Polygon([
        (-121.5900, 36.5900),
        (-121.5830, 36.5900),
        (-121.5830, 36.5960),
        (-121.5900, 36.5960),
        (-121.5900, 36.5900),   # close the ring by repeating the first point
    ]),
    "FLD-B": Polygon([
        (-121.5820, 36.5900),
        (-121.5750, 36.5900),
        (-121.5750, 36.5950),
        (-121.5820, 36.5950),
        (-121.5820, 36.5900),
    ]),
    "FLD-C": Polygon([
        (-121.5900, 36.5840),
        (-121.5800, 36.5840),
        (-121.5800, 36.5895),
        (-121.5900, 36.5895),
        (-121.5900, 36.5840),
    ]),
    "FLD-D": Polygon([
        (-121.5790, 36.5840),
        (-121.5710, 36.5840),
        (-121.5710, 36.5895),
        (-121.5790, 36.5895),
        (-121.5790, 36.5840),
    ]),
}

# Step 2: Build a regular Python dict with tabular attributes.
# This mirrors what you might SELECT from a database or receive from an API.
attribute_data = {
    "field_id":     list(field_polygons.keys()),
    "crop_type":    ["alfalfa", "alfalfa", "wheat", "corn"],
    "area_ha":      [9.8, 7.2, 14.1, 11.6],   # reported area; we'll recalculate
    "irrigated":    [True, True, False, True],
    "soil_ph":      [6.8, 7.1, 6.5, 7.3],
    "geometry":     list(field_polygons.values()),  # Shapely Polygon objects
}

# Step 3: Instantiate the GeoDataFrame.
# The `geometry` kwarg tells GeoPandas which column holds the geometry objects.
# The `crs` kwarg sets the Coordinate Reference System immediately.
# EPSG:4326 = WGS84, the GPS/lat-lon system.
gdf = gpd.GeoDataFrame(attribute_data, geometry="geometry", crs="EPSG:4326")

print("Created GeoDataFrame from Shapely Polygon objects:")
print(gdf[['field_id', 'crop_type', 'area_ha', 'irrigated', 'soil_ph']].to_string())
print(f"\nCRS: {gdf.crs}")
print(f"Type: {type(gdf)}")

# ---------------------------------------------------------------------------
# SECTION 2: Creating a GeoDataFrame from GPS Point Logs
# ---------------------------------------------------------------------------
print_section("SECTION 2: GeoDataFrame from GPS Point Data (AGV Log)")

# Scenario: An AGV logged its position 10 times during a traversal of
# a warehouse yard. The log is a list of (lat, lon, timestamp) tuples —
# the format your IoT platform delivers. We convert to a GeoDataFrame.

# Note: GPS gives (lat, lon) but Shapely/GeoPandas expects (lon, lat) = (x, y).
# This is a VERY common source of bugs. Always swap if your source gives (lat, lon).

agv_log = [
    # (latitude, longitude, speed_kmh, battery_pct)
    (36.5920, -121.5880, 3.2, 92),
    (36.5922, -121.5875, 3.5, 91),
    (36.5924, -121.5870, 3.4, 91),
    (36.5926, -121.5865, 3.6, 90),
    (36.5928, -121.5860, 2.8, 90),
    (36.5930, -121.5855, 3.1, 89),
    (36.5932, -121.5850, 3.3, 89),
    (36.5934, -121.5845, 3.0, 88),
    (36.5936, -121.5840, 2.9, 88),
    (36.5938, -121.5835, 3.2, 87),
]

# Convert to GeoDataFrame: swap lat/lon → lon/lat for Point(x, y)
agv_gdf = gpd.GeoDataFrame(
    {
        "latitude":    [r[0] for r in agv_log],
        "longitude":   [r[1] for r in agv_log],
        "speed_kmh":   [r[2] for r in agv_log],
        "battery_pct": [r[3] for r in agv_log],
        "geometry":    [Point(r[1], r[0]) for r in agv_log],  # (lon, lat) → (x, y)
    },
    geometry="geometry",
    crs="EPSG:4326",
)

print("AGV position log as GeoDataFrame (first 5 rows):")
print(agv_gdf[['latitude', 'longitude', 'speed_kmh', 'battery_pct']].head())
print(f"\nGeometry type: {agv_gdf.geom_type.unique()}")

# ---------------------------------------------------------------------------
# SECTION 3: Reprojecting — WGS84 → UTM Zone 10N
# ---------------------------------------------------------------------------
print_section("SECTION 3: Reprojecting CRS (WGS84 → UTM Zone 10N)")

# WHY REPROJECT?
# In WGS84 (EPSG:4326), coordinates are in DEGREES. This means:
#   - area calculations give you square-DEGREES (meaningless for farmers)
#   - distance calculations give you degree-distances (also meaningless)
#
# For California (roughly longitude -114° to -124°, latitude 32° to 42°),
# UTM Zone 10N (EPSG:32610) is the appropriate projected system:
#   - X axis = Easting in METERS from zone's central meridian
#   - Y axis = Northing in METERS from the equator
#   - 1 unit = 1 meter → area in m², distance in m

# .to_crs() returns a NEW GeoDataFrame; it does NOT modify in-place.
gdf_utm = gdf.to_crs("EPSG:32610")

print(f"Original CRS:   {gdf.crs.name}  (EPSG:{gdf.crs.to_epsg()})")
print(f"Reprojected CRS: {gdf_utm.crs.name}  (EPSG:{gdf_utm.crs.to_epsg()})")
print()

# Compare coordinate values before and after reprojection
print("Coordinate comparison — first field centroid:")
centroid_wgs84 = gdf.geometry.iloc[0].centroid
centroid_utm   = gdf_utm.geometry.iloc[0].centroid
print(f"  WGS84:  lon={centroid_wgs84.x:.6f}°,  lat={centroid_wgs84.y:.6f}°")
print(f"  UTM 10N: easting={centroid_utm.x:.2f} m,  northing={centroid_utm.y:.2f} m")

# ---------------------------------------------------------------------------
# SECTION 4: Computing Area CORRECTLY in the Projected CRS
# ---------------------------------------------------------------------------
print_section("SECTION 4: Area Calculation — Wrong CRS vs Correct CRS")

print(f"{'Field':>8} {'area_ha (reported)':>20} {'Area in WGS84 (deg²)':>22} {'Area in UTM (m²)':>18} {'Area in ha (UTM)':>18}")
print("-" * 92)

for i, row in gdf.iterrows():
    reported_ha = row['area_ha']
    area_wgs84  = row.geometry.area         # degrees² — meaningless
    area_utm_m2 = gdf_utm.geometry.iloc[i].area   # meters²  — correct
    area_utm_ha = area_utm_m2 / 10_000      # 1 ha = 10,000 m²

    print(f"{row['field_id']:>8} "
          f"{reported_ha:>20.2f} "
          f"{area_wgs84:>22.8f} "
          f"{area_utm_m2:>18.2f} "
          f"{area_utm_ha:>18.4f}")

print()
print("LESSON: The WGS84 'area' numbers are in square-degrees — they have NO")
print("physical meaning. Only the UTM (meters²) column gives real-world area.")
print("The small differences from the 'reported' column are because the reported")
print("values use a reference dataset while ours are computed from the geometry.")

# Add the correctly-computed hectare area as a new column
gdf_utm['area_ha_computed'] = gdf_utm.geometry.area / 10_000
print(f"\nAdded 'area_ha_computed' column to UTM GeoDataFrame.")

# ---------------------------------------------------------------------------
# SECTION 5: Spatial Filtering — Attribute-Based
# ---------------------------------------------------------------------------
print_section("SECTION 5: Filtering Rows — Attribute-Based")

# Attribute filtering works exactly like pandas boolean indexing.
# No special spatial methods needed for attribute conditions.

# Filter: only irrigated fields
irrigated_gdf = gdf_utm[gdf_utm['irrigated'] == True].copy()
print(f"All fields:       {len(gdf_utm)}")
print(f"Irrigated only:   {len(irrigated_gdf)}")
print(irrigated_gdf[['field_id', 'crop_type', 'irrigated']].to_string())

# Filter: fields larger than 10 ha (using computed area)
large_fields = gdf_utm[gdf_utm['area_ha_computed'] > 10.0].copy()
print(f"\nFields > 10 ha: {len(large_fields)}")
print(large_fields[['field_id', 'crop_type', 'area_ha_computed']].to_string())

# ---------------------------------------------------------------------------
# SECTION 6: Spatial Filtering — Geometry-Based (Bounding Box)
# ---------------------------------------------------------------------------
print_section("SECTION 6: Spatial Filtering — Bounding Box (cx indexer)")

# The .cx[] indexer (coordinate indexer) filters by spatial extent.
# Syntax: gdf.cx[minx:maxx, miny:maxy]
# This is useful for cropping a large national dataset to a study area.

# Define a bounding box that covers only the western half of our fields
# (using original WGS84 coordinates for clarity)
west_bbox_minlon = -121.5920
west_bbox_maxlon = -121.5800
west_bbox_minlat = 36.5830
west_bbox_maxlat = 36.5970

# Apply the cx[] indexer (works in the GeoDataFrame's native CRS)
western_fields = gdf.cx[west_bbox_minlon:west_bbox_maxlon,
                         west_bbox_minlat:west_bbox_maxlat]

print(f"Bounding box filter: lon [{west_bbox_minlon}, {west_bbox_maxlon}], "
      f"lat [{west_bbox_minlat}, {west_bbox_maxlat}]")
print(f"Fields in bbox: {len(western_fields)} / {len(gdf)}")
print(western_fields[['field_id', 'crop_type']].to_string())

# ---------------------------------------------------------------------------
# SECTION 7: Spatial Join — Point-in-Polygon
# ---------------------------------------------------------------------------
print_section("SECTION 7: Spatial Join — Which AGV Positions Are in Which Field?")

# Spatial join is one of GeoPandas' most powerful features.
# gpd.sjoin() joins two GeoDataFrames based on spatial relationships.
# predicate options: 'intersects', 'contains', 'within', 'touches', 'crosses'

# Reproject the AGV log to UTM to match the field GeoDataFrame
agv_utm = agv_gdf.to_crs("EPSG:32610")

# Spatial join: for each AGV point, find which field polygon contains it
# (Most AGV points are outside all fields in this synthetic example,
#  but this demonstrates the workflow used in real fleet monitoring.)
joined = gpd.sjoin(
    agv_utm,                # left GeoDataFrame (points)
    gdf_utm[['field_id', 'crop_type', 'geometry']],  # right GeoDataFrame (polygons)
    how="left",             # keep all AGV positions even if no match
    predicate="within",     # True if point is within polygon
)

# Rename the overlapping index column
joined = joined.rename(columns={'index_right': 'field_index'})

print(f"AGV positions: {len(agv_utm)}")
print(f"Joined result:  {len(joined)}  (same count with left join)")
print()
print("AGV position → field assignment:")
cols = ['latitude', 'longitude', 'speed_kmh', 'field_id', 'crop_type']
# field_id will be NaN if the point doesn't fall in any field
available_cols = [c for c in cols if c in joined.columns]
print(joined[available_cols].to_string())
print()
print("NaN in field_id means that AGV position was not inside any field polygon.")
print("In a real pipeline you would flag these as 'outside operational zone'.")

# ---------------------------------------------------------------------------
# SECTION 8: Adding Derived Geometry Columns
# ---------------------------------------------------------------------------
print_section("SECTION 8: Derived Geometry Columns")

# GeoDataFrames can store multiple geometry columns, though only one is
# 'active' at a time. Common derived columns:
#   - centroid: center point of each polygon
#   - envelope: minimum bounding rectangle
#   - buffer: expanded polygon (for proximity analysis)

# Add centroid column (kept as a non-active geometry column)
gdf_utm['centroid'] = gdf_utm.geometry.centroid
gdf_utm['buffered_50m'] = gdf_utm.geometry.buffer(50)   # 50-meter buffer

print("Derived columns added to UTM GeoDataFrame:")
print(f"  'centroid'     → Point at geometric center of each polygon")
print(f"  'buffered_50m' → Polygon expanded 50 meters outward (proximity zone)")
print()
print("Centroid coordinates (UTM, meters):")
for _, row in gdf_utm.iterrows():
    cx, cy = row['centroid'].x, row['centroid'].y
    print(f"  {row['field_id']}: Easting={cx:.1f} m, Northing={cy:.1f} m")

print()
print("USE CASE: 50-meter buffer for irrigation adjacency analysis —")
print("Fields whose buffers overlap share a water resource boundary.")
print("This pattern is used for compliance checks in water-use permits.")

print_section("Script Complete")
print("Next: Run 03_basic_plotting.py to visualize these GeoDataFrames.")
