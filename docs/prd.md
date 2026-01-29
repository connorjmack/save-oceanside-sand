# PRD: Oceanside Beach Transect Visualizer

| Field        | Value                                      |
| ------------ | ------------------------------------------ |
| Status       | In Progress (Phase 1 Complete)             |
| Author       | —                                          |
| Last Updated | 2026-01-29                                 |
| Reviewers    | —                                          |

## Problem Statement

Citizen scientists conduct regular beach surveys along Oceanside, CA using RTK GPS equipment, collecting elevation data along established MOP (Monitoring and Prediction) cross-shore transect lines. Currently, there's no way for these volunteers to visualize their collective work, see survey coverage over time, or understand how the beach profile is changing. The raw LLH files sit unused, and the community lacks insight into the erosion/accretion patterns their data could reveal.

## Goals

1. **Visualize survey coverage**: Show which MOP lines were surveyed on any given date via an interactive map with satellite imagery
2. **Enable temporal exploration**: Allow stepping through survey dates to see how coverage evolved from Nov 2022 to present
3. **Support profile analysis**: Display elevation cross-sections along MOP lines and compare the same location across multiple survey dates
4. **Detect beach changes**: Help users identify erosion and accretion patterns by overlaying profiles from different dates

## Success Metrics

- App loads initial view in <3 seconds on typical connection
- Timeline navigation between dates feels instant (<200ms)
- Profile view renders multi-date comparison (10+ dates) without lag
- Users can identify which MOP lines have the most historical data
- Users can visually compare elevation changes across seasons/years

## Non-Goals

- Real-time data ingestion (batch processing is fine)
- Native mobile app (responsive web is sufficient)
- Data editing or annotation features
- Public data access without explicit consent from survey participants
- Vertical datum conversion (ellipsoidal heights are acceptable for relative comparison)
- Statistical analysis or automated change detection algorithms

## Users & Use Cases

### Primary Users

**Citizen Scientists**: Volunteers who conduct the beach surveys. Want to see their work visualized and understand the bigger picture of beach change.

**Researchers**: May use the tool to identify interesting patterns worth deeper analysis. Need to export data for external tools.

### Use Cases

1. **Temporal Exploration**: User opens app → sees most recent survey on map → drags timeline to explore historical coverage → plays animation to watch survey history unfold

2. **Profile Analysis**: User selects date on timeline → clicks a MOP line on map → sees elevation profile → toggles on additional dates → identifies erosion between winter storms

3. **Data Export**: User filters to date range and quality level → exports visible transect data as CSV for external analysis

## Requirements

### Functional Requirements

**Map View**
- Display satellite basemap centered on Oceanside beach/pier area (~33.19°N to 33.15°N)
- Render MOP reference lines as base layer (from KML file)
- Overlay surveyed transects as colored polylines for selected date
- Color-code transects by: survey quality (fix type), elevation gradient, or uniform per date
- Show hover tooltips with transect metadata (date, point count, MOP line ID)
- Support click interaction to open Profile View for that MOP line

**Timeline**
- Display timeline showing all survey dates (24 dates as of Jan 2026)
- Support discrete stepping (prev/next date buttons)
- Support slider-based navigation
- Show current date prominently
- Support animation mode (auto-advance through dates)

**Profile View**
- Display elevation (y-axis) vs distance along transect (x-axis) chart
- Show selected date's profile as primary line
- Support overlaying the same MOP line from all other survey dates
- Each date as distinct colored line with legend
- Toggle individual dates on/off in legend
- Hover interaction showing exact coordinates and elevation
- Zoom/pan support on chart
- Back button to return to Map View

**Data Controls**
- Date range filter to limit visible surveys
- Quality filter (RTK fixed only, or include float/single)
- Export currently visible data as CSV

### Non-Functional Requirements

**Performance**
- Initial load <3s on broadband
- Date switching <200ms
- Handle 200+ LLH files smoothly
- Lazy load profile data (don't fetch all profiles upfront)

**Privacy**
- Survey data not publicly accessible without consent
- Support authenticated access or private data injection
- No PII in exported data

**Accessibility**
- Keyboard navigation for timeline
- Color schemes distinguishable for colorblind users
- Chart data accessible via tooltips

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React SPA (Vite)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  MapView    │  │ ProfileView │  │  Timeline + Controls│  │
│  │ (Mapbox GL) │  │ (Plotly.js) │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 data/processed/ (static)                    │
│   surveys.json │ transects.geojson │ profiles/{id}.json    │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ (build-time processing)
┌─────────────────────────────────────────────────────────────┐
│                   Python Processing                         │
│  utilities/parse_llh.py → scripts/generate_transects.py    │
│            → scripts/process_surveys.py                     │
│            → scripts/create_interactive_mop_map.py          │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│       data/raw/LLH/*.LLH  +  data/raw/MOPS/MOPs-SD.kml     │
└─────────────────────────────────────────────────────────────┘
```

### Data Model

**MOP Lines** (from KML file: `data/raw/MOPS/MOPs-SD.kml`)
- Line name (e.g., "SD-0001" through "SD-2372")
- Geometry (LineString in WGS84)
- 2,372 MOP lines covering San Diego County coast

**Survey Session** (derived from LLH filename)
- Date (YYYY-MM-DD)
- Device name (e.g., "CPG_Reach_1", "SOS_Emlid_R")
- Source filename
- Point count
- Quality distribution (% fix/float/single)

**Transect** (segmented from LLH points by time gaps and direction changes)
- Transect ID (format: `YYYYMMDD_DeviceName_TXXX`)
- Survey date
- Device name
- Points array: [{lat, lon, height, quality, timestamp}]
- Computed properties: length_meters, rtk_fix_percentage, bounds

**LLH Point** (parsed from LLH file)
- timestamp, lat, lon, height
- quality (1=RTK fix, 2=float, 5=single)
- num_satellites, sdn, sde, sdu, sdne, sdeu, sdun, age, ratio

### Processing Pipeline

1. **Parse LLH files** (`utilities/parse_llh.py`):
   - Extract date and device name from filename
   - Read all points with quality flags and metadata
   - Return LLHFile objects with LLHPoint arrays

2. **Segment into transects** (`scripts/generate_transects.py`):
   - Split continuous point streams by time gaps (>30s threshold)
   - Split by direction changes (>90° threshold)
   - Filter segments below minimum point count (default 50)
   - Generate unique transect IDs

3. **Aggregate surveys** (`scripts/process_surveys.py`):
   - Group LLH files by survey date
   - Calculate per-date statistics (point counts, quality distribution, bounds)
   - Generate survey metadata index

4. **Generate outputs**:
   - `surveys.json` - survey metadata with statistics
   - `transects.geojson` - all transect geometries for map rendering
   - `profiles/{transect_id}.json` - per-transect elevation profile data

5. **MOP-based analysis** (`scripts/create_interactive_mop_map.py`):
   - Parse MOP lines from KML file
   - Project GPS points onto MOP lines using orthogonal projection (1m buffer)
   - Bin points by 0.5m intervals along MOP line
   - Generate interactive HTML visualization with time series

### File Outputs

```
data/processed/
├── surveys.json              # Survey metadata index
│                             # [{date, files, devices, total_points,
│                             #   total_transects, rtk_fix_percentage,
│                             #   quality_counts, bounds, transect_stats}]
├── transects.geojson         # All transect geometries (FeatureCollection)
│                             # Features: LineString with properties
└── profiles/
    ├── 20221103_CPGReach1_T001.json    # Per-transect profile data
    ├── 20221103_CPGReach1_T002.json    # {transect_id, survey_date,
    └── ...                              #  distances[], elevations[],
                                         #  qualities[], coordinates[]}

figures/
└── mop_interactive_map.html  # Interactive MOP time series visualization
```

### Current Data Statistics (as of 2026-01-29)

- **Survey dates**: 24 (Nov 2022 - Jan 2026)
- **Total transects**: 1,122
- **Total points**: 873,561
- **MOP lines with data**: 46 (of 522 in survey area)
- **Devices**: CPG_Reach_1, SOS_Emlid_R, CPGReach1

### API / Data Loading

No backend API—static file hosting:
- `surveys.json` loaded on app init
- `transects.geojson` loaded on app init (or lazy load by date)
- `profiles/{transectId}.json` loaded when transect clicked

For privacy, data can be:
- Served from authenticated CDN/bucket
- Injected at build time via environment variable pointing to data URL
- Bundled into build (with consent) for fully static deployment

## Dependencies

**External**
- Mapbox GL JS + Mapbox account (satellite tiles)
- MOP lines KML file (`data/raw/MOPS/MOPs-SD.kml`) - 2,372 lines for San Diego County

**Python** (see `requirements.txt`)
- pandas==2.2.0, numpy==1.26.3 (data manipulation)
- geopandas==0.14.2, shapely==2.0.2 (spatial operations)
- pyproj==3.6.1 (coordinate transforms)
- scipy==1.12.0 (interpolation)
- pytest==8.0.0 (testing)

**Node/Frontend**
- React 18+
- TypeScript
- Vite
- mapbox-gl
- plotly.js (react-plotly.js wrapper)
- tailwindcss

## Edge Cases & Error Handling

| Scenario | Handling |
|----------|----------|
| LLH file with no points within MOP line threshold | Log warning, exclude from that MOP line's data |
| MOP line with only 1-2 survey dates | Display normally, note sparse data in UI |
| Survey with all float/single (no RTK fix) | Include but flag as lower quality, respect quality filter |
| Extremely long transect (>5000 points) | Downsample for map display, full resolution for profile |
| Missing MOP KML file | Show error on startup, link to setup instructions |
| Date range filter excludes all data | Show empty state message |
| LLH filename doesn't match expected pattern | Log warning, attempt fallback parsing |

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MOP line snapping produces incorrect matches | Medium | High | Use 1m orthogonal buffer, visual validation in interactive map |
| Performance issues with large point clouds | Medium | Medium | Downsample for map, lazy load profiles, virtualize lists |
| Mapbox API costs exceed free tier | Low | Low | Monitor usage, cache tiles, consider switching to free tiles |
| Coordinate system issues (ellipsoidal vs orthometric heights) | Low | Medium | Document limitation, heights are relative comparisons |

## Testing Strategy

**Python Processing** (64 tests implemented)
- Unit tests for LLH parser (`tests/test_parse_llh.py`): valid files, malformed files, edge cases
- Unit tests for transect generation (`tests/test_generate_transects.py`): distance, bearing, segmentation
- Unit tests for survey processing (`tests/test_process_surveys.py`): aggregation, metadata generation
- Shared fixtures in `tests/conftest.py`

**Frontend**
- Unit tests for data transformation utilities
- Component tests for Timeline, transect rendering logic
- Visual regression tests for map and chart components (optional)
- E2E test: load app, navigate timeline, click transect, view profile

**Manual Testing**
- Verify satellite imagery loads correctly
- Test timeline animation smoothness
- Validate profile overlays are visually correct
- Test on mobile viewport

## Rollout Plan

1. **Local Development**: Run locally with data in gitignored `processed/` folder
2. **Private Preview**: Deploy to Vercel/Netlify with data in private bucket, share link with survey team
3. **Authenticated Access**: Add basic auth or invite-only access if needed
4. **Public Release** (optional, with consent): Bake data into build, deploy as fully static site

## Timeline & Milestones

### Phase 1: Data Processing (MVP Foundation) ✅ COMPLETE

- ✅ Python modules to parse LLH files (`utilities/parse_llh.py`)
- ✅ Transect segmentation by time gaps and direction changes (`scripts/generate_transects.py`)
- ✅ Survey aggregation and metadata generation (`scripts/process_surveys.py`)
- ✅ MOP KML integration with orthogonal projection (`scripts/create_interactive_mop_map.py`)
- ✅ Generate all output files (surveys.json, transects.geojson, profiles/)
- ✅ Unit test suite (64 tests)

### Phase 2: Map View

- React + Vite project setup
- Mapbox integration with satellite tiles
- Load and display MOP reference lines
- Load and display transects for selected date
- Timeline component with date navigation

### Phase 3: Profile View

- Profile chart component with Plotly
- Single-date elevation display
- Multi-date overlay capability
- Smooth view transitions (map ↔ profile)

### Phase 4: Polish

- Animation playback for timeline
- Quality filtering
- CSV export
- Mobile responsive layout
- Performance optimization

## Alternatives Considered

**Leaflet vs Mapbox GL JS**: Leaflet is simpler and fully open source, but Mapbox GL JS has better performance for large datasets and built-in satellite imagery. Chose Mapbox for performance. *Note: Phase 1 interactive map uses Leaflet for simplicity.*

**D3.js vs Plotly.js for charts**: D3 offers more control but requires more code. Plotly provides interactive charts out of the box with good multi-series support. Chose Plotly for faster development.

**Backend API vs static files**: A backend would enable dynamic queries but adds complexity and hosting cost. Static files work well for this read-only use case with moderate data size. Chose static for simplicity.

**Deck.gl for map rendering**: Better for massive point clouds but steeper learning curve. Standard Mapbox GL JS should handle this data volume. Can revisit if performance issues arise.

**Shapefile vs KML for MOP lines**: Originally planned shapefile, but KML file (`MOPs-SD.kml`) was available with 2,372 MOP lines. KML parsing implemented directly.

## Open Questions

1. ~~**MOP shapefile format**: What's the schema? Which field contains the line ID?~~ **Resolved**: Using KML file with line names like "SD-0001"
2. ~~**Snapping threshold**: What distance (in meters) should be the cutoff for associating a point with a MOP line?~~ **Resolved**: 1 meter orthogonal buffer
3. **Authentication approach**: For private preview, use Vercel password protection, Netlify identity, or something else?
4. ~~**Elevation units**: Are LLH heights in meters? Any local datum considerations?~~ **Resolved**: Heights are ellipsoidal (WGS84) in meters, acceptable for relative comparison

## Task Breakdown

### Phase 1: Data Processing ✅ COMPLETE

- [x] Create `scripts/` and `utilities/` directory structure
- [x] Write `utilities/parse_llh.py` - LLHPoint, LLHFile classes, parse single/multiple LLH files
- [x] Write unit tests for LLH parser - `tests/test_parse_llh.py`
- [x] Write `scripts/generate_transects.py` - Transect class, segmentation by time/direction
- [x] Write unit tests for transect generation - `tests/test_generate_transects.py`
- [x] Write `scripts/process_surveys.py` - aggregate_surveys_by_date, generate_survey_metadata
- [x] Write unit tests for process_surveys - `tests/test_process_surveys.py`
- [x] Write `scripts/create_interactive_mop_map.py` - MOP KML parsing, orthogonal projection
- [x] Generate `data/processed/surveys.json` - survey metadata index
- [x] Generate `data/processed/transects.geojson` - transect geometries
- [x] Generate `data/processed/profiles/*.json` - per-transect profile data
- [x] Run full pipeline on all LLH files - verified outputs
- [x] Add `requirements.txt` with Python dependencies

### Phase 2: Map View

- [ ] Initialize Vite + React + TypeScript project
- [ ] Add Tailwind CSS configuration
- [ ] Add Mapbox GL JS dependency
- [ ] Create `.env.example` with `VITE_MAPBOX_TOKEN` placeholder
- [ ] Create `src/components/MapView.tsx` - basic Mapbox map with satellite tiles
- [ ] Load and render MOP lines as base layer
- [ ] Create `src/hooks/useTransectData.ts` - fetch and cache transect GeoJSON
- [ ] Render transects for current date as colored polylines
- [ ] Add transect hover tooltips (date, point count, MOP line ID)
- [ ] Create `src/components/Timeline.tsx` - date navigation UI
- [ ] Create `src/hooks/useTimeline.ts` - timeline state management
- [ ] Connect timeline to map - date changes update transects
- [ ] Add click handler on transects - capture transect ID for profile view

### Phase 3: Profile View

- [ ] Add react-plotly.js dependency
- [ ] Create `src/components/ProfileView.tsx` - elevation chart scaffold
- [ ] Create `src/hooks/useProfileData.ts` - fetch profile JSON for transect
- [ ] Render single-date profile (distance vs elevation)
- [ ] Add multi-date overlay - show profiles from same MOP line across dates
- [ ] Add legend with date labels and toggle visibility
- [ ] Add hover tooltip showing coordinates and elevation
- [ ] Add zoom/pan support to chart
- [ ] Create view router - switch between MapView and ProfileView
- [ ] Add back button in ProfileView to return to map
- [ ] Animate transition between views

### Phase 4: Polish

- [ ] Add animation mode to timeline - auto-advance through dates
- [ ] Add play/pause button for animation
- [ ] Add date range filter component
- [ ] Add quality filter toggle (RTK fixed only)
- [ ] Wire filters to data loading
- [ ] Add CSV export button
- [ ] Implement CSV export for current view's data
- [ ] Test and fix mobile responsive layout
- [ ] Optimize transect rendering for large datasets (simplification/clustering)
- [ ] Add loading states and error boundaries
- [ ] Write README with setup and deployment instructions
- [ ] Configure deployment (Vercel/Netlify)

## Changelog

| Date       | Change                    | Rationale                                              |
| ---------- | ------------------------- | ------------------------------------------------------ |
| 2026-01-29 | Initial draft             | Created PRD based on README spec and user requirements |
| 2026-01-29 | Updated for Phase 1 complete | Documented actual implementation: KML instead of shapefile, actual file paths, current data statistics, resolved open questions |
