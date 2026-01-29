# Todo

> Source: [docs/prd.md](./prd.md)
> Last synced: 2026-01-29

## In Progress

<!-- Tasks currently being worked on -->

## Up Next

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

## Blocked

<!-- Tasks waiting on external factors -->

## Completed

### Phase 1: Data Processing — 2026-01-29

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

**Implementation notes:**
- MOP reference lines loaded from KML (`data/raw/MOPS/MOPs-SD.kml`) — 2,372 MOP lines for San Diego County
- MOP snapping uses orthogonal projection with 1m buffer, binning at 0.5m intervals
- Interactive MOP time series visualization at `figures/mop_interactive_map.html` (522 MOPs displayed, 46 with survey data)
- Additional scripts: `scripts/visualize_surveys.py`, `scripts/compute_timeseries.py`, `scripts/generate_dem.py`
- Unit test suite: 64 tests in `tests/` directory
- Current data: 24 survey dates, 1,122 transects, 873,561 points (Nov 2022 - Jan 2026)
