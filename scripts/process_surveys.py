"""
Survey Processor - Main Data Pipeline Script

Orchestrates the complete data processing pipeline:
1. Parse all LLH files from data/raw/LLH directory
2. Group points into transects
3. Generate survey metadata index
4. Output processed data files for frontend consumption

Outputs:
- data/processed/surveys.json: Metadata index of all survey dates
- data/processed/transects.geojson: GeoJSON of all transects for map display
- data/processed/profiles/: Individual transect profile data
"""

import os
import json
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utilities.parse_llh import parse_all_llh_files, LLHFile
from scripts.generate_transects import segment_points_into_transects, Transect, generate_transects_geojson, generate_profile_data


def aggregate_surveys_by_date(llh_files: List[LLHFile]) -> Dict[str, List[LLHFile]]:
    """
    Group LLH files by survey date.

    Multiple LLH files may exist for the same survey date (different devices,
    multiple solution files, etc.). This function aggregates them.

    Args:
        llh_files: List of parsed LLH files

    Returns:
        Dictionary mapping date string (YYYY-MM-DD) to list of LLH files
    """
    surveys = defaultdict(list)

    for llh_file in llh_files:
        date_key = llh_file.survey_date.strftime('%Y-%m-%d')
        surveys[date_key].append(llh_file)

    return dict(surveys)


def generate_survey_metadata(surveys: Dict[str, List[LLHFile]],
                            transects_by_date: Dict[str, List[Transect]],
                            output_path: str):
    """
    Generate surveys.json metadata index.

    This file provides a summary of all available survey dates with statistics,
    enabling the frontend to build timeline controls and lazy-load data.

    Args:
        surveys: Dictionary of survey date -> LLH files
        transects_by_date: Dictionary of survey date -> transects
        output_path: Path to output JSON file
    """
    survey_list = []

    for date_str in sorted(surveys.keys()):
        llh_files = surveys[date_str]
        transects = transects_by_date.get(date_str, [])

        # Aggregate statistics across all files for this date
        total_points = sum(f.point_count for f in llh_files)
        total_transects = len(transects)

        # Calculate quality statistics
        all_qualities = []
        for f in llh_files:
            for point in f.points:
                all_qualities.append(point.quality)

        rtk_fix_count = sum(1 for q in all_qualities if q == 1)
        rtk_fix_percentage = (rtk_fix_count / len(all_qualities) * 100) if all_qualities else 0

        # Get device names
        devices = sorted(set(f.device_name for f in llh_files))

        # Calculate spatial bounds
        all_lats = []
        all_lons = []
        for f in llh_files:
            for point in f.points:
                all_lats.append(point.lat)
                all_lons.append(point.lon)

        bounds = {
            'min_lat': min(all_lats) if all_lats else 0,
            'max_lat': max(all_lats) if all_lats else 0,
            'min_lon': min(all_lons) if all_lons else 0,
            'max_lon': max(all_lons) if all_lons else 0
        }

        # Calculate transect statistics
        if transects:
            total_length = sum(t.length_meters() for t in transects)
            avg_transect_length = total_length / len(transects)
            min_length = min(t.length_meters() for t in transects)
            max_length = max(t.length_meters() for t in transects)
        else:
            total_length = 0
            avg_transect_length = 0
            min_length = 0
            max_length = 0

        survey_entry = {
            'date': date_str,
            'files': [f.filename for f in llh_files],
            'devices': devices,
            'total_points': total_points,
            'total_transects': total_transects,
            'rtk_fix_percentage': round(rtk_fix_percentage, 1),
            'quality_counts': {
                'fix': sum(1 for q in all_qualities if q == 1),
                'float': sum(1 for q in all_qualities if q == 2),
                'single': sum(1 for q in all_qualities if q == 5)
            },
            'bounds': bounds,
            'transect_stats': {
                'total_length_meters': round(total_length, 2),
                'avg_length_meters': round(avg_transect_length, 2),
                'min_length_meters': round(min_length, 2),
                'max_length_meters': round(max_length, 2)
            }
        }

        survey_list.append(survey_entry)

    # Create metadata object
    metadata = {
        'surveys': survey_list,
        'summary': {
            'total_survey_dates': len(survey_list),
            'date_range': {
                'start': survey_list[0]['date'] if survey_list else None,
                'end': survey_list[-1]['date'] if survey_list else None
            },
            'total_transects': sum(s['total_transects'] for s in survey_list),
            'total_points': sum(s['total_points'] for s in survey_list)
        },
        'generated_at': datetime.utcnow().isoformat()
    }

    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Generated survey metadata: {output_path}")
    print(f"  Total survey dates: {metadata['summary']['total_survey_dates']}")
    print(f"  Date range: {metadata['summary']['date_range']['start']} to {metadata['summary']['date_range']['end']}")
    print(f"  Total transects: {metadata['summary']['total_transects']}")
    print(f"  Total points: {metadata['summary']['total_points']:,}")


def main():
    """Main processing pipeline"""
    import sys

    # Configuration
    data_dir = sys.argv[1] if len(sys.argv) > 1 else 'data/raw/LLH'
    output_dir = 'data/processed'

    print("="*60)
    print("OCEANSIDE BEACH SURVEY DATA PROCESSOR")
    print("="*60)

    # Step 1: Parse all LLH files
    print("\n[1/4] Parsing LLH files...")
    llh_files = parse_all_llh_files(data_dir)

    if not llh_files:
        print("Error: No LLH files were successfully parsed")
        return

    # Step 2: Group by survey date
    print("\n[2/4] Grouping surveys by date...")
    surveys = aggregate_surveys_by_date(llh_files)
    print(f"  Found {len(surveys)} unique survey dates")

    # Step 3: Generate transects
    print("\n[3/4] Segmenting points into transects...")
    all_transects = []
    transects_by_date = defaultdict(list)

    for date_str, date_llh_files in surveys.items():
        date_transects = []
        for llh_file in date_llh_files:
            transects = segment_points_into_transects(
                llh_file,
                time_gap_threshold=30.0,
                direction_change_threshold=90.0,
                min_points_per_transect=50
            )
            date_transects.extend(transects)

        all_transects.extend(date_transects)
        transects_by_date[date_str] = date_transects
        print(f"  {date_str}: {len(date_transects)} transects from {len(date_llh_files)} files")

    print(f"\n  Total transects: {len(all_transects)}")

    # Step 4: Generate output files
    print("\n[4/4] Generating output files...")

    # Generate transects GeoJSON
    generate_transects_geojson(all_transects, f'{output_dir}/transects.geojson')

    # Generate profile data
    generate_profile_data(all_transects, f'{output_dir}/profiles')

    # Generate survey metadata
    generate_survey_metadata(surveys, transects_by_date, f'{output_dir}/surveys.json')

    print("\n" + "="*60)
    print("PROCESSING COMPLETE!")
    print("="*60)
    print(f"\nOutput files generated in '{output_dir}/' directory:")
    print(f"  - surveys.json: Survey metadata index ({len(surveys)} dates)")
    print(f"  - transects.geojson: Map transect geometries ({len(all_transects)} transects)")
    print(f"  - profiles/: Individual transect data ({len(all_transects)} files)")
    print("\nReady for frontend consumption!")


if __name__ == '__main__':
    main()
