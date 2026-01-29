# PRD: Oceanside Beach Transect Visualizer

| Field        | Value                                      |
| ------------ | ------------------------------------------ |
| Status       | Draft                                      |
| Author       | —                                          |
| Last Updated | 2026-01-29                                 |
| Reviewers    | —                                          |

## Problem Statement

Citizen scientists conduct regular beach surveys along Oceanside, CA using RTK GPS equipment, collecting elevation data along established MOP (Monitoring and Prediction) cross-shore transect lines. Currently, there's no way for these volunteers to visualize their collective work, see survey coverage over time, or understand how the beach profile is changing. The raw LLH files sit unused, and the community lacks insight into the erosion/accretion patterns their data could reveal.

## Goals

1. **Visualize survey coverage**: Show which MOP lines were surveyed on any given date via an interactive map with satellite imagery
2. **Enable temporal exploration**: Allow stepping through 58+ survey dates to see how coverage evolved from Nov 2022 to present
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
- Render MOP reference lines as base layer (from shapefile)
- Overlay surveyed transects as colored polylines for selected date
- Color-code transects by: survey quality (fix type), elevation gradient, or uniform per date
- Show hover tooltips with transect metadata (date, point count, MOP line ID)
- Support click interaction to open Profile View for that MOP line

**Timeline**
- Display timeline showing all 58+ survey dates
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
│                    processed/ (static)                      │
│  surveys.json │ mop-lines.geojson │ transects/ │ profiles/ │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ (build-time processing)
┌─────────────────────────────────────────────────────────────┐
│                   Python Processing                         │
│  parse_llh.py → snap_to_mop.py → generate_outputs.py       │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│              data/LLH/*.LLH  +  data/mop_lines.shp         │
└─────────────────────────────────────────────────────────────┘
```

### Data Model

**MOP Lines** (from shapefile)
- Line ID (e.g., MOP-0001)
- Geometry (LineString in WGS84)
- Optional metadata (name, established date)

**Survey Session** (derived from LLH filename)
- Date (YYYY-MM-DD)
- Device name
- Source filename
- Point count
- Quality distribution (% fix/float/single)

**Transect** (LLH points snapped to MOP line)
- MOP line ID (foreign key)
- Survey date
- Points array: [{distance_along_line, elevation, quality, lat, lon}]

### Processing Pipeline

1. **Parse MOP shapefile** → `mop-lines.geojson`
2. **Parse each LLH file**:
   - Extract date from filename
   - Read all points with quality flags
   - Snap each point to nearest MOP line (within threshold, e.g., 50m)
   - Compute distance along MOP line for each point
3. **Aggregate by MOP line and date** → per-MOP profile JSON files
4. **Generate survey index** → `surveys.json` (dates, stats, available MOP lines)
5. **Generate transect geometries** → `transects/{date}.geojson` (for map rendering)

### File Outputs

```
processed/
├── surveys.json           # [{date, pointCount, mopLines: [...]}]
├── mop-lines.geojson      # Reference MOP line geometries
├── transects/
│   ├── 2022-11-03.geojson # Surveyed transects for this date
│   └── ...
└── profiles/
    ├── MOP-0001.json      # All dates' profiles for this MOP line
    └── ...
```

### API / Data Loading

No backend API—static file hosting:
- `surveys.json` loaded on app init
- `mop-lines.geojson` loaded on app init
- `transects/{date}.geojson` loaded when date selected
- `profiles/{mopId}.json` loaded when MOP line clicked

For privacy, data can be:
- Served from authenticated CDN/bucket
- Injected at build time via environment variable pointing to data URL
- Bundled into build (with consent) for fully static deployment

## Dependencies

**External**
- Mapbox GL JS + Mapbox account (satellite tiles)
- MOP lines shapefile (provided by user)

**Python**
- pandas, numpy (data manipulation)
- geopandas, shapely (spatial operations)
- pyproj (coordinate transforms if needed)

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
| Missing MOP shapefile | Show error on startup, link to setup instructions |
| Date range filter excludes all data | Show empty state message |

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MOP line snapping produces incorrect matches | Medium | High | Tune distance threshold, add visual validation step |
| Performance issues with large point clouds | Medium | Medium | Downsample for map, lazy load profiles, virtualize lists |
| Mapbox API costs exceed free tier | Low | Low | Monitor usage, cache tiles, consider switching to free tiles |
| Coordinate system issues (ellipsoidal vs orthometric heights) | Low | Medium | Document limitation, heights are relative comparisons |

## Testing Strategy

**Python Processing**
- Unit tests for LLH parser (valid files, malformed files, edge cases)
- Unit tests for MOP line snapping logic
- Integration test: process sample data, verify output structure

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

### Phase 1: Data Processing (MVP Foundation)
- Python scripts to parse LLH files
- MOP shapefile integration
- Point-to-MOP snapping
- Generate all output files

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

**Leaflet vs Mapbox GL JS**: Leaflet is simpler and fully open source, but Mapbox GL JS has better performance for large datasets and built-in satellite imagery. Chose Mapbox for performance.

**D3.js vs Plotly.js for charts**: D3 offers more control but requires more code. Plotly provides interactive charts out of the box with good multi-series support. Chose Plotly for faster development.

**Backend API vs static files**: A backend would enable dynamic queries but adds complexity and hosting cost. Static files work well for this read-only use case with moderate data size. Chose static for simplicity.

**Deck.gl for map rendering**: Better for massive point clouds but steeper learning curve. Standard Mapbox GL JS should handle this data volume. Can revisit if performance issues arise.

## Open Questions

1. **MOP shapefile format**: What's the schema? Which field contains the line ID?
2. **Snapping threshold**: What distance (in meters) should be the cutoff for associating a point with a MOP line?
3. **Authentication approach**: For private preview, use Vercel password protection, Netlify identity, or something else?
4. **Elevation units**: Are LLH heights in meters? Any local datum considerations?

## Task Breakdown

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

## Changelog

| Date       | Change        | Rationale                                              |
| ---------- | ------------- | ------------------------------------------------------ |
| 2026-01-29 | Initial draft | Created PRD based on README spec and user requirements |
