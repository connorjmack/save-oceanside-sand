"""
Shared pytest fixtures for Phase 1 tests
"""

import os
import sys
import tempfile
import pytest
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utilities.parse_llh import LLHPoint, LLHFile


@pytest.fixture
def sample_llh_point():
    """Create a sample LLHPoint for testing"""
    return LLHPoint(
        timestamp=datetime(2025, 3, 9, 19, 55, 28, 197000),
        lat=33.201084400,
        lon=-117.387366944,
        height=-7.4818,
        quality=1,
        num_satellites=28,
        sdn=0.01,
        sde=0.01,
        sdu=0.01,
        sdne=0.0,
        sdeu=0.0,
        sdun=0.0,
        age=1.2,
        ratio=0.0
    )


@pytest.fixture
def sample_llh_points():
    """Create a list of sample LLHPoints for testing"""
    base_time = datetime(2025, 3, 9, 19, 55, 28)
    points = []

    for i in range(100):
        point = LLHPoint(
            timestamp=datetime(2025, 3, 9, 19, 55, 28 + i // 5, (i % 5) * 200000),
            lat=33.201084 + i * 0.00001,  # Moving north
            lon=-117.387366 - i * 0.00001,  # Moving west
            height=-7.5 + i * 0.01,
            quality=1 if i % 3 != 0 else 2,
            num_satellites=28,
            sdn=0.01,
            sde=0.01,
            sdu=0.01,
            sdne=0.0,
            sdeu=0.0,
            sdun=0.0,
            age=1.2,
            ratio=0.0
        )
        points.append(point)

    return points


@pytest.fixture
def sample_llh_file(sample_llh_points):
    """Create a sample LLHFile for testing"""
    return LLHFile(
        filename="2025_03_09_TestDevice_solution_20250309195528.LLH",
        survey_date=datetime(2025, 3, 9),
        device_name="TestDevice",
        points=sample_llh_points
    )


@pytest.fixture
def temp_llh_file():
    """Create a temporary LLH file with sample data"""
    content = """2025/03/09 19:55:28.197   33.201084400 -117.387366944    -7.4818   1  28   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   1.20    0.0
2025/03/09 19:55:28.397   33.201083297 -117.387366892    -7.6060   1  28   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   0.00    0.0
2025/03/09 19:55:28.600   33.201083394 -117.387366952    -7.6016   2  25   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   0.00    0.0
2025/03/09 19:55:28.800   33.201083422 -117.387367018    -7.6129   1  28   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   0.00    0.0
2025/03/09 19:55:29.000   33.201083466 -117.387367019    -7.6112   5  15   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   0.00    0.0"""

    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.LLH',
        prefix='2025_03_09_TestDevice_solution_20250309195528',
        delete=False
    ) as f:
        f.write(content)
        filepath = f.name

    yield filepath

    # Cleanup
    os.unlink(filepath)


@pytest.fixture
def temp_llh_dir():
    """Create a temporary directory with multiple LLH files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # File 1 - standard format
        content1 = """2025/03/09 19:55:28.197   33.201084400 -117.387366944    -7.4818   1  28   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   1.20    0.0
2025/03/09 19:55:28.397   33.201083297 -117.387366892    -7.6060   1  28   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   0.00    0.0"""

        filepath1 = os.path.join(tmpdir, "2025_03_09_DeviceA_solution_20250309195528.LLH")
        with open(filepath1, 'w') as f:
            f.write(content1)

        # File 2 - same date, different device
        content2 = """2025/03/09 20:10:00.000   33.202000000 -117.388000000    -8.0000   1  30   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   1.00    0.0
2025/03/09 20:10:00.200   33.202001000 -117.388001000    -8.0100   1  30   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   1.00    0.0"""

        filepath2 = os.path.join(tmpdir, "2025_03_09_DeviceB_solution_20250309201000.LLH")
        with open(filepath2, 'w') as f:
            f.write(content2)

        # File 3 - different date
        content3 = """2025/03/10 10:00:00.000   33.203000000 -117.389000000    -9.0000   1  25   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   1.00    0.0
2025/03/10 10:00:00.200   33.203001000 -117.389001000    -9.0100   2  20   0.0100   0.0100   0.0100   0.0000   0.0000   0.0000   1.00    0.0"""

        filepath3 = os.path.join(tmpdir, "2025_03_10_DeviceA_solution_20250310100000.LLH")
        with open(filepath3, 'w') as f:
            f.write(content3)

        yield tmpdir


@pytest.fixture
def points_with_time_gap():
    """Create points with a time gap for transect segmentation testing"""
    points = []

    # First segment: 60 points over 12 seconds
    for i in range(60):
        point = LLHPoint(
            timestamp=datetime(2025, 3, 9, 19, 55, 28 + i // 5, (i % 5) * 200000),
            lat=33.201084 + i * 0.00001,
            lon=-117.387366,
            height=-7.5,
            quality=1,
            num_satellites=28,
            sdn=0.01, sde=0.01, sdu=0.01,
            sdne=0.0, sdeu=0.0, sdun=0.0,
            age=1.2, ratio=0.0
        )
        points.append(point)

    # Gap of 45 seconds (> 30s threshold)

    # Second segment: 60 points starting 45 seconds later
    for i in range(60):
        point = LLHPoint(
            timestamp=datetime(2025, 3, 9, 19, 56, 25 + i // 5, (i % 5) * 200000),
            lat=33.202084 + i * 0.00001,
            lon=-117.388366,
            height=-8.0,
            quality=1,
            num_satellites=28,
            sdn=0.01, sde=0.01, sdu=0.01,
            sdne=0.0, sdeu=0.0, sdun=0.0,
            age=1.2, ratio=0.0
        )
        points.append(point)

    return points


@pytest.fixture
def points_with_direction_change():
    """Create points with a direction reversal for transect segmentation testing"""
    points = []

    # First segment: 60 points moving north
    for i in range(60):
        point = LLHPoint(
            timestamp=datetime(2025, 3, 9, 19, 55, 28 + i // 5, (i % 5) * 200000),
            lat=33.201084 + i * 0.0001,  # Moving north
            lon=-117.387366,
            height=-7.5,
            quality=1,
            num_satellites=28,
            sdn=0.01, sde=0.01, sdu=0.01,
            sdne=0.0, sdeu=0.0, sdun=0.0,
            age=1.2, ratio=0.0
        )
        points.append(point)

    # Second segment: 60 points moving south (direction change > 90 degrees)
    for i in range(60):
        point = LLHPoint(
            timestamp=datetime(2025, 3, 9, 19, 55, 40 + i // 5, (i % 5) * 200000),
            lat=33.207084 - i * 0.0001,  # Moving south
            lon=-117.387366,
            height=-7.5,
            quality=1,
            num_satellites=28,
            sdn=0.01, sde=0.01, sdu=0.01,
            sdne=0.0, sdeu=0.0, sdun=0.0,
            age=1.2, ratio=0.0
        )
        points.append(point)

    return points
