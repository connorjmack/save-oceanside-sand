# Data Processing Scripts

Python scripts for processing beach survey LLH files into optimized formats for frontend visualization.

## Scripts Overview

### 1. `parse_llh.py`
Parses raw LLH files from Emlid Reach GNSS receivers.

**Features:**
- Extracts GPS points with position, quality, and metadata
- Handles multiple file naming conventions
- Provides data validation and error reporting
- Can be used standalone or imported as a module

**Usage:**
```bash
python scripts/parse_llh.py data/LLH
```

**Classes:**
- `LLHPoint`: Represents a single GPS point with all attributes
- `LLHFile`: Represents a parsed LLH file with metadata
- `parse_llh_file()`: Parse a single LLH file
- `parse_all_llh_files()`: Parse entire directory

### 2. `generate_transects.py`
Segments continuous GPS point streams into discrete beach transects.

**Segmentation Algorithm:**
- **Time gaps**: Splits when gap between consecutive points > 30 seconds
- **Direction changes**: Splits when bearing changes > 90 degrees (turnaround detection)
- **Minimum length**: Discards segments with < 50 points

**Outputs:**
- GeoJSON LineString features for map display
- Profile data (distance vs elevation) for cross-section charts

**Usage:**
```bash
python scripts/generate_transects.py data/LLH
```

**Classes:**
- `Transect`: Represents a single beach transect line
- `segment_points_into_transects()`: Main segmentation algorithm
- `generate_transects_geojson()`: Create GeoJSON output
- `generate_profile_data()`: Create per-transect profile JSON

### 3. `process_surveys.py` (Main Pipeline)
Orchestrates the complete data processing workflow.

**Pipeline Steps:**
1. Parse all LLH files from `data/LLH/`
2. Group files by survey date
3. Segment points into transects
4. Generate output files in `processed/` directory

**Outputs:**
- `processed/surveys.json`: Survey metadata index with statistics
- `processed/transects.geojson`: All transects as GeoJSON FeatureCollection
- `processed/profiles/*.json`: Individual transect profile data

**Usage:**
```bash
python scripts/process_surveys.py
# or specify custom data directory:
python scripts/process_surveys.py /path/to/LLH/files
```

## Installation

```bash
pip install -r requirements.txt
```

**Required dependencies:**
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `geopandas` - Geospatial data handling
- `shapely` - Geometric operations

## Data Flow

```
data/LLH/*.LLH
    ↓
[parse_llh.py] → Parse GPS points
    ↓
[generate_transects.py] → Segment into transects
    ↓
[process_surveys.py] → Aggregate and output
    ↓
processed/
    ├── surveys.json          (metadata index)
    ├── transects.geojson     (map geometries)
    └── profiles/             (elevation profiles)
        ├── 20221103_Device1_T001.json
        ├── 20221103_Device1_T002.json
        └── ...
```

## Output Format Details

### surveys.json
```json
{
  "surveys": [
    {
      "date": "2022-11-03",
      "files": ["2022_11_03_Device_solution.LLH"],
      "devices": ["Device1"],
      "total_points": 15234,
      "total_transects": 8,
      "rtk_fix_percentage": 87.3,
      "quality_counts": { "fix": 13312, "float": 1844, "single": 78 },
      "bounds": { "min_lat": 33.15, "max_lat": 33.19, ... },
      "transect_stats": { ... }
    }
  ],
  "summary": {
    "total_survey_dates": 58,
    "date_range": { "start": "2022-11-03", "end": "2026-01-18" },
    "total_transects": 462,
    "total_points": 1234567
  }
}
```

### transects.geojson
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "20221103_Device1_T001",
      "geometry": {
        "type": "LineString",
        "coordinates": [[-117.352, 33.157, 2.45], ...]
      },
      "properties": {
        "transect_id": "20221103_Device1_T001",
        "survey_date": "2022-11-03",
        "point_count": 1234,
        "length_meters": 285.6,
        "min_elevation": -0.8,
        "max_elevation": 12.3,
        "rtk_fix_percentage": 92.1,
        ...
      }
    }
  ]
}
```

### profiles/[transect_id].json
```json
{
  "transect_id": "20221103_Device1_T001",
  "survey_date": "2022-11-03",
  "distances": [0, 0.23, 0.51, ...],
  "elevations": [2.45, 2.48, 2.52, ...],
  "qualities": [1, 1, 1, ...],
  "coordinates": [[-117.352, 33.157], ...]
}
```

## Configuration Parameters

### Transect Segmentation Thresholds

Adjust in `process_surveys.py` → `segment_points_into_transects()`:

- `time_gap_threshold`: Default 30 seconds
  - Increase to merge more points into single transects
  - Decrease for stricter separation

- `direction_change_threshold`: Default 90 degrees
  - Increase to allow more directional variation
  - Decrease for stricter straight-line transects

- `min_points_per_transect`: Default 50 points
  - Increase to filter out short segments
  - Decrease to keep more transects

## Troubleshooting

**No LLH files found:**
- Ensure files are in `data/LLH/` directory
- Check file extensions (`.LLH` or `.llh`)

**Parsing errors:**
- Check LLH file format (space-delimited, 15 columns)
- Verify filename follows convention: `YYYY_MM_DD_Device_solution_TIMESTAMP.LLH`

**Too many/too few transects:**
- Adjust segmentation thresholds (see Configuration Parameters above)
- Check for data quality issues (gaps, noise)

**Performance issues:**
- Processing is memory-intensive for large datasets
- Consider processing subsets if encountering memory errors

## Next Steps

After running `process_surveys.py`, the `processed/` directory contains all data needed for the frontend React application (Phase 2).
