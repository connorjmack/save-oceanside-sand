"""
Compute Time Series Profiles for Transect Comparison

For each transect, finds all GPS points from ALL survey dates that fall
within a 1-meter buffer of the transect line, projects them onto the
transect, and creates time-series elevation data.
"""

import os
import sys
import json
import math
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from parse_llh import parse_all_llh_files, LLHPoint, LLHFile


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance in meters"""
    R = 6371000
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def point_to_segment_distance(px: float, py: float,
                               x1: float, y1: float,
                               x2: float, y2: float) -> Tuple[float, float, float]:
    """
    Calculate perpendicular distance from point to line segment.
    Returns (distance_meters, projection_ratio, distance_along_segment_meters)

    projection_ratio: 0 = at start, 1 = at end, 0-1 = on segment
    """
    # Convert to local meters (approximate for small distances)
    # At Oceanside (~33°N), 1 degree lat ≈ 110,574m, 1 degree lon ≈ 92,890m
    lat_to_m = 110574
    lon_to_m = 92890

    # Convert to local coordinate system (meters)
    px_m = (px - x1) * lon_to_m
    py_m = (py - y1) * lat_to_m
    x2_m = (x2 - x1) * lon_to_m
    y2_m = (y2 - y1) * lat_to_m

    # Segment length squared
    seg_len_sq = x2_m**2 + y2_m**2

    if seg_len_sq < 1e-10:  # Degenerate segment
        dist = math.sqrt(px_m**2 + py_m**2)
        return dist, 0.0, 0.0

    # Projection ratio (0-1 if on segment)
    t = max(0, min(1, (px_m * x2_m + py_m * y2_m) / seg_len_sq))

    # Closest point on segment
    proj_x = t * x2_m
    proj_y = t * y2_m

    # Distance to closest point
    dist = math.sqrt((px_m - proj_x)**2 + (py_m - proj_y)**2)

    # Distance along segment to projection point
    dist_along = t * math.sqrt(seg_len_sq)

    return dist, t, dist_along


def project_point_onto_transect(point_lon: float, point_lat: float,
                                 transect_coords: List[List[float]]) -> Optional[Tuple[float, float]]:
    """
    Project a point onto a transect polyline.

    Returns (distance_to_line, distance_along_transect) or None if too far.
    Buffer distance is 1 meter.
    """
    BUFFER_METERS = 1.0

    min_dist = float('inf')
    best_dist_along = 0.0
    cumulative_dist = 0.0

    for i in range(len(transect_coords) - 1):
        lon1, lat1 = transect_coords[i][0], transect_coords[i][1]
        lon2, lat2 = transect_coords[i+1][0], transect_coords[i+1][1]

        # Get segment length for cumulative distance
        seg_len = haversine_distance(lat1, lon1, lat2, lon2)

        # Get distance from point to this segment
        dist, t, dist_along_seg = point_to_segment_distance(
            point_lon, point_lat, lon1, lat1, lon2, lat2
        )

        if dist < min_dist:
            min_dist = dist
            best_dist_along = cumulative_dist + dist_along_seg

        cumulative_dist += seg_len

    if min_dist <= BUFFER_METERS:
        return (min_dist, best_dist_along)
    return None


def build_spatial_index(all_points: List[Tuple[float, float, float, str, datetime]],
                        cell_size: float = 0.0001) -> Dict[Tuple[int, int], List]:
    """
    Build a simple grid-based spatial index for fast point lookup.
    cell_size is in degrees (~10m at this latitude)
    """
    index = defaultdict(list)

    for point_data in all_points:
        lon, lat = point_data[0], point_data[1]
        cell_x = int(lon / cell_size)
        cell_y = int(lat / cell_size)
        index[(cell_x, cell_y)].append(point_data)

    return index


def get_nearby_cells(lon: float, lat: float, cell_size: float = 0.0001,
                     buffer_cells: int = 1) -> List[Tuple[int, int]]:
    """Get grid cells that might contain nearby points"""
    center_x = int(lon / cell_size)
    center_y = int(lat / cell_size)

    cells = []
    for dx in range(-buffer_cells, buffer_cells + 1):
        for dy in range(-buffer_cells, buffer_cells + 1):
            cells.append((center_x + dx, center_y + dy))
    return cells


def compute_transect_timeseries(transect_feature: Dict,
                                 spatial_index: Dict,
                                 cell_size: float = 0.0001) -> Dict:
    """
    Compute time series data for a single transect.

    Finds all points from all dates within 1m buffer and projects them.
    """
    coords = transect_feature['geometry']['coordinates']
    props = transect_feature['properties']
    transect_id = props['transect_id']
    transect_date = props['survey_date']

    # Collect all candidate points from cells near the transect
    candidate_points = []
    checked_cells = set()

    for coord in coords:
        lon, lat = coord[0], coord[1]
        nearby = get_nearby_cells(lon, lat, cell_size)
        for cell in nearby:
            if cell not in checked_cells:
                checked_cells.add(cell)
                candidate_points.extend(spatial_index.get(cell, []))

    # Project each candidate point onto transect
    # Group by date
    points_by_date = defaultdict(list)

    for point_data in candidate_points:
        lon, lat, height, quality, survey_date = point_data

        result = project_point_onto_transect(lon, lat, coords)
        if result is not None:
            perp_dist, dist_along = result
            points_by_date[survey_date].append({
                'distance': round(dist_along, 2),
                'elevation': round(height, 3),
                'quality': quality,
                'perp_distance': round(perp_dist, 3)
            })

    # Sort points by distance for each date
    timeseries = {}
    for date_str, points in points_by_date.items():
        sorted_points = sorted(points, key=lambda p: p['distance'])
        # Deduplicate by distance (take average if multiple points at same distance)
        deduplicated = []
        i = 0
        while i < len(sorted_points):
            # Group points within 0.5m
            group = [sorted_points[i]]
            j = i + 1
            while j < len(sorted_points) and sorted_points[j]['distance'] - sorted_points[i]['distance'] < 0.5:
                group.append(sorted_points[j])
                j += 1

            avg_dist = sum(p['distance'] for p in group) / len(group)
            avg_elev = sum(p['elevation'] for p in group) / len(group)
            deduplicated.append({
                'distance': round(avg_dist, 2),
                'elevation': round(avg_elev, 3)
            })
            i = j

        if len(deduplicated) >= 5:  # Only include if meaningful number of points
            timeseries[date_str] = {
                'distances': [p['distance'] for p in deduplicated],
                'elevations': [p['elevation'] for p in deduplicated],
                'point_count': len(deduplicated)
            }

    return {
        'transect_id': transect_id,
        'base_date': transect_date,
        'timeseries': timeseries,
        'num_dates': len(timeseries)
    }


def main():
    """Main processing function"""
    print("=" * 60)
    print("COMPUTING TRANSECT TIME SERIES DATA")
    print("=" * 60)

    # Load all raw GPS points
    print("\n[1/4] Loading all GPS points from LLH files...")
    llh_files = parse_all_llh_files('data/LLH')

    # Flatten all points with metadata
    all_points = []
    for llh_file in llh_files:
        date_str = llh_file.survey_date.strftime('%Y-%m-%d')
        for point in llh_file.points:
            all_points.append((
                point.lon,
                point.lat,
                point.height,
                point.quality,
                date_str
            ))

    print(f"  Loaded {len(all_points):,} total points from {len(llh_files)} files")

    # Build spatial index
    print("\n[2/4] Building spatial index...")
    spatial_index = build_spatial_index(all_points)
    print(f"  Created index with {len(spatial_index):,} cells")

    # Load transects
    print("\n[3/4] Loading transects...")
    with open('processed/transects.geojson', 'r') as f:
        transects = json.load(f)

    num_transects = len(transects['features'])
    print(f"  Loaded {num_transects} transects")

    # Compute time series for each transect
    print("\n[4/4] Computing time series for each transect...")
    timeseries_data = {}

    for i, feature in enumerate(transects['features']):
        if (i + 1) % 100 == 0:
            print(f"  Processing transect {i + 1}/{num_transects}...")

        ts_data = compute_transect_timeseries(feature, spatial_index)

        # Only store if there's data from multiple dates
        if ts_data['num_dates'] > 1:
            timeseries_data[ts_data['transect_id']] = ts_data

    # Save results
    output_path = 'processed/transect_timeseries.json'
    with open(output_path, 'w') as f:
        json.dump(timeseries_data, f)

    print(f"\n  Saved time series data for {len(timeseries_data)} transects")
    print(f"  Output: {output_path}")

    # Print statistics
    num_dates_dist = defaultdict(int)
    for ts in timeseries_data.values():
        num_dates_dist[ts['num_dates']] += 1

    print("\n  Time series coverage:")
    for n_dates in sorted(num_dates_dist.keys()):
        print(f"    {n_dates} dates: {num_dates_dist[n_dates]} transects")

    print("\n" + "=" * 60)
    print("TIME SERIES COMPUTATION COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
