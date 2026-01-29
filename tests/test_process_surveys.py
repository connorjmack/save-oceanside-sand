"""
Tests for process_surveys.py - Main pipeline orchestration
"""

import os
import sys
import json
import tempfile
from datetime import datetime
from collections import defaultdict

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from parse_llh import LLHFile, LLHPoint
from generate_transects import Transect
from process_surveys import (
    aggregate_surveys_by_date,
    generate_survey_metadata
)


class TestAggregateSurveysByDate:
    """Tests for aggregate_surveys_by_date function"""

    def test_aggregate_single_date(self, sample_llh_file):
        """Test aggregating files from a single date"""
        result = aggregate_surveys_by_date([sample_llh_file])

        assert len(result) == 1
        assert '2025-03-09' in result
        assert len(result['2025-03-09']) == 1

    def test_aggregate_multiple_files_same_date(self, sample_llh_points):
        """Test aggregating multiple files from the same date"""
        file1 = LLHFile(
            filename="2025_03_09_DeviceA_solution_20250309100000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="DeviceA",
            points=sample_llh_points
        )
        file2 = LLHFile(
            filename="2025_03_09_DeviceB_solution_20250309110000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="DeviceB",
            points=sample_llh_points
        )

        result = aggregate_surveys_by_date([file1, file2])

        assert len(result) == 1
        assert '2025-03-09' in result
        assert len(result['2025-03-09']) == 2

    def test_aggregate_multiple_dates(self, sample_llh_points):
        """Test aggregating files from multiple dates"""
        file1 = LLHFile(
            filename="2025_03_09_Device_solution_20250309100000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points
        )
        file2 = LLHFile(
            filename="2025_03_10_Device_solution_20250310100000.LLH",
            survey_date=datetime(2025, 3, 10),
            device_name="Device",
            points=sample_llh_points
        )
        file3 = LLHFile(
            filename="2025_03_11_Device_solution_20250311100000.LLH",
            survey_date=datetime(2025, 3, 11),
            device_name="Device",
            points=sample_llh_points
        )

        result = aggregate_surveys_by_date([file1, file2, file3])

        assert len(result) == 3
        assert '2025-03-09' in result
        assert '2025-03-10' in result
        assert '2025-03-11' in result

    def test_aggregate_empty_list(self):
        """Test aggregating an empty list of files"""
        result = aggregate_surveys_by_date([])
        assert result == {}


class TestGenerateSurveyMetadata:
    """Tests for generate_survey_metadata function"""

    def test_generate_metadata_structure(self, sample_llh_points):
        """Test that generated metadata has correct structure"""
        file1 = LLHFile(
            filename="2025_03_09_Device_solution_20250309100000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points
        )

        transect = Transect(
            transect_id="20250309_Device_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points
        )

        surveys = {'2025-03-09': [file1]}
        transects_by_date = {'2025-03-09': [transect]}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "surveys.json")
            generate_survey_metadata(surveys, transects_by_date, output_path)

            with open(output_path) as f:
                metadata = json.load(f)

            # Check top-level structure
            assert 'surveys' in metadata
            assert 'summary' in metadata
            assert 'generated_at' in metadata

            # Check summary structure
            assert 'total_survey_dates' in metadata['summary']
            assert 'date_range' in metadata['summary']
            assert 'total_transects' in metadata['summary']
            assert 'total_points' in metadata['summary']

    def test_generate_metadata_survey_entry(self, sample_llh_points):
        """Test that survey entries have correct fields"""
        file1 = LLHFile(
            filename="2025_03_09_Device_solution_20250309100000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points
        )

        transect = Transect(
            transect_id="20250309_Device_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points
        )

        surveys = {'2025-03-09': [file1]}
        transects_by_date = {'2025-03-09': [transect]}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "surveys.json")
            generate_survey_metadata(surveys, transects_by_date, output_path)

            with open(output_path) as f:
                metadata = json.load(f)

            survey = metadata['surveys'][0]

            # Check required fields
            assert survey['date'] == '2025-03-09'
            assert 'files' in survey
            assert 'devices' in survey
            assert 'total_points' in survey
            assert 'total_transects' in survey
            assert 'rtk_fix_percentage' in survey
            assert 'quality_counts' in survey
            assert 'bounds' in survey
            assert 'transect_stats' in survey

    def test_generate_metadata_point_counts(self, sample_llh_points):
        """Test that point counts are calculated correctly"""
        file1 = LLHFile(
            filename="2025_03_09_DeviceA_solution_20250309100000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="DeviceA",
            points=sample_llh_points[:50]  # 50 points
        )
        file2 = LLHFile(
            filename="2025_03_09_DeviceB_solution_20250309110000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="DeviceB",
            points=sample_llh_points[:30]  # 30 points
        )

        surveys = {'2025-03-09': [file1, file2]}
        transects_by_date = {'2025-03-09': []}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "surveys.json")
            generate_survey_metadata(surveys, transects_by_date, output_path)

            with open(output_path) as f:
                metadata = json.load(f)

            survey = metadata['surveys'][0]
            # Total should be 50 + 30 = 80
            assert survey['total_points'] == 80

    def test_generate_metadata_quality_counts(self, sample_llh_points):
        """Test that quality counts are aggregated correctly"""
        file1 = LLHFile(
            filename="2025_03_09_Device_solution_20250309100000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points
        )

        surveys = {'2025-03-09': [file1]}
        transects_by_date = {'2025-03-09': []}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "surveys.json")
            generate_survey_metadata(surveys, transects_by_date, output_path)

            with open(output_path) as f:
                metadata = json.load(f)

            quality_counts = metadata['surveys'][0]['quality_counts']

            # Based on fixture: quality=1 if i % 3 != 0 else 2
            assert quality_counts['fix'] == 66  # RTK fix (quality=1)
            assert quality_counts['float'] == 34  # Float (quality=2)
            assert quality_counts['single'] == 0  # Single (quality=5)

    def test_generate_metadata_bounds(self, sample_llh_points):
        """Test that bounds are calculated correctly"""
        file1 = LLHFile(
            filename="2025_03_09_Device_solution_20250309100000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points
        )

        surveys = {'2025-03-09': [file1]}
        transects_by_date = {'2025-03-09': []}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "surveys.json")
            generate_survey_metadata(surveys, transects_by_date, output_path)

            with open(output_path) as f:
                metadata = json.load(f)

            bounds = metadata['surveys'][0]['bounds']

            # Bounds should contain all point coordinates
            all_lats = [p.lat for p in sample_llh_points]
            all_lons = [p.lon for p in sample_llh_points]

            assert bounds['min_lat'] == min(all_lats)
            assert bounds['max_lat'] == max(all_lats)
            assert bounds['min_lon'] == min(all_lons)
            assert bounds['max_lon'] == max(all_lons)

    def test_generate_metadata_transect_stats(self, sample_llh_points):
        """Test that transect statistics are calculated correctly"""
        file1 = LLHFile(
            filename="2025_03_09_Device_solution_20250309100000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points
        )

        transect1 = Transect(
            transect_id="20250309_Device_T001",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points[:60]
        )
        transect2 = Transect(
            transect_id="20250309_Device_T002",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points[60:]
        )

        surveys = {'2025-03-09': [file1]}
        transects_by_date = {'2025-03-09': [transect1, transect2]}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "surveys.json")
            generate_survey_metadata(surveys, transects_by_date, output_path)

            with open(output_path) as f:
                metadata = json.load(f)

            survey = metadata['surveys'][0]
            stats = survey['transect_stats']

            assert survey['total_transects'] == 2
            assert 'total_length_meters' in stats
            assert 'avg_length_meters' in stats
            assert 'min_length_meters' in stats
            assert 'max_length_meters' in stats
            assert stats['total_length_meters'] > 0

    def test_generate_metadata_date_sorting(self, sample_llh_points):
        """Test that surveys are sorted by date"""
        files = []
        for day in [15, 10, 20, 5]:  # Out of order
            files.append(LLHFile(
                filename=f"2025_03_{day:02d}_Device_solution_202503{day:02d}100000.LLH",
                survey_date=datetime(2025, 3, day),
                device_name="Device",
                points=sample_llh_points
            ))

        surveys = aggregate_surveys_by_date(files)
        transects_by_date = {date: [] for date in surveys.keys()}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "surveys.json")
            generate_survey_metadata(surveys, transects_by_date, output_path)

            with open(output_path) as f:
                metadata = json.load(f)

            dates = [s['date'] for s in metadata['surveys']]
            # Should be sorted chronologically
            assert dates == sorted(dates)
            assert dates == ['2025-03-05', '2025-03-10', '2025-03-15', '2025-03-20']

    def test_generate_metadata_summary(self, sample_llh_points):
        """Test that summary statistics are correct"""
        files = []
        for day in [9, 10]:
            files.append(LLHFile(
                filename=f"2025_03_{day:02d}_Device_solution_202503{day:02d}100000.LLH",
                survey_date=datetime(2025, 3, day),
                device_name="Device",
                points=sample_llh_points
            ))

        surveys = aggregate_surveys_by_date(files)

        transects_by_date = {
            '2025-03-09': [
                Transect("T1", datetime(2025, 3, 9), "Device", sample_llh_points)
            ],
            '2025-03-10': [
                Transect("T2", datetime(2025, 3, 10), "Device", sample_llh_points),
                Transect("T3", datetime(2025, 3, 10), "Device", sample_llh_points)
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "surveys.json")
            generate_survey_metadata(surveys, transects_by_date, output_path)

            with open(output_path) as f:
                metadata = json.load(f)

            summary = metadata['summary']

            assert summary['total_survey_dates'] == 2
            assert summary['total_transects'] == 3  # 1 + 2
            assert summary['total_points'] == 200  # 100 + 100
            assert summary['date_range']['start'] == '2025-03-09'
            assert summary['date_range']['end'] == '2025-03-10'

    def test_generate_metadata_no_transects(self, sample_llh_points):
        """Test metadata generation when there are no transects"""
        file1 = LLHFile(
            filename="2025_03_09_Device_solution_20250309100000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="Device",
            points=sample_llh_points
        )

        surveys = {'2025-03-09': [file1]}
        transects_by_date = {'2025-03-09': []}  # No transects

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "surveys.json")
            generate_survey_metadata(surveys, transects_by_date, output_path)

            with open(output_path) as f:
                metadata = json.load(f)

            survey = metadata['surveys'][0]
            stats = survey['transect_stats']

            assert survey['total_transects'] == 0
            assert stats['total_length_meters'] == 0
            assert stats['avg_length_meters'] == 0

    def test_generate_metadata_device_list(self, sample_llh_points):
        """Test that device names are correctly listed"""
        file1 = LLHFile(
            filename="2025_03_09_DeviceA_solution_20250309100000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="DeviceA",
            points=sample_llh_points
        )
        file2 = LLHFile(
            filename="2025_03_09_DeviceB_solution_20250309110000.LLH",
            survey_date=datetime(2025, 3, 9),
            device_name="DeviceB",
            points=sample_llh_points
        )

        surveys = {'2025-03-09': [file1, file2]}
        transects_by_date = {'2025-03-09': []}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "surveys.json")
            generate_survey_metadata(surveys, transects_by_date, output_path)

            with open(output_path) as f:
                metadata = json.load(f)

            devices = metadata['surveys'][0]['devices']
            assert sorted(devices) == ['DeviceA', 'DeviceB']
