# GeoPandas Fundamentals
### A Practical Tutorial for Agricultural & Industrial Geospatial Analysis
**Author:** Emmanuel Oyekanlu — Principal Data Engineer

---

## Table of Contents
1. [What Is GeoPandas?](#what-is-geopandas)
2. [Why GeoPandas Matters](#why-geopandas-matters)
3. [Installation](#installation)
4. [Repository Structure](#repository-structure)
5. [Script-by-Script Usage Guide](#script-by-script-usage-guide)
6. [Key Concepts Reference](#key-concepts-reference)
7. [Real-World Applications](#real-world-applications)
8. [Troubleshooting](#troubleshooting)

---

## What Is GeoPandas?

GeoPandas is an open-source Python library that extends the popular **pandas** data analysis library to support geospatial data operations. Just as pandas gives you a `DataFrame` for tabular data, GeoPandas gives you a **`GeoDataFrame`** — a DataFrame that has one special column (called `geometry`) containing geographic shapes: points, lines, and polygons.

Under the hood, GeoPandas is built on top of several foundational geospatial libraries:

| Library     | Role                                                                 |
|-------------|----------------------------------------------------------------------|
| **Shapely** | Creates and manipulates geometric objects (points, polygons, etc.)   |
| **Fiona**   | Reads and writes spatial file formats (Shapefile, GeoJSON, GPKG)     |
| **PyProj**  | Handles coordinate reference systems (CRS) and map projections       |
| **pandas**  | Provides the underlying DataFrame infrastructure                     |
| **matplotlib** | Powers the static map plotting capabilities                      |

Think of GeoPandas as the glue that binds all of these together into an easy-to-use, pandas-friendly interface. If you already know pandas, you already know 70% of GeoPandas.

---

## Why GeoPandas Matters

### For Agricultural Data Engineering

Modern precision agriculture produces enormous volumes of geospatial data:

- **Field boundary polygons** from farm management software (e.g., Climate FieldView, John Deere Operations Center)
- **Soil sample point clouds** from variable-rate application surveys
- **Yield monitor tracks** from combine harvesters (GPS-tagged yield data every few seconds)
- **NDVI raster layers** derived from satellite imagery (Sentinel-2, Landsat)
- **Irrigation zone polygons** from district GIS databases
- **Weather station locations** for interpolation and advisory systems

GeoPandas lets a data engineer ingest all of these formats, join them on spatial relationships ("which soil samples fall inside this field polygon?"), compute area and distance metrics, reproject between coordinate systems, and export enriched datasets — all in a few dozen lines of Python.

### For AGV / AMR (Autonomous Ground Vehicle / Autonomous Mobile Robot) Systems

In a warehouse or agricultural AGV deployment, geospatial thinking is everywhere:

- **Geofencing:** Define boundary polygons for operational zones. Check whether an AGV's GPS fix falls inside an allowed zone.
- **Path planning layers:** Aisles, charging stations, no-go zones, and pedestrian corridors are spatial features that can be stored and queried as GeoDataFrames.
- **Fleet monitoring dashboards:** Plot real-time AGV positions on a floor-plan map using GeoPandas + matplotlib.
- **Incident reporting:** Spatially join an AGV collision event (a point) with zone polygons to auto-tag the incident with context ("collision occurred in Aisle 7, Zone B — near charging dock").

### For Industrial Data Pipelines

GeoPandas integrates cleanly with the modern data stack:

- Read spatial data from **PostGIS** (via SQLAlchemy + GeoAlchemy2)
- Write results to **cloud storage** (GeoJSON files in S3/GCS)
- Serve as the spatial engine inside **Apache Airflow DAGs**
- Feed enriched GeoDataFrames into **Pandas pipelines** for downstream ML feature engineering

---

## Installation

### Prerequisites
- Python 3.9 or higher
- A virtual environment (strongly recommended)

### Step 1: Create and Activate a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Notes on Installation
GeoPandas has C-level dependencies (GDAL, GEOS, PROJ) that can be tricky on Windows.
If `pip install geopandas` fails on Windows, use the **conda** approach:

```bash
conda create -n geopandas_env python=3.11
conda activate geopandas_env
conda install -c conda-forge geopandas matplotlib fiona shapely pyproj
```

Alternatively, install pre-compiled wheels from Christoph Gohlke's repository or use WSL2.

---

## Repository Structure

```
01_geopandas_fundamentals/
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
├── .gitignore                       # Standard Python gitignore
├── data/
│   └── sample_fields.geojson        # 5 agricultural field polygons (Salinas Valley, CA)
├── 01_reading_spatial_data.py       # Load GeoJSON & Shapefile, inspect CRS and attributes
├── 02_geodataframe_operations.py    # Build GeoDataFrames, reproject, spatial filtering
├── 03_basic_plotting.py             # Multi-panel matplotlib maps, save PNG
└── 04_crs_and_projections.py        # Deep dive into CRS: WGS84 vs UTM
```

---

## Script-by-Script Usage Guide

### `01_reading_spatial_data.py`
**What it teaches:** How to load geospatial data from GeoJSON and inspect it.

```bash
python 01_reading_spatial_data.py
```

This script:
- Reads `data/sample_fields.geojson` using `geopandas.read_file()`
- Prints the CRS (Coordinate Reference System)
- Prints geometry types for each feature
- Displays the attribute table head (like `df.head()`)
- Shows bounding box and basic statistics

**Key takeaway:** GeoPandas makes reading spatial data as easy as `pd.read_csv()`.

---

### `02_geodataframe_operations.py`
**What it teaches:** Creating GeoDataFrames from scratch, reprojecting, and spatial filtering.

```bash
python 02_geodataframe_operations.py
```

This script:
- Builds a `GeoDataFrame` from Shapely `Polygon` objects and a Python dict
- Sets the CRS to EPSG:4326 (WGS84, latitude/longitude)
- Reprojects to EPSG:32610 (UTM Zone 10N — appropriate for California)
- Filters rows where area exceeds a threshold
- Demonstrates `gdf.cx[]` coordinate-based indexing

**Key takeaway:** Always work in a projected CRS (UTM) when computing areas and distances. WGS84 gives area in degrees², which is meaningless.

---

### `03_basic_plotting.py`
**What it teaches:** Creating publication-quality static maps with matplotlib.

```bash
python 03_basic_plotting.py
```

This script:
- Creates a multi-panel figure (2×2 subplots)
- Color-codes polygons by `crop_type` attribute (categorical colormap)
- Color-codes polygons by `area_ha` attribute (continuous colormap with colorbar)
- Adds centroids as scatter points
- Saves the figure as `output_map.png`

**Key takeaway:** GeoPandas `.plot()` returns a matplotlib `Axes` object — you can combine it with any standard matplotlib customization.

---

### `04_crs_and_projections.py`
**What it teaches:** CRS concepts, why they matter, and how to work with them correctly.

```bash
python 04_crs_and_projections.py
```

This script:
- Explains EPSG codes with practical examples
- Demonstrates WGS84 (geographic) vs UTM (projected) coordinates
- Shows the area distortion you get by computing area in the wrong CRS
- Guides through reprojecting and verifying the result
- Prints CRS authority strings, axis information, and units

**Key takeaway:** CRS errors are the #1 source of silent bugs in geospatial pipelines. Always check `.crs` before any calculation.

---

## Key Concepts Reference

### Coordinate Reference Systems (CRS)

| EPSG Code | Name         | Type       | Units   | Use Case                          |
|-----------|--------------|------------|---------|-----------------------------------|
| 4326      | WGS84        | Geographic | Degrees | GPS coordinates, web maps, storage|
| 32610     | UTM Zone 10N | Projected  | Meters  | California — distance & area calc |
| 32614     | UTM Zone 14N | Projected  | Meters  | Central US (Kansas, Nebraska)     |
| 3857      | Web Mercator | Projected  | Meters  | Tile-based web maps (Google, OSM) |
| 5070      | CONUS Albers | Projected  | Meters  | National US analysis              |

### GeoDataFrame Anatomy

```python
gdf = gpd.read_file("data/sample_fields.geojson")
gdf.columns       # includes 'geometry' column + attribute columns
gdf.geometry      # GeoSeries of Shapely geometry objects
gdf.crs           # pyproj.CRS object
gdf.total_bounds  # (minx, miny, maxx, maxy) — bounding box
```

---

## Real-World Applications

### Use Case 1: Farm Boundary ETL Pipeline
An agricultural data platform ingests field boundary uploads from farmers (GeoJSON from their farm app). A GeoPandas pipeline:
1. Reads uploaded GeoJSON
2. Validates geometry (no self-intersections, no NaN coordinates)
3. Reprojects to UTM, computes area in hectares
4. Spatially joins with a county boundary layer to assign the correct county FIPS code
5. Writes enriched records to a PostGIS database

### Use Case 2: AGV Zone Compliance Audit
After a shift, download all AGV position logs (lat/lon + timestamp). Use GeoPandas to:
1. Convert position logs to a GeoDataFrame of points
2. Spatially join points with zone polygons
3. Flag any positions that fall outside allowed zones
4. Generate a per-AGV compliance report

### Use Case 3: Irrigation Efficiency Analysis
Join field polygons with irrigation district boundaries. For each field, calculate:
- What percentage of the field lies within each irrigation district
- Total irrigated area by crop type
- Fields that straddle district boundaries (require special handling)

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'fiona'`**
→ Install with `pip install fiona` or use conda. On Windows, ensure you have the GDAL runtime.

**`CRSError: Input is not a CRS`**
→ You're passing a raw integer like `4326` instead of `"EPSG:4326"`. Always use the full string.

**`ShapelyDeprecationWarning`**
→ You may be using Shapely 1.x syntax with Shapely 2.x. Update imports: use `shapely.geometry.Point` directly rather than `from shapely.geometry import Point` in some edge cases.

**Plots not showing (running on server)**
→ Add `import matplotlib; matplotlib.use('Agg')` before importing pyplot when running headlessly.

---

*Built by Emmanuel Oyekanlu — Principal Solution Engineer*

**For questions, see the individual script docstrings which contain detailed inline documentation.**
