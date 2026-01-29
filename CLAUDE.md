# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive web application for visualizing GPS beach survey transects from Oceanside, CA. Processes LLH files from Emlid Reach GNSS receivers (58 survey sessions, Nov 2022 - Jan 2026).

## Project Structure

```
save-oceanside-sand/
├── data/
│   ├── raw/LLH/           # Raw GPS survey files (209 files)
│   ├── raw/MOPS/          # MOP line definitions
│   └── processed/         # Generated data (surveys.json, transects.geojson, surfaces/, profiles/)
├── docs/                  # Documentation (prd.md, todo.md)
├── figures/               # Generated visualizations
├── scripts/               # Python data processing scripts
├── tests/                 # pytest test suite
├── utilities/             # Shared Python modules (parse_llh.py)
└── web/                   # React frontend
    ├── src/               # React components, hooks, store, types, utils
    ├── public/processed   # Symlink to data/processed
    └── (config files)     # package.json, vite.config.ts, tsconfig.json, etc.
```

## Commands

```bash
# Activate Python environment
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Run data processing pipeline
python scripts/process_surveys.py

# Generate 3D surface DEMs
python scripts/generate_dem.py

# Run tests
pytest tests/

# Frontend development
cd web
npm install
npm run dev
```

## Architecture

**Data Pipeline**: `data/raw/LLH/*.LLH` → Python scripts → `data/processed/`

**Frontend Stack**: React + TypeScript + Vite, Three.js (3D surfaces), Zustand (state), Tailwind CSS

**Views**:
- Surface View: 3D interpolated beach surface with timeline navigation
- Map View: Satellite map with transect overlays
- Profile View: Elevation cross-sections across dates

## LLH File Format

Space-delimited: `YYYY/MM/DD HH:MM:SS.sss lat lon height Q ns sdn sde sdu sdne sdeu sdun age ratio`

- Quality flag (col 6): 1=RTK fix, 2=float, 5=single
- Height (col 5): Ellipsoidal (WGS84)
- Files named: `YYYY_MM_DD_[DeviceName]_solution_YYYYMMDDHHMMSS.LLH`

## Key Files

- `utilities/parse_llh.py` - Shared LLH parser (imported by all scripts)
- `scripts/process_surveys.py` - Main data pipeline
- `scripts/generate_dem.py` - 3D surface generation with scipy interpolation
- `web/src/components/views/SurfaceView/` - 3D visualization with Three.js
