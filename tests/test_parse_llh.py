"""
Tests for parse_llh.py - LLH file parsing functionality
"""

import os
import sys
import tempfile
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utilities.parse_llh import (
    LLHPoint,
    LLHFile,
    parse_llh_filename,
    parse_llh_file,
    parse_all_llh_files
)


class TestLLHPoint:
    """Tests for LLHPoint class"""

    def test_point_creation(self, sample_llh_point):
        """Test creating an LLHPoint with all attributes"""
        point = sample_llh_point
        assert point.lat == 33.201084400
        assert point.lon == -117.387366944
        assert point.height == -7.4818
        assert point.quality == 1
        assert point.num_satellites == 28

    def test_point_to_dict(self, sample_llh_point):
        """Test converting LLHPoint to dictionary"""
        point_dict = sample_llh_point.to_dict()

        assert 'timestamp' in point_dict
        assert point_dict['lat'] == 33.201084400
        assert point_dict['lon'] == -117.387366944
        assert point_dict['height'] == -7.4818
        assert point_dict['quality'] == 1
        assert point_dict['num_satellites'] == 28
        assert point_dict['sdn'] == 0.01
        assert point_dict['sde'] == 0.01
        assert point_dict['sdu'] == 0.01

    def test_point_timestamp_iso_format(self, sample_llh_point):
        """Test that timestamp is converted to ISO format"""
        point_dict = sample_llh_point.to_dict()
        # Should be parseable as ISO format
        parsed = datetime.fromisoformat(point_dict['timestamp'])
        assert parsed == sample_llh_point.timestamp


class TestLLHFile:
    """Tests for LLHFile class"""

    def test_file_creation(self, sample_llh_file):
        """Test creating an LLHFile with all attributes"""
        llh_file = sample_llh_file
        assert llh_file.filename == "2025_03_09_TestDevice_solution_20250309195528.LLH"
        assert llh_file.device_name == "TestDevice"
        assert llh_file.survey_date == datetime(2025, 3, 9)

    def test_point_count(self, sample_llh_file):
        """Test point_count property"""
        assert sample_llh_file.point_count == 100

    def test_quality_counts(self, sample_llh_file):
        """Test quality_counts property"""
        counts = sample_llh_file.quality_counts
        assert 1 in counts
        assert 2 in counts
        assert 5 in counts
        # Based on fixture: quality=1 if i % 3 != 0 else 2
        # 100 points: 34 with quality=2, 66 with quality=1
        assert counts[1] == 66
        assert counts[2] == 34
        assert counts[5] == 0

    def test_to_dataframe(self, sample_llh_file):
        """Test converting to pandas DataFrame"""
        df = sample_llh_file.to_dataframe()
        assert len(df) == 100
        assert 'lat' in df.columns
        assert 'lon' in df.columns
        assert 'height' in df.columns
        assert 'quality' in df.columns
        assert 'timestamp' in df.columns


class TestParseFilename:
    """Tests for parse_llh_filename function"""

    def test_standard_filename_format(self):
        """Test parsing standard filename format"""
        filename = "2025_03_09_SOS_Emlid_R_solution_20250309195455.LLH"
        result = parse_llh_filename(filename)

        assert result is not None
        assert result['date'] == "2025-03-09"
        assert result['device_name'] == "SOS_Emlid_R"
        assert result['solution_timestamp'] == "20250309195455"

    def test_filename_with_simple_device_name(self):
        """Test parsing filename with simple device name"""
        filename = "2024_11_02_CPG_Reach_1_solution_20241103002622.LLH"
        result = parse_llh_filename(filename)

        assert result is not None
        assert result['date'] == "2024-11-02"
        assert result['device_name'] == "CPG_Reach_1"
        assert result['solution_timestamp'] == "20241103002622"

    def test_lowercase_extension(self):
        """Test parsing filename with lowercase .llh extension"""
        filename = "2025_03_09_TestDevice_solution_20250309195528.llh"
        result = parse_llh_filename(filename)

        assert result is not None
        assert result['date'] == "2025-03-09"

    def test_invalid_filename_too_few_parts(self):
        """Test that invalid filenames return None"""
        filename = "invalid_file.LLH"
        result = parse_llh_filename(filename)
        assert result is None

    def test_invalid_filename_no_extension(self):
        """Test filename without solution keyword fallback"""
        filename = "2025_03_09_DeviceName_20250309195528.LLH"
        result = parse_llh_filename(filename)
        # Should still work using fallback logic
        assert result is not None
        assert result['date'] == "2025-03-09"


class TestParseLLHFile:
    """Tests for parse_llh_file function"""

    def test_parse_valid_file(self, temp_llh_file):
        """Test parsing a valid LLH file"""
        result = parse_llh_file(temp_llh_file)

        assert result is not None
        assert result.point_count == 5
        assert result.survey_date == datetime(2025, 3, 9)

    def test_parse_file_quality_distribution(self, temp_llh_file):
        """Test that quality flags are parsed correctly"""
        result = parse_llh_file(temp_llh_file)
        counts = result.quality_counts

        # Based on temp_llh_file fixture: 3 with Q=1, 1 with Q=2, 1 with Q=5
        assert counts[1] == 3
        assert counts[2] == 1
        assert counts[5] == 1

    def test_parse_file_coordinates(self, temp_llh_file):
        """Test that coordinates are parsed correctly"""
        result = parse_llh_file(temp_llh_file)

        first_point = result.points[0]
        assert abs(first_point.lat - 33.201084400) < 1e-8
        assert abs(first_point.lon - (-117.387366944)) < 1e-8
        assert abs(first_point.height - (-7.4818)) < 1e-4

    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist"""
        result = parse_llh_file("/nonexistent/path/file.LLH")
        assert result is None

    def test_parse_file_with_malformed_lines(self):
        """Test parsing a file with some malformed lines"""
        content = """2025/03/09 19:55:28.197   33.201084400 -117.387366944    -7.4818   1  28   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   1.20    0.0
invalid line with not enough columns
2025/03/09 19:55:28.397   33.201083297 -117.387366892    -7.6060   1  28   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   0.00    0.0
# This is a comment line
2025/03/09 19:55:28.600   33.201083394 -117.387366952    -7.6016   1  28   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   0.00    0.0"""

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.LLH',
            prefix='2025_03_09_Test_solution_20250309195528',
            delete=False
        ) as f:
            f.write(content)
            filepath = f.name

        try:
            result = parse_llh_file(filepath)
            # Should parse 3 valid lines (skipping invalid and comment)
            assert result is not None
            assert result.point_count == 3
        finally:
            os.unlink(filepath)

    def test_parse_empty_file(self):
        """Test parsing an empty file"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.LLH',
            prefix='2025_03_09_Test_solution_20250309195528',
            delete=False
        ) as f:
            f.write("")
            filepath = f.name

        try:
            result = parse_llh_file(filepath)
            # Empty file should return None
            assert result is None
        finally:
            os.unlink(filepath)


class TestParseAllLLHFiles:
    """Tests for parse_all_llh_files function"""

    def test_parse_directory(self, temp_llh_dir):
        """Test parsing all files in a directory"""
        results = parse_all_llh_files(temp_llh_dir)

        assert len(results) == 3
        # Check that files from different dates are included
        dates = sorted(set(f.survey_date for f in results))
        assert len(dates) == 2  # 2025-03-09 and 2025-03-10

    def test_parse_nonexistent_directory(self):
        """Test parsing a directory that doesn't exist"""
        results = parse_all_llh_files("/nonexistent/directory")
        assert results == []

    def test_parse_empty_directory(self):
        """Test parsing an empty directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = parse_all_llh_files(tmpdir)
            assert results == []

    def test_parse_directory_with_non_llh_files(self, temp_llh_dir):
        """Test that non-LLH files are ignored"""
        # Add a non-LLH file
        with open(os.path.join(temp_llh_dir, "readme.txt"), 'w') as f:
            f.write("This is not an LLH file")

        results = parse_all_llh_files(temp_llh_dir)
        # Should still only have 3 LLH files
        assert len(results) == 3
