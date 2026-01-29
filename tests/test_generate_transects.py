"""
Tests for generate_transects.py - Transect generation functionality
"""

import os
import sys
import json
import math
import tempfile
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utilities.parse_llh import LLHPoint, LLHFile
from scripts.generate_transects import (
    Transect,
    haversine_distance,
    calculate_bearing,
    segment_points_into_transects,
    generate_transects_geojson,
    generate_profile_data
)


class TestHaversineDistance:
    """Tests for haversine_distance function"""

    def test_same_point_zero_distance(self):
        """Test that distance between same point is zero"""
        dist = haversine_distance(33.2, -117.3, 33.2, -117.3)
        assert dist == 0.0

    def test_known_distance(self):
        """Test against a known distance calculation"""
        # San Diego to Los Angeles is approximately 180 km
        # Using approximate coordinates
        sd_lat, sd_lon = 32.7157, -117.1611
        la_lat, la_lon = 34.0522, -118.2437

        dist = haversine_distance(sd_lat, sd_lon, la_lat, la_lon)

        # Should be approximately 180 km (180000 meters) +/- 10%
        assert 160000 < dist < 200000

    def test_short_distance_oceanside_beach(self):
        """Test short distance typical of beach survey points"""
        # Two points about 1 meter apart on Oceanside beach
        lat1, lon1 = 33.201084, -117.387366
        lat2, lon2 = 33.201094, -117.387366  # ~1m north

        dist = haversine_distance(lat1, lon1, lat2, lon2)

        # Should be approximately 1.1 meters
        assert 0.5 < dist < 2.0

    def test_distance_symmetry(self):
        """Test that distance is symmetric (A to B == B to A)"""
        lat1, lon1 = 33.2, -117.3
        lat2, lon2 = 33.3, -117.4

        dist1 = haversine_distance(lat1, lon1, lat2, lon2)
        dist2 = haversine_distance(lat2, lon2, lat1, lon1)

        assert abs(dist1 - dist2) < 0.01


class TestCalculateBearing:
    """Tests for calculate_bearing function"""

    def test_north_bearing(self):
        """Test bearing for point directly north"""
        bearing = calculate_bearing(33.0, -117.0, 34.0, -117.0)
        # Should be approximately 0 degrees (north)
        assert bearing < 5 or bearing > 355

    def test_east_bearing(self):
        """Test bearing for point directly east"""
        bearing = calculate_bearing(33.0, -117.0, 33.0, -116.0)
        # Should be approximately 90 degrees (east)
        assert 85 < bearing < 95

    def test_south_bearing(self):
        """Test bearing for point directly south"""
        bearing = calculate_bearing(34.0, -117.0, 33.0, -117.0)
        # Should be approximately 180 degrees (south)
        assert 175 < bearing < 185

    def test_west_bearing(self):
        """Test bearing for point directly west"""
        bearing = calculate_bearing(33.0, -116.0, 33.0, -117.0)
        # Should be approximately 270 degrees (west)
        assert 265 < bearing < 275

    def test_bearing_range(self):
        """Test that bearing is always in 0-360 range"""
        # Test several random bearings
        test_cases = [
            (33.0, -117.0, 33.5, -117.5),
            (33.0, -117.0, 32.5, -116.5),
            (33.0, -117.0, 32.5, -117.5),
        ]

        for lat1, lon1, lat2, lon2 in test_cases:
            bearing = calculate_bearing(lat1, lon1, lat2, lon2)
            assert 0 <= bearing < 360


class TestTransect:
    """Tests for Transect class"""

    def test_transect_creation(self, sample_llh_points):
        """Test creating a Transect"""
        transect = Transect(
            transect_id="20250309_Test_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=sample_llh_points
        )

        assert transect.transect_id == "20250309_Test_T001"
        assert transect.point_count == 100
        assert transect.device_name == "Test"

    def test_start_end_points(self, sample_llh_points):
        """Test start_point and end_point properties"""
        transect = Transect(
            transect_id="20250309_Test_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=sample_llh_points
        )

        assert transect.start_point == sample_llh_points[0]
        assert transect.end_point == sample_llh_points[-1]

    def test_avg_quality(self, sample_llh_points):
        """Test avg_quality property"""
        transect = Transect(
            transect_id="20250309_Test_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=sample_llh_points
        )

        avg = transect.avg_quality
        # Quality is 1 or 2 based on fixture, so average should be between 1 and 2
        assert 1.0 <= avg <= 2.0

    def test_rtk_fix_percentage(self, sample_llh_points):
        """Test rtk_fix_percentage property"""
        transect = Transect(
            transect_id="20250309_Test_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=sample_llh_points
        )

        pct = transect.rtk_fix_percentage
        # 66 of 100 points have quality=1 (RTK fix)
        assert pct == 66.0

    def test_bounds(self, sample_llh_points):
        """Test bounds property"""
        transect = Transect(
            transect_id="20250309_Test_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=sample_llh_points
        )

        bounds = transect.bounds
        assert 'min_lat' in bounds
        assert 'max_lat' in bounds
        assert 'min_lon' in bounds
        assert 'max_lon' in bounds
        assert bounds['min_lat'] < bounds['max_lat']
        assert bounds['min_lon'] < bounds['max_lon']

    def test_length_meters(self, sample_llh_points):
        """Test length_meters method"""
        transect = Transect(
            transect_id="20250309_Test_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=sample_llh_points
        )

        length = transect.length_meters()
        # Points move by ~0.00001 degrees each, 100 points
        # Should be a few hundred meters
        assert length > 0

    def test_to_geojson_feature(self, sample_llh_points):
        """Test converting transect to GeoJSON feature"""
        transect = Transect(
            transect_id="20250309_Test_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=sample_llh_points
        )

        feature = transect.to_geojson_feature()

        assert feature['type'] == 'Feature'
        assert feature['id'] == '20250309_Test_T001'
        assert feature['geometry']['type'] == 'LineString'
        assert len(feature['geometry']['coordinates']) == 100

        # Check properties
        props = feature['properties']
        assert props['transect_id'] == '20250309_Test_T001'
        assert props['survey_date'] == '2025-03-09'
        assert props['point_count'] == 100
        assert 'length_meters' in props
        assert 'rtk_fix_percentage' in props
        assert 'quality_counts' in props

    def test_to_profile_data(self, sample_llh_points):
        """Test converting transect to profile data"""
        transect = Transect(
            transect_id="20250309_Test_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=sample_llh_points
        )

        profile = transect.to_profile_data()

        assert profile['transect_id'] == '20250309_Test_T001'
        assert profile['survey_date'] == '2025-03-09'
        assert len(profile['distances']) == 100
        assert len(profile['elevations']) == 100
        assert len(profile['qualities']) == 100
        assert len(profile['coordinates']) == 100

        # First distance should be 0
        assert profile['distances'][0] == 0.0

        # Distances should be monotonically increasing
        for i in range(1, len(profile['distances'])):
            assert profile['distances'][i] >= profile['distances'][i - 1]


class TestSegmentPointsIntoTransects:
    """Tests for segment_points_into_transects function"""

    def test_single_continuous_segment(self, sample_llh_file):
        """Test that continuous points form a single transect"""
        transects = segment_points_into_transects(
            sample_llh_file,
            time_gap_threshold=30.0,
            direction_change_threshold=90.0,
            min_points_per_transect=50
        )

        # All 100 points should form one transect
        assert len(transects) == 1
        assert transects[0].point_count == 100

    def test_time_gap_segmentation(self, points_with_time_gap):
        """Test that time gaps create separate transects"""
        llh_file = LLHFile(
            filename="2025_03_09_Test_solution_20250309195528.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=points_with_time_gap
        )

        transects = segment_points_into_transects(
            llh_file,
            time_gap_threshold=30.0,
            direction_change_threshold=90.0,
            min_points_per_transect=50
        )

        # Should have 2 transects (split by 45s gap)
        assert len(transects) == 2
        assert transects[0].point_count == 60
        assert transects[1].point_count == 60

    def test_direction_change_segmentation(self, points_with_direction_change):
        """Test that direction changes create separate transects"""
        llh_file = LLHFile(
            filename="2025_03_09_Test_solution_20250309195528.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=points_with_direction_change
        )

        transects = segment_points_into_transects(
            llh_file,
            time_gap_threshold=30.0,
            direction_change_threshold=90.0,
            min_points_per_transect=50
        )

        # Should have 2 transects (split by direction change)
        assert len(transects) == 2

    def test_minimum_points_filter(self, sample_llh_points):
        """Test that segments below minimum points are discarded"""
        # Create a file with only 30 points
        small_points = sample_llh_points[:30]
        llh_file = LLHFile(
            filename="2025_03_09_Test_solution_20250309195528.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=small_points
        )

        transects = segment_points_into_transects(
            llh_file,
            time_gap_threshold=30.0,
            direction_change_threshold=90.0,
            min_points_per_transect=50
        )

        # Should have 0 transects (30 < 50 minimum)
        assert len(transects) == 0

    def test_empty_file(self):
        """Test handling of empty LLH file"""
        llh_file = LLHFile(
            filename="2025_03_09_Test_solution_20250309195528.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=[]
        )

        transects = segment_points_into_transects(llh_file)
        assert transects == []

    def test_transect_id_format(self, sample_llh_file):
        """Test that transect IDs follow expected format"""
        transects = segment_points_into_transects(sample_llh_file)

        for transect in transects:
            # Format: YYYYMMDD_DeviceName_TXXX
            assert transect.transect_id.startswith("20250309_")
            assert "_T" in transect.transect_id

    def test_custom_thresholds(self, points_with_time_gap):
        """Test with custom threshold values"""
        llh_file = LLHFile(
            filename="2025_03_09_Test_solution_20250309195528.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=points_with_time_gap
        )

        # With higher time threshold (60s), gap of 45s should not split
        transects = segment_points_into_transects(
            llh_file,
            time_gap_threshold=60.0,  # Higher than 45s gap
            direction_change_threshold=90.0,
            min_points_per_transect=50
        )

        # Should be 1 transect (45s gap < 60s threshold)
        assert len(transects) == 1
        assert transects[0].point_count == 120


class TestGenerateTransectsGeoJSON:
    """Tests for generate_transects_geojson function"""

    def test_generate_geojson_file(self, sample_llh_points):
        """Test generating GeoJSON file"""
        transect = Transect(
            transect_id="20250309_Test_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=sample_llh_points
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "transects.geojson")
            generate_transects_geojson([transect], output_path)

            # Check file exists
            assert os.path.exists(output_path)

            # Load and verify content
            with open(output_path) as f:
                geojson = json.load(f)

            assert geojson['type'] == 'FeatureCollection'
            assert len(geojson['features']) == 1
            assert 'metadata' in geojson
            assert geojson['metadata']['total_transects'] == 1

    def test_generate_empty_geojson(self):
        """Test generating GeoJSON with no transects"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "transects.geojson")
            generate_transects_geojson([], output_path)

            with open(output_path) as f:
                geojson = json.load(f)

            assert geojson['type'] == 'FeatureCollection'
            assert len(geojson['features']) == 0


class TestGenerateProfileData:
    """Tests for generate_profile_data function"""

    def test_generate_profile_files(self, sample_llh_points):
        """Test generating profile data files"""
        transect = Transect(
            transect_id="20250309_Test_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Test",
            points=sample_llh_points
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_profile_data([transect], tmpdir)

            # Check file exists
            profile_path = os.path.join(tmpdir, "20250309_Test_T001.json")
            assert os.path.exists(profile_path)

            # Load and verify content
            with open(profile_path) as f:
                profile = json.load(f)

            assert profile['transect_id'] == '20250309_Test_T001'
            assert len(profile['distances']) == 100
            assert len(profile['elevations']) == 100

    def test_generate_multiple_profiles(self, sample_llh_points):
        """Test generating multiple profile files"""
        transects = [
            Transect(
                transect_id=f"20250309_Test_T{i:03d}",
                survey_date=datetime(2025, 3, 9),
                device_name="Test",
                points=sample_llh_points
            )
            for i in range(1, 4)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_profile_data(transects, tmpdir)

            # Check all files exist
            for i in range(1, 4):
                profile_path = os.path.join(tmpdir, f"20250309_Test_T{i:03d}.json")
                assert os.path.exists(profile_path)
