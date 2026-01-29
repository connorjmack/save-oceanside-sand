"""
Compute Time Series Profiles for Transect Comparison (Optimized)

For selected transects, finds GPS points from ALL survey dates that fall
within a 1-meter buffer of the transect line using efficient spatial indexing.
"""

import os
import sys
import json
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utilities.parse_llh import parse_all_llh_files


# Constants for coordinate conversion at Oceanside latitude
LAT_TO_M = 110574  # meters per degree latitude
LON_TO_M = 92890   # meters per degree longitude at ~33°N
BUFFER_METERS = 1.0


def load_all_points():
    """Load all GPS points into numpy arrays for fast processing"""
    print("  Loading LLH files...")
    llh_files = parse_all_llh_files('data/raw/LLH')

    # Count total points
    total = sum(len(f.points) for f in llh_files)
    print(f"  Total points: {total:,}")

    # Pre-allocate arrays
    lons = np.zeros(total, dtype=np.float64)
    lats = np.zeros(total, dtype=np.float64)
    heights = np.zeros(total, dtype=np.float32)
    dates = []

    idx = 0
    for llh_file in llh_files:
        date_str = llh_file.survey_date.strftime('%Y-%m-%d')
        for point in llh_file.points:
            lons[idx] = point.lon
            lats[idx] = point.lat
            heights[idx] = point.height
            dates.append(date_str)
            idx += 1

    return lons, lats, heights, np.array(dates)


def point_to_line_distance_vectorized(px: np.ndarray, py: np.ndarray,
                                       x1: float, y1: float,
                                       x2: float, y2: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Vectorized distance from points to line segment.
    Returns (distances, distance_along_segment)
    """
    # Convert to local meters
    px_m = (px - x1) * LON_TO_M
    py_m = (py - y1) * LAT_TO_M
    x2_m = (x2 - x1) * LON_TO_M
    y2_m = (y2 - y1) * LAT_TO_M

    seg_len_sq = x2_m**2 + y2_m**2

    if seg_len_sq < 1e-10:
        dist = np.sqrt(px_m**2 + py_m**2)
        return dist, np.zeros_like(dist)

    # Projection ratio clamped to [0, 1]
    t = np.clip((px_m * x2_m + py_m * y2_m) / seg_len_sq, 0, 1)

    # Closest point on segment
    proj_x = t * x2_m
    proj_y = t * y2_m

    # Distance to closest point
    dist = np.sqrt((px_m - proj_x)**2 + (py_m - proj_y)**2)
    dist_along = t * np.sqrt(seg_len_sq)

    return dist, dist_along


def compute_transect_timeseries_fast(transect_coords: List[List[float]],
                                      transect_id: str,
                                      transect_date: str,
                                      lons: np.ndarray,
                                      lats: np.ndarray,
                                      heights: np.ndarray,
                                      dates: np.ndarray) -> Dict:
    """
    Fast computation of time series data for a single transect.
    """
    # Get bounding box of transect with buffer
    coords_arr = np.array(transect_coords)
    min_lon = coords_arr[:, 0].min() - 0.00002  # ~2m buffer
    max_lon = coords_arr[:, 0].max() + 0.00002
    min_lat = coords_arr[:, 1].min() - 0.00002
    max_lat = coords_arr[:, 1].max() + 0.00002

    # Filter points to bounding box first (fast)
    bbox_mask = (lons >= min_lon) & (lons <= max_lon) & \
                (lats >= min_lat) & (lats <= max_lat)

    if not np.any(bbox_mask):
        return None

    # Get subset of points
    sub_lons = lons[bbox_mask]
    sub_lats = lats[bbox_mask]
    sub_heights = heights[bbox_mask]
    sub_dates = dates[bbox_mask]

    # For each point, find minimum distance to any segment
    n_points = len(sub_lons)
    min_distances = np.full(n_points, np.inf)
    best_dist_along = np.zeros(n_points)

    cumulative_dist = 0.0

    for i in range(len(transect_coords) - 1):
        lon1, lat1 = transect_coords[i][0], transect_coords[i][1]
        lon2, lat2 = transect_coords[i+1][0], transect_coords[i+1][1]

        # Segment length
        seg_len = np.sqrt(((lon2-lon1)*LON_TO_M)**2 + ((lat2-lat1)*LAT_TO_M)**2)

        # Distance from all points to this segment
        dist, dist_along = point_to_line_distance_vectorized(
            sub_lons, sub_lats, lon1, lat1, lon2, lat2
        )

        # Update minimums
        closer = dist < min_distances
        min_distances = np.where(closer, dist, min_distances)
        best_dist_along = np.where(closer, cumulative_dist + dist_along, best_dist_along)

        cumulative_dist += seg_len

    # Filter to points within buffer
    within_buffer = min_distances <= BUFFER_METERS

    if not np.any(within_buffer):
        return None

    final_dists = best_dist_along[within_buffer]
    final_heights = sub_heights[within_buffer]
    final_dates = sub_dates[within_buffer]

    # Group by date
    timeseries = {}
    unique_dates = np.unique(final_dates)

    for date_str in unique_dates:
        date_mask = final_dates == date_str
        d = final_dists[date_mask]
        h = final_heights[date_mask]

        # Sort by distance
        sort_idx = np.argsort(d)
        d = d[sort_idx]
        h = h[sort_idx]

        # Bin points by 0.5m intervals and average
        if len(d) < 3:
            continue

        bin_edges = np.arange(0, d.max() + 0.5, 0.5)
        if len(bin_edges) < 2:
            continue

        bin_indices = np.digitize(d, bin_edges)
        binned_dists = []
        binned_elevs = []

        for bin_idx in range(1, len(bin_edges)):
            mask = bin_indices == bin_idx
            if np.any(mask):
                binned_dists.append(float(np.mean(d[mask])))
                binned_elevs.append(float(np.mean(h[mask])))

        if len(binned_dists) >= 5:
            timeseries[date_str] = {
                'distances': [round(x, 2) for x in binned_dists],
                'elevations': [round(x, 3) for x in binned_elevs]
            }

    if len(timeseries) < 2:
        return None

    return {
        'transect_id': transect_id,
        'base_date': transect_date,
        'timeseries': timeseries,
        'num_dates': len(timeseries)
    }


def select_representative_transects(transects: Dict, max_transects: int = 200) -> List[Dict]:
    """
    Select representative transects spread across space and time.
    """
    features = transects['features']

    if len(features) <= max_transects:
        return features

    # Group by date
    by_date = defaultdict(list)
    for f in features:
        by_date[f['properties']['survey_date']].append(f)

    # Select evenly from each date
    selected = []
    dates = sorted(by_date.keys())
    per_date = max(1, max_transects // len(dates))

    for date in dates:
        date_transects = by_date[date]
        # Select evenly spaced transects
        if len(date_transects) <= per_date:
            selected.extend(date_transects)
        else:
            indices = np.linspace(0, len(date_transects) - 1, per_date, dtype=int)
            selected.extend([date_transects[i] for i in indices])

    return selected[:max_transects]


def main():
    """Main processing function"""
    print("=" * 60)
    print("COMPUTING TRANSECT TIME SERIES DATA")
    print("=" * 60)

    # Load all points into numpy arrays
    print("\n[1/3] Loading all GPS points...")
    lons, lats, heights, dates = load_all_points()
    print(f"  Loaded {len(lons):,} points")

    # Load transects
    print("\n[2/3] Loading and selecting transects...")
    with open('data/processed/transects.geojson', 'r') as f:
        transects = json.load(f)

    # Select representative subset for faster processing
    selected = select_representative_transects(transects, max_transects=300)
    print(f"  Selected {len(selected)} representative transects")

    # Compute time series
    print("\n[3/3] Computing time series...")
    timeseries_data = {}

    for i, feature in enumerate(selected):
        if (i + 1) % 50 == 0:
            print(f"  Processing {i + 1}/{len(selected)}...")

        props = feature['properties']
        coords = feature['geometry']['coordinates']

        result = compute_transect_timeseries_fast(
            coords,
            props['transect_id'],
            props['survey_date'],
            lons, lats, heights, dates
        )

        if result:
            timeseries_data[result['transect_id']] = result

    # Save results
    output_path = 'data/processed/transect_timeseries.json'
    with open(output_path, 'w') as f:
        json.dump(timeseries_data, f)

    print(f"\n  Saved {len(timeseries_data)} transects with multi-date data")

    # Statistics
    if timeseries_data:
        avg_dates = np.mean([ts['num_dates'] for ts in timeseries_data.values()])
        max_dates = max(ts['num_dates'] for ts in timeseries_data.values())
        print(f"  Average dates per transect: {avg_dates:.1f}")
        print(f"  Maximum dates for a transect: {max_dates}")

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
