# Todo

> Source: [docs/prd.md](./prd.md)
> Last synced: 2026-01-29

## In Progress

<!-- Tasks currently being worked on -->

## Up Next

### Phase 1: Data Processing

- [ ] Create `scripts/` directory structure
- [ ] Write `scripts/parse_llh.py` - parse single LLH file into DataFrame
- [ ] Write unit tests for LLH parser - valid file, empty file, malformed lines
- [ ] Write `scripts/load_mop.py` - load MOP shapefile into GeoDataFrame
- [ ] Write `scripts/snap_points.py` - snap LLH points to nearest MOP line
- [ ] Write unit tests for snapping logic - within threshold, outside threshold, equidistant
- [ ] Write `scripts/generate_outputs.py` - orchestrate full pipeline
- [ ] Generate `processed/surveys.json` - survey metadata index
- [ ] Generate `processed/mop-lines.geojson` - reference line geometries
- [ ] Generate `processed/transects/{date}.geojson` - per-date map geometries
- [ ] Generate `processed/profiles/{mopId}.json` - per-MOP-line profile data
- [ ] Run full pipeline on all LLH files - verify outputs
- [ ] Add `requirements.txt` with Python dependencies

### Phase 2: Map View

- [ ] Initialize Vite + React + TypeScript project
- [ ] Add Tailwind CSS configuration
- [ ] Add Mapbox GL JS dependency
- [ ] Create `.env.example` with `VITE_MAPBOX_TOKEN` placeholder
- [ ] Create `src/components/MapView.tsx` - basic Mapbox map with satellite tiles
- [ ] Load and render `mop-lines.geojson` as base layer
- [ ] Create `src/hooks/useTransectData.ts` - fetch and cache transect GeoJSON
- [ ] Render transects for current date as colored polylines
- [ ] Add transect hover tooltips (date, point count, MOP line ID)
- [ ] Create `src/components/Timeline.tsx` - date navigation UI
- [ ] Create `src/hooks/useTimeline.ts` - timeline state management
- [ ] Connect timeline to map - date changes update transects
- [ ] Add click handler on transects - capture MOP line ID for profile view

### Phase 3: Profile View

- [ ] Add react-plotly.js dependency
- [ ] Create `src/components/ProfileView.tsx` - elevation chart scaffold
- [ ] Create `src/hooks/useProfileData.ts` - fetch profile JSON for MOP line
- [ ] Render single-date profile (distance vs elevation)
- [ ] Add multi-date overlay - show all dates for selected MOP line
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

- [ ] Write `scripts/load_mop.py` - **blocked on**: MOP shapefile upload from user

## Completed

<!-- Move completed tasks here to keep the active list clean -->
