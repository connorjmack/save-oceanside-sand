# Oceanside Beach Transect Visualizer

An interactive web application for visualizing GPS beach survey transects collected over time. The tool enables researchers to explore spatial coverage across survey sessions and analyze elevation changes at specific beach locations through time.

## Project Overview

This visualization tool processes LLH (Latitude, Longitude, Height) files from Emlid Reach GNSS receivers used in RTK beach surveys. The data spans **58 survey sessions from November 2022 to January 2026** covering beach transects in Oceanside, California (approximately 33.157°N, -117.352°W).

### Primary Use Cases

1. **Spatial Coverage Analysis**: View which beach areas were surveyed on any given date
2. **Temporal Comparison**: Step through time to see how survey coverage evolved
3. **Profile Analysis**: Examine elevation profiles along individual transects
4. **Beach Change Detection**: Compare transect elevations across multiple dates to identify erosion/accretion patterns

## Features

### Map View (Primary Interface)

- **Satellite basemap** with beach transects overlaid as colored polylines
- **Timeline slider/stepper** to navigate between survey dates (58 dates available)
- **Date display** showing current survey session
- **Transect rendering** with color-coding by:
  - Survey quality (fix type: RTK fixed vs float vs single)
  - Elevation (color ramp from low to high)
  - Or uniform color per survey date
- **Click interaction**: Click any transect to enter Profile View
- **Hover tooltips**: Show transect metadata (date, point count, length)
- **Animation mode**: Auto-play through dates to visualize coverage over time

### Profile View (Detail Interface)

- **Triggered by**: Clicking a transect on the map
- **Cross-section plot**: Distance along transect (x-axis) vs Elevation (y-axis)
- **Time series overlay**: Show the same transect location across ALL available dates
  - Each date as a separate line with distinct color
  - Legend showing dates with toggle visibility
- **Interactive features**:
  - Hover to see exact coordinates and elevation
  - Zoom/pan on the profile
  - Toggle individual dates on/off
- **Back button**: Return to Map View

### Data Controls

- **Date range filter**: Limit view to specific time period
- **Quality filter**: Show only high-quality (RTK fixed) points
- **Export**: Download currently visible data as CSV

## Data Format

### Input: LLH Files

Located in `data/LLH/`, files follow naming convention:
```
YYYY_MM_DD_[DeviceName]_solution_YYYYMMDDHHMMSS.LLH
```

Example: `2025_03_09_SOS_Emlid_R_solution_20250309195455.LLH`

### LLH File Structure

Space-delimited columns:
```
YYYY/MM/DD HH:MM:SS.sss  latitude  longitude  height  Q  ns  sdn  sde  sdu  sdne  sdeu  sdun  age  ratio
```

| Column | Description |
|--------|-------------|
| 1-2 | Date and time (UTC) |
| 3 | Latitude (decimal degrees) |
| 4 | Longitude (decimal degrees) |
| 5 | Ellipsoidal height (meters) |
| 6 | Quality flag (1=fix, 2=float, 5=single) |
| 7 | Number of satellites |
| 8-13 | Standard deviations (north, east, up, correlations) |
| 14 | Age of differential |
| 15 | Ratio factor |

### Data Statistics

- **Total LLH files**: 209
- **Unique survey dates**: 58
- **Date range**: November 3, 2022 → January 18, 2026
- **Location**: Oceanside, CA beach (pier area, ~33.19°N to 33.15°N)
- **Typical transect**: 500-2000 points, perpendicular to shoreline

## Technical Architecture

### Recommended Stack

**Frontend (Single Page Application)**:
- **React** with TypeScript for UI components
- **Mapbox GL JS** or **Leaflet** with satellite tiles for map rendering
- **Plotly.js** or **D3.js** for profile charts
- **Tailwind CSS** for styling

**Data Processing**:
- **Python scripts** to pre-process LLH files into optimized JSON/GeoJSON
- Aggregate by survey date
- Compute transect geometries and metadata
- Generate spatial index for fast lookups

### Data Pipeline

```
data/LLH/*.LLH  →  [Python Parser]  →  processed/
                                           ├── surveys.json       (metadata index)
                                           ├── transects.geojson  (map geometries)
                                           └── profiles/          (per-transect data)
                                                 ├── transect_001.json
                                                 └── ...
```

### File Structure

```
oceanside-beach-viz/
├── README.md
├── data/
│   ├── LLH/                    # Raw survey data (209 files)
│   └── zips/                   # Archived original zips
├── scripts/
│   ├── parse_llh.py            # LLH file parser
│   ├── process_surveys.py      # Aggregate by date
│   └── generate_transects.py   # Create transect geometries
├── processed/                  # Generated data for frontend
│   ├── surveys.json
│   ├── transects.geojson
│   └── profiles/
├── src/
│   ├── components/
│   │   ├── MapView.tsx         # Main map interface
│   │   ├── ProfileView.tsx     # Transect detail view
│   │   ├── Timeline.tsx        # Date navigation
│   │   └── TransectLayer.tsx   # Map transect rendering
│   ├── hooks/
│   │   ├── useTransectData.ts  # Data fetching/caching
│   │   └── useTimeline.ts      # Timeline state management
│   ├── utils/
│   │   └── geo.ts              # Coordinate transformations
│   └── App.tsx
├── public/
└── package.json
```

## User Flows

### Flow 1: Temporal Exploration

1. User opens app → Map View loads with most recent survey
2. User drags timeline slider to earlier date
3. Map updates to show transects from selected date
4. User clicks "Play" to animate through all dates
5. User pauses on interesting date, hovers transect for details

### Flow 2: Profile Analysis

1. User selects date of interest on timeline
2. User clicks specific transect on map
3. App transitions to Profile View
4. Profile shows elevation cross-section for clicked transect
5. User toggles on additional dates to compare profiles
6. User identifies erosion between winter 2023 and summer 2024
7. User clicks "Back to Map" to continue exploring

### Flow 3: Data Export

1. User filters to date range and quality level
2. User clicks "Export CSV"
3. Browser downloads filtered transect data

## Development Priorities

### Phase 1: Data Processing (MVP)
- [ ] Python script to parse all LLH files
- [ ] Group points into transects (by spatial clustering or time gaps)
- [ ] Generate GeoJSON for map display
- [ ] Create survey metadata index

### Phase 2: Map View
- [ ] Basic React app with Mapbox/Leaflet
- [ ] Load and display transects for single date
- [ ] Timeline component with date stepping
- [ ] Transect click handler

### Phase 3: Profile View
- [ ] Profile chart component
- [ ] Single-transect elevation display
- [ ] Multi-date overlay capability
- [ ] Smooth transitions between views

### Phase 4: Polish
- [ ] Animation playback
- [ ] Quality filtering
- [ ] Export functionality
- [ ] Mobile responsiveness

## Key Challenges

1. **Transect Identification**: Raw LLH files are continuous point streams. Need algorithm to segment into discrete transects (likely by time gaps or directional changes).

2. **Transect Matching**: To compare same location across dates, need spatial matching algorithm (e.g., find transects within X meters of each other).

3. **Performance**: 209 files with potentially millions of points. Need efficient data structures and lazy loading.

4. **Coordinate Systems**: LLH uses WGS84 ellipsoidal heights. May need to convert to orthometric heights (NAVD88) for meaningful beach elevation analysis.

## Environment Setup

```bash
# Install Python dependencies
pip install pandas numpy geopandas shapely

# Install Node dependencies
npm install

# Process raw data
python scripts/process_surveys.py

# Start development server
npm run dev
```

## API Keys Required

- **Mapbox**: For satellite imagery tiles (free tier available)
  - Get key at: https://www.mapbox.com/
  - Set as environment variable: `VITE_MAPBOX_TOKEN`

## References

- Emlid LLH format: https://docs.emlid.com/
- Beach survey methodology: RTK GPS walking surveys perpendicular to shoreline
- Location: Oceanside Municipal Pier vicinity, San Diego County, CA
