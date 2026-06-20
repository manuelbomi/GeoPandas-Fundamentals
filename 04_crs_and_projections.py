"""
04_crs_and_projections.py
==========================
Author: Emmanuel Oyekanlu — Principal Data Engineer

PURPOSE:
    Provide a thorough, practical tutorial on Coordinate Reference Systems
    (CRS) — the most common source of silent bugs in geospatial data pipelines.
    We explain the theory, demonstrate the consequences of wrong CRS choice,
    and show how to inspect, set, and transform CRS correctly using GeoPandas
    and pyproj.

REAL-WORLD CONTEXT:
    CRS errors are insidious because they often don't raise exceptions —
    they just give you wrong numbers. Examples from real pipelines:
      - Computing field area in WGS84 and reporting it to farmers in "hectares"
        (it was actually in square-degrees, off by a factor of ~10,000)
      - Joining two GeoDataFrames with different CRS and getting a completely
        wrong spatial relationship (points appearing in the ocean)
      - An AGV path planning system that mixed metric (UTM) zone polygons with
        a WGS84 GPS feed — the AGV could never find itself in any zone

    This script arms you with the knowledge to avoid these pitfalls.

USAGE:
    python 04_crs_and_projections.py
"""

import os
import math
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
from pyproj import CRS, Transformer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_PATH = os.path.join(SCRIPT_DIR, "data", "sample_fields.geojson")


def print_section(title: str) -> None:
    width = 65
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


# ---------------------------------------------------------------------------
# SECTION 1: What is a CRS?
# ---------------------------------------------------------------------------
print_section("SECTION 1: What Is a CRS?")

print("""
A Coordinate Reference System (CRS) is a mathematical framework that maps
numbers (x, y, and optionally z) to real-world geographic positions.

A CRS has three key components:

  1. DATUM — defines the shape of the Earth (the ellipsoid used as reference)
             Example: WGS84 datum uses an ellipsoid with:
               - Semi-major axis (equatorial radius): 6,378,137.0 m
               - Flattening: 1/298.257223563

  2. COORDINATE SYSTEM — the axis definition
             Geographic CS: axes are longitude and latitude (in degrees)
             Projected CS:  axes are Easting and Northing (in meters, feet, etc.)

  3. PROJECTION (for projected CRS only) — the mathematical method used to
             "unwrap" the curved Earth surface onto a flat 2D plane
             Examples: UTM (Universal Transverse Mercator), Albers, Lambert CC

EPSG CODES:
  The EPSG (European Petroleum Survey Group) registry assigns numeric codes
  to hundreds of standard CRS definitions. This is the most common way to
  specify a CRS in software.

  Key codes:
    EPSG:4326  → WGS84 Geographic  (GPS, lat/lon, GeoJSON standard)
    EPSG:3857  → Web Mercator      (Google Maps, OpenStreetMap tile layers)
    EPSG:32610 → UTM Zone 10N      (California, Oregon, Washington — metric)
    EPSG:32614 → UTM Zone 14N      (Kansas, Nebraska, Oklahoma — metric)
    EPSG:5070  → CONUS Albers      (Conterminous US equal-area — metric)
    EPSG:4269  → NAD83             (US national survey standard — geographic)
""")

# ---------------------------------------------------------------------------
# SECTION 2: Inspecting a CRS with pyproj
# ---------------------------------------------------------------------------
print_section("SECTION 2: CRS Inspection via pyproj")

# pyproj.CRS is the authoritative Python class for CRS information.
# GeoPandas' gdf.crs IS a pyproj.CRS object.

crs_wgs84 = CRS.from_epsg(4326)
crs_utm10n = CRS.from_epsg(32610)
crs_webmerc = CRS.from_epsg(3857)

for label, crs_obj in [("WGS84 (EPSG:4326)", crs_wgs84),
                         ("UTM Zone 10N (EPSG:32610)", crs_utm10n),
                         ("Web Mercator (EPSG:3857)", crs_webmerc)]:
    print(f"\n--- {label} ---")
    print(f"  Name:            {crs_obj.name}")
    print(f"  Type geographic: {crs_obj.is_geographic}")
    print(f"  Type projected:  {crs_obj.is_projected}")
    print(f"  Linear unit:     {crs_obj.axis_info[0].unit_name}")
    print(f"  EPSG:            {crs_obj.to_epsg()}")
    # Geodetic CRS is the underlying geographic CRS for projected ones
    if crs_obj.is_projected:
        print(f"  Underlying geog: {crs_obj.geodetic_crs.name}")

# ---------------------------------------------------------------------------
# SECTION 3: Geographic vs Projected — The Fundamental Difference
# ---------------------------------------------------------------------------
print_section("SECTION 3: Geographic vs Projected CRS")

print("""
GEOGRAPHIC CRS (e.g., WGS84 EPSG:4326):
  - Coordinates: (longitude °, latitude °)
  - The Earth stays as a curved ellipsoid
  - NO distortion in position — but area and distance calculations are WRONG
    if you treat degrees as a linear unit (they are NOT constant in km)
  - 1° latitude ≈ 110.57 km everywhere on Earth
  - 1° longitude ≈ 111.32 × cos(latitude) km  ← varies with latitude!
    At lat 36.6° (Salinas Valley): 1° lon ≈ 89.3 km
    At lat  0.0° (equator):        1° lon ≈ 111.3 km
    At lat 60.0° (Alaska/Norway):  1° lon ≈  55.7 km

PROJECTED CRS (e.g., UTM Zone 10N EPSG:32610):
  - Coordinates: (Easting m, Northing m)
  - The Earth's curved surface is mathematically "unrolled" onto a flat plane
  - 1 unit = 1 meter (in metric projected CRS)
  - Area in m² is accurate within each UTM zone (distortion < 0.1% near center)
  - Distance in meters is accurate — use for buffer zones, AGV path lengths, etc.

WHICH CRS TO USE WHEN:
  - STORAGE / INTERCHANGE: WGS84 (4326) — GPS-native, GeoJSON default
  - DISTANCE / AREA CALC:  UTM zone for your region (e.g., 32610 for CA)
  - NATIONAL US ANALYSIS:  CONUS Albers (5070)
  - WEB MAP TILES:         Web Mercator (3857) — but NEVER compute area in it
                           (Mercator distorts area severely at high latitudes)
""")

# ---------------------------------------------------------------------------
# SECTION 4: Demonstrating CRS Effect on Area Calculation
# ---------------------------------------------------------------------------
print_section("SECTION 4: Area Distortion — WGS84 vs UTM vs True")

# Define a 1° × 1° square centered on Salinas Valley
# This lets us calculate a "known" true area using spherical math
lat_center = 36.6
lon_center = -121.6
half_deg = 0.5

test_polygon_wgs84 = Polygon([
    (lon_center - half_deg, lat_center - half_deg),
    (lon_center + half_deg, lat_center - half_deg),
    (lon_center + half_deg, lat_center + half_deg),
    (lon_center - half_deg, lat_center + half_deg),
    (lon_center - half_deg, lat_center - half_deg),
])

# True area estimate: 1° lat × 1° lon at this latitude
true_km2 = (110.57 * 1.0) * (111.32 * math.cos(math.radians(lat_center)) * 1.0)
true_ha  = true_km2 * 100   # 1 km² = 100 ha

# Area in WGS84 (wrong — degrees²)
area_deg2 = test_polygon_wgs84.area

# Reproject and get area in m²
gdf_test = gpd.GeoDataFrame(
    [{"geometry": test_polygon_wgs84}],
    crs="EPSG:4326"
)
gdf_test_utm = gdf_test.to_crs("EPSG:32610")
area_utm_m2 = gdf_test_utm.geometry.iloc[0].area
area_utm_ha = area_utm_m2 / 10_000
area_utm_km2 = area_utm_m2 / 1_000_000

print(f"Test polygon: 1° × 1° square centered at lat={lat_center}, lon={lon_center}")
print()
print(f"  True area (spherical approx):  {true_km2:>12.2f} km²  = {true_ha:>12.1f} ha")
print(f"  Area in WGS84 degrees²:        {area_deg2:>12.6f} deg² ← MEANINGLESS")
print(f"  Area in UTM Zone 10N:          {area_utm_km2:>12.2f} km²  = {area_utm_ha:>12.1f} ha")
print()

error_pct = abs(area_utm_km2 - true_km2) / true_km2 * 100
print(f"  UTM vs True error: {error_pct:.2f}%  (excellent accuracy for a single UTM zone)")
print()
print("  The WGS84 value 0.862... sq-degrees has no physical meaning.")
print("  Never use Shapely .area on a WGS84 geometry in production.")

# ---------------------------------------------------------------------------
# SECTION 5: Reprojection Workflow Best Practices
# ---------------------------------------------------------------------------
print_section("SECTION 5: Reprojection Workflow and Pitfalls")

gdf = gpd.read_file(GEOJSON_PATH)

print("CORRECT REPROJECTION WORKFLOW:")
print()
print("  Step 1: Load data (it comes in its native CRS)")
print(f"          gdf.crs = {gdf.crs.to_epsg()}")
print()
print("  Step 2: CHECK the CRS before doing anything")
print("          Always print gdf.crs and confirm it's what you expect.")
print("          A silent CRS mismatch is the #1 cause of wrong spatial joins.")
print()
print("  Step 3: For area/distance → reproject to an appropriate metric CRS")
gdf_utm = gdf.to_crs("EPSG:32610")
print(f"          gdf_utm = gdf.to_crs('EPSG:32610')")
print(f"          gdf_utm.crs = {gdf_utm.crs.name}")
print()
print("  Step 4: Compute metrics in the projected CRS")
gdf_utm['area_m2'] = gdf_utm.geometry.area
gdf_utm['area_ha'] = gdf_utm['area_m2'] / 10_000
gdf_utm['perimeter_m'] = gdf_utm.geometry.length
print(f"          gdf_utm['area_ha']     = geometry.area / 10_000")
print(f"          gdf_utm['perimeter_m'] = geometry.length")
print()
print("  Step 5: When done, reproject BACK to WGS84 for storage/export")
gdf_out = gdf_utm.to_crs("EPSG:4326")
print(f"          gdf_out = gdf_utm.to_crs('EPSG:4326')  ← back to lat/lon for GeoJSON")

print()
print("\nField metrics in UTM (correctly projected):")
print(f"{'Field':>10} {'Area (m²)':>12} {'Area (ha)':>10} {'Perimeter (m)':>15}")
print("-" * 52)
for _, row in gdf_utm.iterrows():
    print(f"{row['field_id']:>10} {row['area_m2']:>12.1f} {row['area_ha']:>10.3f} {row['perimeter_m']:>15.1f}")

# ---------------------------------------------------------------------------
# SECTION 6: CRS Pitfalls — Common Errors and How to Catch Them
# ---------------------------------------------------------------------------
print_section("SECTION 6: Common CRS Pitfalls")

print("""
PITFALL 1: Joining GeoDataFrames with different CRS
   → Error: results may be wrong with NO exception raised
   → Fix:   Always call .to_crs(other_gdf.crs) before sjoin()

PITFALL 2: Setting CRS vs Reprojecting CRS
   → .set_crs("EPSG:4326")   — assigns CRS without transforming coords
     USE THIS when you have raw coordinates but no CRS metadata
   → .to_crs("EPSG:32610")   — transforms coordinates to new CRS
     USE THIS when you want to work in a different projection

PITFALL 3: Wrong axis order (lat/lon vs lon/lat)
   → WGS84 in GeoJSON spec = (longitude, latitude) = (x, y)
   → Some sensors/APIs return (latitude, longitude)
   → Always check before creating Point(x, y) objects

PITFALL 4: Using Web Mercator (EPSG:3857) for area/distance
   → Web Mercator is only for tile-based web maps
   → Area distortion at 60° latitude is ~4× worse than at equator
   → NEVER use gdf.to_crs(3857).geometry.area for real calculations

PITFALL 5: Assuming a UTM zone — verifying it
""")

# Demonstrate: find the correct UTM zone for a point
def get_utm_epsg(longitude: float, latitude: float) -> int:
    """
    Calculate the EPSG code for the UTM zone containing a given point.
    This is the standard formula used in GIS software.
    """
    zone_number = int((longitude + 180) / 6) + 1
    if latitude >= 0:
        epsg = 32600 + zone_number   # Northern hemisphere
    else:
        epsg = 32700 + zone_number   # Southern hemisphere
    return epsg

# Test on Salinas Valley
test_lon, test_lat = -121.6, 36.6
utm_epsg = get_utm_epsg(test_lon, test_lat)
print(f"  For Salinas Valley (lon={test_lon}, lat={test_lat}):")
print(f"  Correct UTM EPSG = {utm_epsg}  (Zone {(int((test_lon + 180) / 6) + 1)}N)")

# Test on a Midwest location (for context)
test_lon2, test_lat2 = -96.5, 38.5  # Kansas
utm_epsg2 = get_utm_epsg(test_lon2, test_lat2)
print(f"\n  For Central Kansas (lon={test_lon2}, lat={test_lat2}):")
print(f"  Correct UTM EPSG = {utm_epsg2}  (Zone {(int((test_lon2 + 180) / 6) + 1)}N)")

# ---------------------------------------------------------------------------
# SECTION 7: Pyproj Transformer — Low-Level Coordinate Conversion
# ---------------------------------------------------------------------------
print_section("SECTION 7: Low-Level Coordinate Transformation with pyproj")

print("Sometimes you need to transform individual (x, y) pairs, not a full")
print("GeoDataFrame. pyproj.Transformer gives you that control.")
print()

# Create a transformer from WGS84 to UTM Zone 10N
# always_xy=True ensures (longitude, latitude) input order regardless of CRS axis definition
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32610", always_xy=True)

# Transform sample AGV GPS positions
gps_positions = [
    (-121.635, 36.619),
    (-121.622, 36.614),
    (-121.608, 36.627),
]

print(f"{'GPS (lon, lat)':^30} | {'UTM (Easting, Northing)':^30}")
print("-" * 65)
for lon, lat in gps_positions:
    easting, northing = transformer.transform(lon, lat)
    print(f"  ({lon:.3f}, {lat:.3f}){' ':>12} | ({easting:.2f} m, {northing:.2f} m)")

print()
print("USE CASE: In an AGV system, when you receive a raw GPS NMEA sentence,")
print("use pyproj.Transformer to convert it to UTM before comparing against")
print("zone polygons stored in your fleet management database.")
print()
print("This avoids the overhead of constructing a GeoDataFrame for every")
print("single GPS ping — the Transformer is stateless and thread-safe.")

print_section("Script Complete — CRS Mastery Achieved")
print("You now know:")
print("  1. The difference between geographic and projected CRS")
print("  2. Why EPSG:4326 gives wrong area/distance values")
print("  3. How to choose the right UTM zone for your study area")
print("  4. How to reproject with .to_crs() vs .set_crs()")
print("  5. How to use pyproj.Transformer for low-level coordinate conversion")
print()
print("See README.md for a CRS quick-reference table.")
