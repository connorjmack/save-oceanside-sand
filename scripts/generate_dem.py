"""
DEM Generator for Beach Survey Data

Converts transect point data into regular grid Digital Elevation Models (DEMs)
for 3D surface visualization. Uses scipy interpolation to create continuous
surfaces from discrete transect measurements.

Output format:
- Binary Float32 files (.dem.bin) containing height values in row-major order
- Metadata JSON files (.dem.json) with bounds, dimensions, and transform info
"""

import os
import json
import struct
import math
from typing import Dict, List, Tuple, Optional
import numpy as np
from scipy.interpolate import griddata


# Reference point for local coordinate system (Oceanside Pier area)
ORIGIN_LAT = 33.19
ORIGIN_LON = -117.40

# Meters per degree at this latitude
METERS_PER_DEG_LAT = 111320
METERS_PER_DEG_LON = METERS_PER_DEG_LAT * math.cos(math.radians(ORIGIN_LAT))


def latlon_to_local(lat: float, lon: float) -> Tuple[float, float]:
    """
    Convert lat/lon to local metric coordinates (meters from origin).

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees

    Returns:
        Tuple of (x_meters, y_meters) from origin
    """
    y = (lat - ORIGIN_LAT) * METERS_PER_DEG_LAT
    x = (lon - ORIGIN_LON) * METERS_PER_DEG_LON
    return x, y


def local_to_latlon(x: float, y: float) -> Tuple[float, float]:
    """
    Convert local metric coordinates back to lat/lon.

    Args:
        x: X coordinate in meters from origin
        y: Y coordinate in meters from origin

    Returns:
        Tuple of (lat, lon) in decimal degrees
    """
    lat = ORIGIN_LAT + (y / METERS_PER_DEG_LAT)
    lon = ORIGIN_LON + (x / METERS_PER_DEG_LON)
    return lat, lon


def load_transects_geojson(filepath: str) -> Dict:
    """Load and parse the transects GeoJSON file."""
    print(f"Loading transects from {filepath}...")
    with open(filepath, 'r') as f:
        return json.load(f)


def extract_points_by_date(geojson: Dict) -> Dict[str, List[Tuple[float, float, float]]]:
    """
    Extract all points from transects, grouped by survey date.

    Args:
        geojson: Parsed transects GeoJSON

    Returns:
        Dict mapping date string to list of (x, y, elevation) tuples in local coords
    """
    points_by_date: Dict[str, List[Tuple[float, float, float]]] = {}

    for feature in geojson['features']:
        date = feature['properties']['survey_date']
        coords = feature['geometry']['coordinates']

        if date not in points_by_date:
            points_by_date[date] = []

        for coord in coords:
            lon, lat, elevation = coord[0], coord[1], coord[2]
            x, y = latlon_to_local(lat, lon)
            points_by_date[date].append((x, y, elevation))

    return points_by_date


def create_dem_grid(
    points: List[Tuple[float, float, float]],
    resolution: float = 2.0,
    buffer: float = 10.0,
    method: str = 'linear'
) -> Tuple[np.ndarray, Dict]:
    """
    Create a DEM grid from scattered points using interpolation.

    Args:
        points: List of (x, y, elevation) tuples in local coordinates
        resolution: Grid cell size in meters
        buffer: Buffer distance around point extent in meters
        method: Interpolation method ('linear', 'cubic', 'nearest')

    Returns:
        Tuple of (dem_array, metadata_dict)
    """
    if not points:
        raise ValueError("No points provided for DEM generation")

    # Convert to numpy arrays
    points_arr = np.array(points)
    x_points = points_arr[:, 0]
    y_points = points_arr[:, 1]
    z_points = points_arr[:, 2]

    # Calculate bounds with buffer
    x_min = x_points.min() - buffer
    x_max = x_points.max() + buffer
    y_min = y_points.min() - buffer
    y_max = y_points.max() + buffer

    # Create regular grid
    n_cols = int(np.ceil((x_max - x_min) / resolution))
    n_rows = int(np.ceil((y_max - y_min) / resolution))

    # Adjust max to fit exact grid cells
    x_max = x_min + n_cols * resolution
    y_max = y_min + n_rows * resolution

    # Generate grid coordinates
    x_grid = np.linspace(x_min + resolution/2, x_max - resolution/2, n_cols)
    y_grid = np.linspace(y_min + resolution/2, y_max - resolution/2, n_rows)
    xx, yy = np.meshgrid(x_grid, y_grid)

    # Interpolate
    print(f"  Interpolating {len(points)} points to {n_cols}x{n_rows} grid...")
    grid_points = np.column_stack([xx.ravel(), yy.ravel()])

    dem = griddata(
        points_arr[:, :2],  # x, y coordinates
        z_points,           # elevation values
        grid_points,
        method=method,
        fill_value=np.nan
    ).reshape(n_rows, n_cols)

    # Convert lat/lon bounds for metadata
    min_lat, min_lon = local_to_latlon(x_min, y_min)
    max_lat, max_lon = local_to_latlon(x_max, y_max)

    metadata = {
        'n_rows': n_rows,
        'n_cols': n_cols,
        'resolution': resolution,
        'bounds': {
            'x_min': x_min,
            'x_max': x_max,
            'y_min': y_min,
            'y_max': y_max,
            'min_lat': min_lat,
            'max_lat': max_lat,
            'min_lon': min_lon,
            'max_lon': max_lon
        },
        'origin': {
            'lat': ORIGIN_LAT,
            'lon': ORIGIN_LON
        },
        'nodata_value': -9999.0,
        'point_count': len(points),
        'elevation_stats': {
            'min': float(np.nanmin(dem)) if np.any(~np.isnan(dem)) else None,
            'max': float(np.nanmax(dem)) if np.any(~np.isnan(dem)) else None,
            'mean': float(np.nanmean(dem)) if np.any(~np.isnan(dem)) else None
        },
        'valid_cell_count': int(np.sum(~np.isnan(dem))),
        'total_cell_count': n_rows * n_cols
    }

    return dem, metadata


def save_dem_binary(dem: np.ndarray, filepath: str, nodata_value: float = -9999.0):
    """
    Save DEM as binary Float32 file.

    Args:
        dem: 2D numpy array of elevation values
        filepath: Output file path
        nodata_value: Value to use for NaN cells
    """
    # Replace NaN with nodata value
    dem_clean = np.where(np.isnan(dem), nodata_value, dem)

    # Convert to float32 and save as binary
    dem_float32 = dem_clean.astype(np.float32)

    with open(filepath, 'wb') as f:
        f.write(dem_float32.tobytes())

    print(f"  Saved binary DEM: {filepath} ({os.path.getsize(filepath)} bytes)")


def save_dem_metadata(metadata: Dict, filepath: str):
    """Save DEM metadata as JSON file."""
    with open(filepath, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  Saved metadata: {filepath}")


def generate_dem_for_date(
    date: str,
    points: List[Tuple[float, float, float]],
    output_dir: str,
    resolution: float = 2.0,
    method: str = 'linear'
) -> Optional[Dict]:
    """
    Generate DEM files for a single survey date.

    Args:
        date: Survey date string (YYYY-MM-DD)
        points: List of (x, y, elevation) points
        output_dir: Directory to save output files
        resolution: Grid cell size in meters
        method: Interpolation method

    Returns:
        Metadata dict if successful, None if failed
    """
    print(f"\nProcessing {date} ({len(points)} points)...")

    if len(points) < 10:
        print(f"  Skipping: insufficient points ({len(points)} < 10)")
        return None

    try:
        # Create DEM
        dem, metadata = create_dem_grid(points, resolution=resolution, method=method)

        # Add date to metadata
        metadata['survey_date'] = date

        # Save files
        os.makedirs(output_dir, exist_ok=True)
        bin_path = os.path.join(output_dir, f"{date}.dem.bin")
        json_path = os.path.join(output_dir, f"{date}.dem.json")

        save_dem_binary(dem, bin_path, metadata['nodata_value'])
        save_dem_metadata(metadata, json_path)

        return metadata

    except Exception as e:
        print(f"  Error generating DEM: {e}")
        return None


def generate_all_dems(
    transects_path: str,
    output_dir: str,
    resolution: float = 2.0,
    method: str = 'linear'
) -> Dict:
    """
    Generate DEMs for all survey dates.

    Args:
        transects_path: Path to transects.geojson
        output_dir: Directory to save output files
        resolution: Grid cell size in meters
        method: Interpolation method

    Returns:
        Index dict with metadata for all generated surfaces
    """
    # Load data
    geojson = load_transects_geojson(transects_path)
    points_by_date = extract_points_by_date(geojson)

    print(f"Found {len(points_by_date)} survey dates")

    # Generate DEMs for each date
    surfaces_index = {
        'surfaces': [],
        'resolution': resolution,
        'method': method,
        'origin': {
            'lat': ORIGIN_LAT,
            'lon': ORIGIN_LON
        }
    }

    for date in sorted(points_by_date.keys()):
        points = points_by_date[date]
        metadata = generate_dem_for_date(date, points, output_dir, resolution, method)

        if metadata and metadata['valid_cell_count'] > 0:
            surfaces_index['surfaces'].append({
                'date': date,
                'point_count': metadata['point_count'],
                'n_rows': metadata['n_rows'],
                'n_cols': metadata['n_cols'],
                'valid_cells': metadata['valid_cell_count'],
                'elevation_min': metadata['elevation_stats']['min'],
                'elevation_max': metadata['elevation_stats']['max'],
                'bounds': metadata['bounds']
            })
        elif metadata:
            print(f"  Skipping {date}: no valid interpolated cells")

    # Save index
    index_path = os.path.join(output_dir, 'surfaces_index.json')
    with open(index_path, 'w') as f:
        json.dump(surfaces_index, f, indent=2)

    print(f"\nGenerated {len(surfaces_index['surfaces'])} surfaces")
    print(f"Index saved: {index_path}")

    return surfaces_index


if __name__ == '__main__':
    import sys

    # Default paths
    transects_path = 'data/processed/transects.geojson'
    output_dir = 'data/processed/surfaces'
    resolution = 2.0  # meters

    # Parse command line args
    if len(sys.argv) > 1:
        transects_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    if len(sys.argv) > 3:
        resolution = float(sys.argv[3])

    print("=== Beach Survey DEM Generator ===")
    print(f"Input: {transects_path}")
    print(f"Output: {output_dir}")
    print(f"Resolution: {resolution}m")

    generate_all_dems(transects_path, output_dir, resolution=resolution)

    print("\nDone!")
