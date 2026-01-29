"""
Transect Generator for Beach Survey Data

Segments continuous GPS point streams into discrete transects based on:
1. Time gaps between consecutive points (> threshold indicates new transect)
2. Directional changes (significant heading change indicates turn-around)
3. Spatial clustering (points separated by large distances)

Outputs GeoJSON files suitable for map visualization.
"""

import os
import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import numpy as np
from parse_llh import LLHFile, LLHPoint


class Transect:
    """Represents a single beach transect (line of GPS points)"""

    def __init__(self, transect_id: str, survey_date: datetime,
                 device_name: str, points: List[LLHPoint]):
        self.transect_id = transect_id
        self.survey_date = survey_date
        self.device_name = device_name
        self.points = points

    @property
    def point_count(self) -> int:
        return len(self.points)

    @property
    def start_point(self) -> LLHPoint:
        return self.points[0]

    @property
    def end_point(self) -> LLHPoint:
        return self.points[-1]

    @property
    def avg_quality(self) -> float:
        """Average quality flag across all points"""
        return sum(p.quality for p in self.points) / len(self.points)

    @property
    def rtk_fix_percentage(self) -> float:
        """Percentage of points with RTK fix (quality=1)"""
        rtk_count = sum(1 for p in self.points if p.quality == 1)
        return (rtk_count / len(self.points)) * 100

    @property
    def bounds(self) -> Dict[str, float]:
        """Geographic bounding box"""
        lats = [p.lat for p in self.points]
        lons = [p.lon for p in self.points]
        return {
            'min_lat': min(lats),
            'max_lat': max(lats),
            'min_lon': min(lons),
            'max_lon': max(lons)
        }

    def length_meters(self) -> float:
        """Approximate length of transect in meters using haversine distance"""
        total = 0.0
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            total += haversine_distance(p1.lat, p1.lon, p2.lat, p2.lon)
        return total

    def to_geojson_feature(self) -> Dict:
        """Convert transect to GeoJSON LineString feature"""
        coordinates = [[p.lon, p.lat, p.height] for p in self.points]

        # Calculate additional properties
        elevations = [p.height for p in self.points]
        qualities = [p.quality for p in self.points]

        return {
            'type': 'Feature',
            'id': self.transect_id,
            'geometry': {
                'type': 'LineString',
                'coordinates': coordinates
            },
            'properties': {
                'transect_id': self.transect_id,
                'survey_date': self.survey_date.strftime('%Y-%m-%d'),
                'device_name': self.device_name,
                'point_count': self.point_count,
                'length_meters': round(self.length_meters(), 2),
                'min_elevation': round(min(elevations), 3),
                'max_elevation': round(max(elevations), 3),
                'avg_elevation': round(sum(elevations) / len(elevations), 3),
                'rtk_fix_percentage': round(self.rtk_fix_percentage, 1),
                'avg_quality': round(self.avg_quality, 2),
                'quality_counts': {
                    'fix': sum(1 for q in qualities if q == 1),
                    'float': sum(1 for q in qualities if q == 2),
                    'single': sum(1 for q in qualities if q == 5)
                },
                'start_time': self.start_point.timestamp.isoformat(),
                'end_time': self.end_point.timestamp.isoformat()
            }
        }

    def to_profile_data(self) -> Dict:
        """
        Convert transect to profile data format for cross-section visualization.

        Returns distance along transect (cumulative from start) vs elevation.
        """
        distances = [0.0]
        elevations = [self.points[0].height]
        qualities = [self.points[0].quality]

        for i in range(1, len(self.points)):
            p1 = self.points[i - 1]
            p2 = self.points[i]
            dist = haversine_distance(p1.lat, p1.lon, p2.lat, p2.lon)
            distances.append(distances[-1] + dist)
            elevations.append(p2.height)
            qualities.append(p2.quality)

        return {
            'transect_id': self.transect_id,
            'survey_date': self.survey_date.strftime('%Y-%m-%d'),
            'distances': distances,
            'elevations': elevations,
            'qualities': qualities,
            'coordinates': [[p.lon, p.lat] for p in self.points]
        }


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great circle distance between two points in meters.

    Args:
        lat1, lon1: First point coordinates (decimal degrees)
        lat2, lon2: Second point coordinates (decimal degrees)

    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing from point 1 to point 2 in degrees (0-360).

    Args:
        lat1, lon1: First point coordinates (decimal degrees)
        lat2, lon2: Second point coordinates (decimal degrees)

    Returns:
        Bearing in degrees (0° = North, 90° = East)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    y = math.sin(dlon) * math.cos(lat2_rad)
    x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon))

    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360


def segment_points_into_transects(llh_file: LLHFile,
                                  time_gap_threshold: float = 30.0,
                                  direction_change_threshold: float = 90.0,
                                  min_points_per_transect: int = 50) -> List[Transect]:
    """
    Segment a continuous stream of GPS points into discrete transects.

    Segmentation logic:
    1. Time gaps: Split when gap between consecutive points > threshold
    2. Direction changes: Split when bearing change > threshold (indicates turnaround)
    3. Minimum length: Discard segments with fewer than min_points

    Args:
        llh_file: Parsed LLH file containing points
        time_gap_threshold: Maximum seconds between points in same transect
        direction_change_threshold: Maximum bearing change in degrees
        min_points_per_transect: Minimum points required for valid transect

    Returns:
        List of Transect objects
    """
    if not llh_file.points:
        return []

    transects = []
    current_segment = [llh_file.points[0]]
    previous_bearing = None

    for i in range(1, len(llh_file.points)):
        prev_point = llh_file.points[i - 1]
        curr_point = llh_file.points[i]

        # Check time gap
        time_diff = (curr_point.timestamp - prev_point.timestamp).total_seconds()
        if time_diff > time_gap_threshold:
            # End current transect
            if len(current_segment) >= min_points_per_transect:
                transect_id = f"{llh_file.survey_date.strftime('%Y%m%d')}_{llh_file.device_name}_T{len(transects) + 1:03d}"
                transects.append(Transect(transect_id, llh_file.survey_date,
                                        llh_file.device_name, current_segment))
            current_segment = [curr_point]
            previous_bearing = None
            continue

        # Check direction change (only if we have enough distance)
        dist = haversine_distance(prev_point.lat, prev_point.lon,
                                 curr_point.lat, curr_point.lon)

        if dist > 1.0:  # Only calculate bearing if points are > 1m apart
            current_bearing = calculate_bearing(prev_point.lat, prev_point.lon,
                                               curr_point.lat, curr_point.lon)

            if previous_bearing is not None:
                # Calculate angular difference
                bearing_diff = abs(current_bearing - previous_bearing)
                if bearing_diff > 180:
                    bearing_diff = 360 - bearing_diff

                # Check if direction changed significantly
                if bearing_diff > direction_change_threshold:
                    # End current transect
                    if len(current_segment) >= min_points_per_transect:
                        transect_id = f"{llh_file.survey_date.strftime('%Y%m%d')}_{llh_file.device_name}_T{len(transects) + 1:03d}"
                        transects.append(Transect(transect_id, llh_file.survey_date,
                                                llh_file.device_name, current_segment))
                    current_segment = [curr_point]
                    previous_bearing = None
                    continue

            previous_bearing = current_bearing

        # Continue current transect
        current_segment.append(curr_point)

    # Add final segment if valid
    if len(current_segment) >= min_points_per_transect:
        transect_id = f"{llh_file.survey_date.strftime('%Y%m%d')}_{llh_file.device_name}_T{len(transects) + 1:03d}"
        transects.append(Transect(transect_id, llh_file.survey_date,
                                llh_file.device_name, current_segment))

    return transects


def generate_transects_geojson(transects: List[Transect], output_path: str):
    """
    Generate GeoJSON FeatureCollection of all transects.

    Args:
        transects: List of Transect objects
        output_path: Path to output GeoJSON file
    """
    features = [t.to_geojson_feature() for t in transects]

    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'total_transects': len(transects),
            'generated_at': datetime.utcnow().isoformat(),
            'total_points': sum(t.point_count for t in transects)
        }
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(geojson, f, indent=2)

    print(f"Generated GeoJSON with {len(transects)} transects: {output_path}")


def generate_profile_data(transects: List[Transect], output_dir: str):
    """
    Generate individual profile data files for each transect.

    Args:
        transects: List of Transect objects
        output_dir: Directory to save profile JSON files
    """
    os.makedirs(output_dir, exist_ok=True)

    for transect in transects:
        profile_data = transect.to_profile_data()
        output_path = os.path.join(output_dir, f"{transect.transect_id}.json")

        with open(output_path, 'w') as f:
            json.dump(profile_data, f, indent=2)

    print(f"Generated {len(transects)} profile files in: {output_dir}")


if __name__ == '__main__':
    import sys
    from parse_llh import parse_all_llh_files

    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = 'data/LLH'

    print(f"Processing LLH files from: {data_dir}")
    llh_files = parse_all_llh_files(data_dir)

    # Generate transects for all files
    all_transects = []
    for llh_file in llh_files:
        transects = segment_points_into_transects(llh_file)
        all_transects.extend(transects)
        print(f"  {llh_file.filename}: {len(transects)} transects")

    print(f"\nTotal transects generated: {len(all_transects)}")

    # Generate outputs
    generate_transects_geojson(all_transects, 'processed/transects.geojson')
    generate_profile_data(all_transects, 'processed/profiles')

    print("\nDone!")
