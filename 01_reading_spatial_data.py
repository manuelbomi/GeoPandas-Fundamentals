"""
01_reading_spatial_data.py
==========================
Author: Emmanuel Oyekanlu — Principal Data Engineer

PURPOSE:
    Demonstrate how to read geospatial data using GeoPandas.
    We cover GeoJSON loading, inspection of the GeoDataFrame structure,
    CRS verification, geometry type reporting, and basic attribute-table
    exploration — skills that are foundational for any geospatial pipeline.

REAL-WORLD CONTEXT:
    In agricultural data engineering, field boundary files arrive in many
    formats (GeoJSON from farm apps, Shapefiles from county assessors, GPKG
    from ESRI workflows). This script shows how to load and inspect them
    consistently regardless of format — the same `geopandas.read_file()`
    call handles all of them via Fiona's driver auto-detection.

USAGE:
    python 01_reading_spatial_data.py

EXPECTED OUTPUT:
    A series of printed inspection blocks showing CRS, geometry types,
    attribute table structure, and summary statistics.
"""

import os
import geopandas as gpd
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# SECTION 1: Locate the data file
# ---------------------------------------------------------------------------
# Build a path relative to this script's location so the code works
# regardless of the working directory from which it's invoked.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_PATH = os.path.join(SCRIPT_DIR, "data", "sample_fields.geojson")


def print_section(title: str) -> None:
    """Print a formatted section header for readable terminal output."""
    width = 65
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


# ---------------------------------------------------------------------------
# SECTION 2: Reading a GeoJSON file
# ---------------------------------------------------------------------------
print_section("SECTION 2: Reading a GeoJSON File")

# geopandas.read_file() is the primary entry point for loading spatial data.
# It uses Fiona under the hood and auto-detects the file format via the
# file extension and internal magic bytes. Supported formats include:
#   - GeoJSON (.geojson, .json)
#   - ESRI Shapefile (.shp)
#   - GeoPackage (.gpkg)
#   - File Geodatabase (.gdb)
#   - KML (.kml) with appropriate driver
#   - PostGIS (via connection string)

gdf = gpd.read_file(GEOJSON_PATH)

print(f"File loaded successfully: {GEOJSON_PATH}")
print(f"Type of returned object: {type(gdf)}")
print(f"  → geopandas.GeoDataFrame extends pandas.DataFrame")
print(f"  → It has all DataFrame methods PLUS spatial methods")

# ---------------------------------------------------------------------------
# SECTION 3: Inspecting the CRS (Coordinate Reference System)
# ---------------------------------------------------------------------------
print_section("SECTION 3: Coordinate Reference System (CRS)")

# The CRS defines WHICH coordinate system the (x, y) values use.
# GeoJSON is always in WGS84 (EPSG:4326) per the RFC 7946 spec.
# Shapefiles store CRS in a .prj sidecar file.
# GeoPackage stores CRS in an internal metadata table.

print(f"CRS object:      {gdf.crs}")
print(f"EPSG code:       {gdf.crs.to_epsg()}")
print(f"CRS name:        {gdf.crs.name}")
print(f"CRS type:        {'Geographic' if gdf.crs.is_geographic else 'Projected'}")
print(f"Axis units:      {[axis.unit_name for axis in gdf.crs.axis_info]}")
print()
print("WHY THIS MATTERS:")
print("  - EPSG:4326 (WGS84) stores coordinates as longitude/latitude in DEGREES.")
print("  - You CANNOT compute accurate area or distance in degrees.")
print("  - Always reproject to a metric projected CRS before computing geometry.")
print("  - For California: use EPSG:32610 (UTM Zone 10N), units = meters.")

# ---------------------------------------------------------------------------
# SECTION 4: DataFrame structure inspection
# ---------------------------------------------------------------------------
print_section("SECTION 4: GeoDataFrame Structure")

# The GeoDataFrame looks and behaves like a regular pandas DataFrame.
# The key difference is the 'geometry' column, which contains Shapely
# geometry objects (Point, LineString, Polygon, etc.)

print(f"Shape:           {gdf.shape}   ← (rows, columns)")
print(f"Columns:         {list(gdf.columns)}")
print(f"Active geometry: '{gdf.geometry.name}'  ← the special spatial column")
print()

# dtypes shows 'geometry' dtype for the spatial column
print("Column dtypes:")
print(gdf.dtypes.to_string())

# ---------------------------------------------------------------------------
# SECTION 5: Attribute table inspection
# ---------------------------------------------------------------------------
print_section("SECTION 5: Attribute Table (head)")

# .head() works exactly like pandas — shows first N rows.
# The geometry column shows a truncated WKT representation.
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)
print(gdf[['field_id', 'crop_type', 'area_ha', 'soil_type', 'irrigated']].head(10))

# ---------------------------------------------------------------------------
# SECTION 6: Geometry type inspection
# ---------------------------------------------------------------------------
print_section("SECTION 6: Geometry Types")

# Each row can (in theory) have a different geometry type.
# For a clean dataset, they should all be the same.
# geom_type is a GeoSeries attribute that returns the type string per row.

print("Geometry type per feature:")
for idx, row in gdf.iterrows():
    geom = row.geometry
    print(f"  {row['field_id']}: {geom.geom_type}  "
          f"| area={geom.area:.8f} sq-deg  "
          f"| is_valid={geom.is_valid}")

print()
# unique_geom_types tells you if your dataset is homogeneous
unique_types = gdf.geometry.geom_type.unique()
print(f"Unique geometry types in dataset: {unique_types}")

# ---------------------------------------------------------------------------
# SECTION 7: Bounding box and spatial extent
# ---------------------------------------------------------------------------
print_section("SECTION 7: Spatial Extent (Bounding Box)")

# total_bounds returns (minx, miny, maxx, maxy) — the spatial envelope
# of the entire dataset. Useful for:
#   - Setting map view extents
#   - Clipping a raster to the study area
#   - Validating data is in the expected region

minx, miny, maxx, maxy = gdf.total_bounds
print(f"Bounding box of entire dataset:")
print(f"  West  (min longitude): {minx:.6f}°")
print(f"  East  (max longitude): {maxx:.6f}°")
print(f"  South (min latitude):  {miny:.6f}°")
print(f"  North (max latitude):  {maxy:.6f}°")
print()
print(f"Width  (E-W extent): {(maxx - minx) * 111.32:.2f} km  (approx)")
print(f"Height (N-S extent): {(maxy - miny) * 110.57:.2f} km  (approx)")
print("  Note: 1 degree latitude ≈ 110.57 km; 1 degree longitude at 36.6°N ≈ 89.3 km")

# ---------------------------------------------------------------------------
# SECTION 8: Attribute statistics
# ---------------------------------------------------------------------------
print_section("SECTION 8: Attribute Statistics")

# Because GeoDataFrame inherits from DataFrame, all pandas stat methods work.
print("Numeric column summary:")
print(gdf[['area_ha']].describe().round(2))
print()

print("Crop type counts:")
print(gdf['crop_type'].value_counts().to_string())
print()

print("Soil type counts:")
print(gdf['soil_type'].value_counts().to_string())
print()

print(f"Irrigated fields:     {gdf['irrigated'].sum()} / {len(gdf)}")
print(f"Total area (ha):      {gdf['area_ha'].sum():.1f} ha")
print(f"Mean field size (ha): {gdf['area_ha'].mean():.1f} ha")

# ---------------------------------------------------------------------------
# SECTION 9: Accessing individual geometry attributes
# ---------------------------------------------------------------------------
print_section("SECTION 9: Per-Geometry Attributes from Shapely")

# Each geometry object in the GeoSeries is a Shapely geometry.
# Shapely objects have rich attributes: area, length, centroid, bounds, etc.

print(f"{'Field ID':<12} {'Centroid Lon':>14} {'Centroid Lat':>13} {'Perimeter (deg)':>17}")
print("-" * 60)
for _, row in gdf.iterrows():
    geom = row.geometry
    cx, cy = geom.centroid.x, geom.centroid.y
    perim = geom.length  # In degrees — not meaningful, just for demonstration
    print(f"{row['field_id']:<12} {cx:>14.6f} {cy:>13.6f} {perim:>17.6f}")

print()
print("IMPORTANT NOTE: area and length above are in DEGREES² and DEGREES respectively.")
print("They are shown here for inspection only. For real calculations, reproject first.")
print("See 04_crs_and_projections.py for the correct workflow.")

# ---------------------------------------------------------------------------
# SECTION 10: Simulating a Shapefile read (same API)
# ---------------------------------------------------------------------------
print_section("SECTION 10: Shapefile vs GeoJSON — Same API")

print("GeoPandas uses the same read_file() call for ALL formats:")
print()
print("  # GeoJSON")
print("  gdf = gpd.read_file('fields.geojson')")
print()
print("  # Shapefile (point to the .shp file; Fiona reads .dbf/.shx automatically)")
print("  gdf = gpd.read_file('fields.shp')")
print()
print("  # GeoPackage (can specify layer name if multiple layers)")
print("  gdf = gpd.read_file('fields.gpkg', layer='farm_fields')")
print()
print("  # PostGIS (requires sqlalchemy + GeoAlchemy2)")
print("  gdf = gpd.read_postgis('SELECT * FROM fields', con=engine, geom_col='geom')")
print()
print("This format-agnostic API is one of GeoPandas' greatest strengths for ETL pipelines.")

print_section("Script Complete")
print("Next: Run 02_geodataframe_operations.py to learn GeoDataFrame manipulation.")
