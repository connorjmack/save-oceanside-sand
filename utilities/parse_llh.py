"""
LLH File Parser for Emlid Reach GNSS Data

Parses space-delimited LLH files from Emlid Reach receivers used in RTK beach surveys.
Each LLH file contains continuous GPS point data with position and quality metrics.

File format:
YYYY/MM/DD HH:MM:SS.sss lat lon height Q ns sdn sde sdu sdne sdeu sdun age ratio

Where:
- Columns 1-2: Date and time (UTC)
- Column 3: Latitude (decimal degrees)
- Column 4: Longitude (decimal degrees)
- Column 5: Ellipsoidal height (meters, WGS84)
- Column 6: Quality flag (1=RTK fix, 2=float, 5=single)
- Column 7: Number of satellites
- Columns 8-13: Standard deviations and correlations
- Column 14: Age of differential
- Column 15: Ratio factor
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd


class LLHPoint:
    """Represents a single GPS point from an LLH file"""

    def __init__(self, timestamp: datetime, lat: float, lon: float, height: float,
                 quality: int, num_satellites: int, sdn: float, sde: float, sdu: float,
                 sdne: float, sdeu: float, sdun: float, age: float, ratio: float):
        self.timestamp = timestamp
        self.lat = lat
        self.lon = lon
        self.height = height
        self.quality = quality
        self.num_satellites = num_satellites
        self.sdn = sdn
        self.sde = sde
        self.sdu = sdu
        self.sdne = sdne
        self.sdeu = sdeu
        self.sdun = sdun
        self.age = age
        self.ratio = ratio

    def to_dict(self) -> Dict:
        """Convert point to dictionary format"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'lat': self.lat,
            'lon': self.lon,
            'height': self.height,
            'quality': self.quality,
            'num_satellites': self.num_satellites,
            'sdn': self.sdn,
            'sde': self.sde,
            'sdu': self.sdu,
            'sdne': self.sdne,
            'sdeu': self.sdeu,
            'sdun': self.sdun,
            'age': self.age,
            'ratio': self.ratio
        }


class LLHFile:
    """Represents a parsed LLH file with metadata"""

    def __init__(self, filename: str, survey_date: datetime, device_name: str,
                 points: List[LLHPoint]):
        self.filename = filename
        self.survey_date = survey_date
        self.device_name = device_name
        self.points = points

    @property
    def point_count(self) -> int:
        return len(self.points)

    @property
    def quality_counts(self) -> Dict[int, int]:
        """Count points by quality flag"""
        counts = {1: 0, 2: 0, 5: 0}
        for point in self.points:
            if point.quality in counts:
                counts[point.quality] += 1
        return counts

    def to_dataframe(self) -> pd.DataFrame:
        """Convert points to pandas DataFrame"""
        return pd.DataFrame([point.to_dict() for point in self.points])


def parse_llh_filename(filename: str) -> Optional[Dict[str, str]]:
    """
    Extract metadata from LLH filename.

    Expected format: YYYY_MM_DD_[DeviceName]_solution_YYYYMMDDHHMMSS.LLH
    Example: 2025_03_09_SOS_Emlid_R_solution_20250309195455.LLH

    Returns dict with 'date', 'device_name', 'solution_timestamp' or None if invalid
    """
    try:
        # Remove .LLH extension
        base = filename.replace('.LLH', '').replace('.llh', '')
        parts = base.split('_')

        if len(parts) < 5:
            return None

        # Extract date from first three parts
        year, month, day = parts[0], parts[1], parts[2]
        survey_date = f"{year}-{month}-{day}"

        # Find 'solution' keyword to split device name and timestamp
        if 'solution' in parts:
            solution_idx = parts.index('solution')
            device_name = '_'.join(parts[3:solution_idx])
            solution_timestamp = parts[solution_idx + 1] if solution_idx + 1 < len(parts) else ''
        else:
            # Fallback if no 'solution' keyword
            device_name = '_'.join(parts[3:-1])
            solution_timestamp = parts[-1]

        return {
            'date': survey_date,
            'device_name': device_name,
            'solution_timestamp': solution_timestamp
        }
    except Exception:
        return None


def parse_llh_file(filepath: str) -> Optional[LLHFile]:
    """
    Parse a single LLH file.

    Args:
        filepath: Path to the LLH file

    Returns:
        LLHFile object or None if parsing fails
    """
    filename = os.path.basename(filepath)

    # Extract metadata from filename
    metadata = parse_llh_filename(filename)
    if not metadata:
        print(f"Warning: Could not parse filename: {filename}")
        return None

    try:
        survey_date = datetime.strptime(metadata['date'], '%Y-%m-%d')
        device_name = metadata['device_name']
    except ValueError:
        print(f"Warning: Invalid date in filename: {filename}")
        return None

    # Parse file contents
    points = []

    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 15:
                    print(f"Warning: Line {line_num} in {filename} has insufficient columns")
                    continue

                try:
                    # Parse date and time
                    date_str = parts[0]
                    time_str = parts[1]
                    timestamp = datetime.strptime(f"{date_str} {time_str}",
                                                 "%Y/%m/%d %H:%M:%S.%f")

                    # Parse position and quality
                    lat = float(parts[2])
                    lon = float(parts[3])
                    height = float(parts[4])
                    quality = int(parts[5])
                    num_satellites = int(parts[6])

                    # Parse standard deviations
                    sdn = float(parts[7])
                    sde = float(parts[8])
                    sdu = float(parts[9])
                    sdne = float(parts[10])
                    sdeu = float(parts[11])
                    sdun = float(parts[12])

                    # Parse age and ratio
                    age = float(parts[13])
                    ratio = float(parts[14])

                    point = LLHPoint(
                        timestamp=timestamp,
                        lat=lat,
                        lon=lon,
                        height=height,
                        quality=quality,
                        num_satellites=num_satellites,
                        sdn=sdn,
                        sde=sde,
                        sdu=sdu,
                        sdne=sdne,
                        sdeu=sdeu,
                        sdun=sdun,
                        age=age,
                        ratio=ratio
                    )
                    points.append(point)

                except (ValueError, IndexError) as e:
                    print(f"Warning: Could not parse line {line_num} in {filename}: {e}")
                    continue

        if not points:
            print(f"Warning: No valid points found in {filename}")
            return None

        return LLHFile(
            filename=filename,
            survey_date=survey_date,
            device_name=device_name,
            points=points
        )

    except Exception as e:
        print(f"Error reading file {filename}: {e}")
        return None


def parse_all_llh_files(data_dir: str) -> List[LLHFile]:
    """
    Parse all LLH files in a directory.

    Args:
        data_dir: Path to directory containing LLH files

    Returns:
        List of successfully parsed LLHFile objects
    """
    llh_files = []

    if not os.path.exists(data_dir):
        print(f"Error: Directory not found: {data_dir}")
        return []

    # Find all .LLH files (case insensitive)
    all_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.lower().endswith('.llh'):
                all_files.append(os.path.join(root, file))

    print(f"Found {len(all_files)} LLH files")

    # Parse each file
    for i, filepath in enumerate(all_files, 1):
        if i % 10 == 0:
            print(f"Processing file {i}/{len(all_files)}...")

        llh_file = parse_llh_file(filepath)
        if llh_file:
            llh_files.append(llh_file)

    print(f"Successfully parsed {len(llh_files)} files")
    return llh_files


if __name__ == '__main__':
    # Example usage
    import sys

    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = 'data/raw/LLH'

    print(f"Parsing LLH files from: {data_dir}")
    llh_files = parse_all_llh_files(data_dir)

    # Print summary statistics
    total_points = sum(f.point_count for f in llh_files)
    print(f"\nSummary:")
    print(f"  Files parsed: {len(llh_files)}")
    print(f"  Total points: {total_points:,}")

    if llh_files:
        dates = sorted(set(f.survey_date for f in llh_files))
        print(f"  Date range: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")
        print(f"  Unique survey dates: {len(dates)}")
