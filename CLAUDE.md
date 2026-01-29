# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive web application for visualizing GPS beach survey transects from Oceanside, CA. Processes LLH files from Emlid Reach GNSS receivers (58 survey sessions, Nov 2022 - Jan 2026).

## Commands

```bash
# Python data processing
pip install pandas numpy geopandas shapely
python scripts/process_surveys.py

# Frontend development
npm install
npm run dev
```

Requires `VITE_MAPBOX_TOKEN` environment variable for satellite imagery.

## Architecture

**Data Pipeline**: `data/LLH/*.LLH` → Python parser → `processed/` (surveys.json, transects.geojson, profiles/)

**Frontend Stack**: React + TypeScript, Mapbox GL JS or Leaflet, Plotly.js or D3.js, Tailwind CSS

**Two Main Views**:
- Map View: Timeline-controlled satellite map with transect overlays
- Profile View: Elevation cross-sections comparing transects across dates

## LLH File Format

Space-delimited: `YYYY/MM/DD HH:MM:SS.sss lat lon height Q ns sdn sde sdu sdne sdeu sdun age ratio`

- Quality flag (col 6): 1=RTK fix, 2=float, 5=single
- Height (col 5): Ellipsoidal (WGS84), may need conversion to NAVD88

Files named: `YYYY_MM_DD_[DeviceName]_solution_YYYYMMDDHHMMSS.LLH`

## Key Implementation Challenges

1. **Transect segmentation**: Raw LLH files are continuous point streams; segment by time gaps or directional changes
2. **Cross-date transect matching**: Spatial matching algorithm to find corresponding transects within X meters
3. **Performance**: 209 files with potentially millions of points; lazy loading required
