"""
Create Interactive MOP Map with Time Series Profiles

Generates an HTML map where clicking any MOP line shows its
elevation profile time series from all survey dates.
"""

import re
import os
import sys
import json
import numpy as np
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utilities.parse_llh import parse_all_llh_files

# Constants
LAT_TO_M = 110574
LON_TO_M = 92890
BUFFER_M = 1.0


def parse_mop_lines(kml_path, lat_range=None, lon_range=None):
    """
    Parse MOP lines from KML file.

    If lat_range/lon_range provided, filter to that area.
    Otherwise return all MOPs.
    """
    with open(kml_path, 'r') as f:
        content = f.read()

    pattern = r'<Placemark>.*?<name>(.*?)</name>.*?<coordinates>\s*(.*?)\s*</coordinates>.*?</Placemark>'
    matches = re.findall(pattern, content, re.DOTALL)

    mop_lines = {}
    for name, coords_str in matches:
        parts = coords_str.strip().split()
        if len(parts) >= 2:
            coords = [[float(x) for x in p.split(',')[:2]] for p in parts]
            start = coords[0]

            # Filter by lat/lon if ranges provided
            if lat_range and not (lat_range[0] <= start[1] <= lat_range[1]):
                continue
            if lon_range and not (lon_range[0] <= start[0] <= lon_range[1]):
                continue

            mop_name = name.replace(' ', '_')
            if mop_name not in mop_lines:
                mop_lines[mop_name] = {
                    'name': mop_name,
                    'coords': coords,
                    'start': coords[0],
                    'end': coords[-1]
                }

    return mop_lines


def compute_mop_timeseries(mop, all_points_by_date):
    """Compute time series for a single MOP line"""
    start = np.array(mop['start'])
    end = np.array(mop['end'])

    # MOP line vector in meters
    mop_vec = np.array([
        (end[0] - start[0]) * LON_TO_M,
        (end[1] - start[1]) * LAT_TO_M
    ])
    mop_length = np.linalg.norm(mop_vec)
    if mop_length < 1:
        return None
    mop_unit = mop_vec / mop_length

    # Bounding box
    min_lon = min(start[0], end[0]) - 0.0005
    max_lon = max(start[0], end[0]) + 0.0005
    min_lat = min(start[1], end[1]) - 0.0005
    max_lat = max(start[1], end[1]) + 0.0005

    profiles = {}

    for date_str, points in all_points_by_date.items():
        date_points = []

        for lon, lat, height in points:
            # Bbox filter
            if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                continue

            # Project onto MOP line
            px = (lon - start[0]) * LON_TO_M
            py = (lat - start[1]) * LAT_TO_M
            point_vec = np.array([px, py])

            dist_along = np.dot(point_vec, mop_unit)

            if dist_along < 0 or dist_along > mop_length:
                continue

            # Orthogonal distance
            proj_point = dist_along * mop_unit
            ortho_dist = np.linalg.norm(point_vec - proj_point)

            if ortho_dist <= BUFFER_M:
                date_points.append((dist_along, height))

        if len(date_points) >= 5:
            # Bin by 0.5m
            date_points.sort(key=lambda x: x[0])
            dists = np.array([p[0] for p in date_points])
            elevs = np.array([p[1] for p in date_points])

            bins = np.arange(0, mop_length + 0.5, 0.5)
            bin_idx = np.digitize(dists, bins)

            bd, bh = [], []
            for b in range(1, len(bins)):
                mask = bin_idx == b
                if np.sum(mask) > 0:
                    bd.append(float(np.mean(dists[mask])))
                    bh.append(float(np.mean(elevs[mask])))

            if len(bd) >= 5:
                profiles[date_str] = {
                    'distances': [round(x, 2) for x in bd],
                    'elevations': [round(x, 3) for x in bh]
                }

    if len(profiles) < 1:
        return None

    return {
        'mop_name': mop['name'],
        'mop_length': round(mop_length, 1),
        'num_dates': len(profiles),
        'profiles': profiles
    }


def generate_html_map(mop_lines, mop_data, output_path):
    """Generate interactive HTML map with embedded time series charts"""

    # Calculate map center from MOPs with data
    mops_with_data = [mop for name, mop in mop_lines.items() if name in mop_data]
    if mops_with_data:
        all_lats = []
        all_lons = []
        for mop in mops_with_data:
            for coord in mop['coords']:
                all_lons.append(coord[0])
                all_lats.append(coord[1])
        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)
    else:
        center_lat, center_lon = 33.19, -117.38

    # Prepare MOP data for JavaScript
    mop_features = []
    for mop_name, mop in mop_lines.items():
        coords_js = [[c[1], c[0]] for c in mop['coords']]  # [lat, lon] for Leaflet
        has_data = mop_name in mop_data
        num_dates = mop_data[mop_name]['num_dates'] if has_data else 0

        mop_features.append({
            'name': mop_name,
            'coords': coords_js,
            'hasData': has_data,
            'numDates': num_dates
        })

    # Convert time series data to JSON
    mop_data_json = json.dumps(mop_data)
    mop_features_json = json.dumps(mop_features)

    html_template = '''<!DOCTYPE html>
<html>
<head>
    <title>Beach MOP Profiles - Time Series</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
        #container { display: flex; height: 100vh; }
        #map { flex: 1; }
        #sidebar {
            width: 550px;
            background: #f8f9fa;
            border-left: 2px solid #dee2e6;
            display: flex;
            flex-direction: column;
        }
        #sidebar-header {
            padding: 15px;
            background: #2c3e50;
            color: white;
        }
        #sidebar-header h2 { margin: 0 0 5px 0; font-size: 18px; }
        #sidebar-header p { margin: 0; font-size: 12px; opacity: 0.8; }
        #stats {
            padding: 10px 15px;
            background: #ecf0f1;
            border-bottom: 1px solid #bdc3c7;
            font-size: 13px;
        }
        #stats span { margin-right: 15px; }
        #chart-container {
            flex: 1;
            padding: 10px;
            min-height: 0;
        }
        #chart { width: 100%; height: 100%; cursor: crosshair; }
        #instructions {
            padding: 40px 20px;
            text-align: center;
            color: #6c757d;
        }
        #instructions h3 { color: #2c3e50; }
        .stat-label { color: #7f8c8d; }
        .stat-value { font-weight: bold; color: #2c3e50; }

        /* Modal styles */
        #modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        #modal {
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            width: 700px;
            max-width: 90%;
            max-height: 90%;
            display: flex;
            flex-direction: column;
        }
        #modal-header {
            padding: 15px 20px;
            background: #27ae60;
            color: white;
            border-radius: 8px 8px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        #modal-header h3 { margin: 0; font-size: 16px; }
        #modal-close {
            background: none;
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
            padding: 0;
            line-height: 1;
        }
        #modal-close:hover { opacity: 0.8; }
        #modal-body {
            padding: 15px;
            flex: 1;
        }
        #modal-chart { width: 100%; height: 350px; }
        #modal-info {
            padding: 10px 15px;
            background: #f8f9fa;
            border-top: 1px solid #ecf0f1;
            font-size: 12px;
            color: #7f8c8d;
            border-radius: 0 0 8px 8px;
        }
        .click-hint {
            padding: 8px 12px;
            background: #e8f6e9;
            border-left: 3px solid #27ae60;
            margin-bottom: 10px;
            font-size: 12px;
            color: #27ae60;
        }
    </style>
</head>
<body>
    <div id="container">
        <div id="map"></div>
        <div id="sidebar">
            <div id="sidebar-header">
                <h2 id="mop-title">MOP Profile Time Series</h2>
                <p id="mop-subtitle">Click a MOP line on the map to view elevation profiles</p>
            </div>
            <div id="stats" style="display: none;">
                <span><span class="stat-label">Length:</span> <span class="stat-value" id="stat-length">-</span></span>
                <span><span class="stat-label">Surveys:</span> <span class="stat-value" id="stat-dates">-</span></span>
                <span><span class="stat-label">Buffer:</span> <span class="stat-value">±1m</span></span>
            </div>
            <div id="chart-container">
                <div id="instructions">
                    <h3>📍 Select a MOP Line</h3>
                    <p>Click any <span style="color: #3498db; font-weight: bold;">blue line</span> on the map to view its beach profile time series.</p>
                    <p style="font-size: 12px; margin-top: 20px; color: #95a5a6;">
                        <strong style="color: #3498db;">Blue lines</strong> = MOP lines with survey data<br>
                        <strong style="color: #bdc3c7;">Gray lines</strong> = MOP lines without data<br><br>
                        Data shows all GPS points within 1m orthogonal distance of each MOP line.
                    </p>
                </div>
                <div id="click-hint" class="click-hint" style="display: none;">
                    💡 Click anywhere on the profile to see elevation changes over time at that location
                </div>
                <div id="chart"></div>
            </div>
        </div>
    </div>

    <!-- Modal for cross-shore time series -->
    <div id="modal-overlay">
        <div id="modal">
            <div id="modal-header">
                <h3 id="modal-title">Elevation Time Series</h3>
                <button id="modal-close">&times;</button>
            </div>
            <div id="modal-body">
                <div id="modal-chart"></div>
            </div>
            <div id="modal-info">
                Shows how beach elevation has changed over time at the selected cross-shore position.
            </div>
        </div>
    </div>

    <script>
        // MOP data
        const mopFeatures = ''' + mop_features_json + ''';
        const mopData = ''' + mop_data_json + ''';

        // Initialize map
        const map = L.map('map').setView([''' + str(center_lat) + ''', ''' + str(center_lon) + '''], 14);

        // Add tile layers
        const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Esri'
        });

        const streets = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap'
        });

        satellite.addTo(map);
        L.control.layers({'Satellite': satellite, 'Streets': streets}).addTo(map);

        // Add MOP lines
        let selectedLine = null;
        const mopLayers = {};

        mopFeatures.forEach(mop => {
            const color = mop.hasData ? '#3498db' : '#bdc3c7';
            const weight = mop.hasData ? 3 : 1;
            const opacity = mop.hasData ? 0.9 : 0.5;

            const line = L.polyline(mop.coords, {
                color: color,
                weight: weight,
                opacity: opacity
            }).addTo(map);

            line.mopName = mop.name;
            line.hasData = mop.hasData;
            line.originalColor = color;
            line.originalWeight = weight;
            mopLayers[mop.name] = line;

            const tooltipContent = mop.hasData
                ? `<strong>${mop.name}</strong><br>${mop.numDates} survey dates<br><em>Click to view profiles</em>`
                : `<strong>${mop.name}</strong><br>No survey data`;

            line.bindTooltip(tooltipContent, {
                permanent: false,
                direction: 'top',
                className: 'mop-tooltip'
            });

            if (mop.hasData) {
                line.on('click', function() {
                    // Reset previous selection
                    if (selectedLine) {
                        selectedLine.setStyle({
                            color: selectedLine.originalColor,
                            weight: selectedLine.originalWeight
                        });
                    }

                    // Highlight selected
                    this.setStyle({color: '#e74c3c', weight: 5});
                    selectedLine = this;

                    // Show chart
                    showTimeSeries(this.mopName);
                });

                line.on('mouseover', function() {
                    if (this !== selectedLine) {
                        this.setStyle({weight: 5, color: '#2980b9'});
                    }
                });

                line.on('mouseout', function() {
                    if (this !== selectedLine) {
                        this.setStyle({weight: this.originalWeight, color: this.originalColor});
                    }
                });
            }
        });

        // Fit map to MOPs with data
        const boundsGroup = L.featureGroup(
            Object.values(mopLayers).filter(l => l.hasData)
        );
        if (boundsGroup.getLayers().length > 0) {
            map.fitBounds(boundsGroup.getBounds().pad(0.1));
        }

        // Color scale for dates (viridis-like)
        function getDateColor(index, total) {
            const colors = [
                '#440154', '#482878', '#3e4989', '#31688e', '#26828e',
                '#1f9e89', '#35b779', '#6ece58', '#b5de2b', '#fde725'
            ];
            const idx = Math.floor((index / Math.max(1, total - 1)) * (colors.length - 1));
            return colors[Math.min(idx, colors.length - 1)];
        }

        function showTimeSeries(mopName) {
            document.getElementById('instructions').style.display = 'none';
            document.getElementById('chart').style.display = 'block';
            document.getElementById('stats').style.display = 'block';

            const data = mopData[mopName];
            if (!data) return;

            // Update header
            document.getElementById('mop-title').textContent = mopName;
            document.getElementById('mop-subtitle').textContent = 'Beach elevation profile over time';
            document.getElementById('stat-length').textContent = data.mop_length + 'm';
            document.getElementById('stat-dates').textContent = data.num_dates;

            const dates = Object.keys(data.profiles).sort();
            const traces = [];

            dates.forEach((date, i) => {
                const profile = data.profiles[date];
                traces.push({
                    x: profile.distances,
                    y: profile.elevations,
                    mode: 'lines',
                    name: date,
                    line: {
                        color: getDateColor(i, dates.length),
                        width: 2
                    },
                    hovertemplate: '<b>' + date + '</b><br>Distance: %{x:.1f}m<br>Elevation: %{y:.2f}m<extra></extra>'
                });
            });

            const layout = {
                xaxis: {
                    title: 'Distance along MOP (m)',
                    gridcolor: '#ecf0f1',
                    zerolinecolor: '#bdc3c7'
                },
                yaxis: {
                    title: 'Elevation (m, ellipsoidal)',
                    gridcolor: '#ecf0f1',
                    zerolinecolor: '#bdc3c7'
                },
                legend: {
                    orientation: 'v',
                    x: 1.02,
                    y: 1,
                    font: {size: 10},
                    title: {text: 'Survey Date', font: {size: 11}}
                },
                margin: {l: 60, r: 130, t: 20, b: 50},
                hovermode: 'closest',
                plot_bgcolor: 'white',
                paper_bgcolor: '#f8f9fa'
            };

            const config = {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d']
            };

            Plotly.newPlot('chart', traces, layout, config);

            // Add click handler for cross-shore time series
            document.getElementById('chart').on('plotly_click', function(eventData) {
                if (eventData.points && eventData.points.length > 0) {
                    const clickedX = eventData.points[0].x;
                    showCrossShoreTimeSeries(mopName, clickedX);
                }
            });

            // Show click hint
            document.getElementById('click-hint').style.display = 'block';
        }

        // Interpolate elevation at a specific distance
        function interpolateElevation(distances, elevations, targetDist) {
            if (targetDist <= distances[0]) return elevations[0];
            if (targetDist >= distances[distances.length - 1]) return elevations[elevations.length - 1];

            for (let i = 0; i < distances.length - 1; i++) {
                if (distances[i] <= targetDist && targetDist <= distances[i + 1]) {
                    const t = (targetDist - distances[i]) / (distances[i + 1] - distances[i]);
                    return elevations[i] + t * (elevations[i + 1] - elevations[i]);
                }
            }
            return null;
        }

        // Show time series at specific cross-shore location
        function showCrossShoreTimeSeries(mopName, distance) {
            const data = mopData[mopName];
            if (!data) return;

            const dates = Object.keys(data.profiles).sort();
            const elevations = [];
            const validDates = [];

            // Get elevation at this distance for each date
            dates.forEach(date => {
                const profile = data.profiles[date];
                const elev = interpolateElevation(profile.distances, profile.elevations, distance);
                if (elev !== null) {
                    validDates.push(date);
                    elevations.push(elev);
                }
            });

            if (validDates.length < 2) {
                alert('Not enough data at this location across survey dates.');
                return;
            }

            // Calculate change statistics
            const minElev = Math.min(...elevations);
            const maxElev = Math.max(...elevations);
            const range = maxElev - minElev;
            const firstElev = elevations[0];
            const lastElev = elevations[elevations.length - 1];
            const netChange = lastElev - firstElev;

            // Update modal title
            document.getElementById('modal-title').textContent =
                `${mopName} @ ${distance.toFixed(1)}m cross-shore`;

            // Create the time series trace
            const trace = {
                x: validDates,
                y: elevations,
                mode: 'lines+markers',
                type: 'scatter',
                line: {
                    color: '#27ae60',
                    width: 3
                },
                marker: {
                    size: 10,
                    color: elevations.map((e, i) => getDateColor(i, elevations.length))
                },
                hovertemplate: '<b>%{x}</b><br>Elevation: %{y:.3f}m<extra></extra>'
            };

            // Add trend line
            const n = validDates.length;
            const xIndices = validDates.map((_, i) => i);
            const sumX = xIndices.reduce((a, b) => a + b, 0);
            const sumY = elevations.reduce((a, b) => a + b, 0);
            const sumXY = xIndices.reduce((acc, x, i) => acc + x * elevations[i], 0);
            const sumX2 = xIndices.reduce((acc, x) => acc + x * x, 0);
            const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
            const intercept = (sumY - slope * sumX) / n;

            const trendTrace = {
                x: [validDates[0], validDates[validDates.length - 1]],
                y: [intercept, intercept + slope * (n - 1)],
                mode: 'lines',
                line: {
                    color: '#e74c3c',
                    width: 2,
                    dash: 'dash'
                },
                name: 'Trend',
                hoverinfo: 'skip'
            };

            const modalLayout = {
                xaxis: {
                    title: 'Survey Date',
                    tickangle: -45,
                    gridcolor: '#ecf0f1'
                },
                yaxis: {
                    title: 'Elevation (m)',
                    gridcolor: '#ecf0f1'
                },
                margin: {l: 60, r: 20, t: 30, b: 80},
                showlegend: false,
                annotations: [{
                    x: 0.02,
                    y: 0.98,
                    xref: 'paper',
                    yref: 'paper',
                    text: `Range: ${range.toFixed(3)}m<br>Net change: ${netChange >= 0 ? '+' : ''}${netChange.toFixed(3)}m`,
                    showarrow: false,
                    font: {size: 11},
                    bgcolor: 'rgba(255,255,255,0.8)',
                    bordercolor: '#bdc3c7',
                    borderwidth: 1,
                    borderpad: 4,
                    align: 'left'
                }],
                plot_bgcolor: 'white',
                paper_bgcolor: 'white'
            };

            Plotly.newPlot('modal-chart', [trace, trendTrace], modalLayout, {responsive: true});

            // Show modal
            document.getElementById('modal-overlay').style.display = 'flex';
        }

        // Modal close handlers
        document.getElementById('modal-close').onclick = function() {
            document.getElementById('modal-overlay').style.display = 'none';
        };

        document.getElementById('modal-overlay').onclick = function(e) {
            if (e.target === this) {
                this.style.display = 'none';
            }
        };

        // Close modal on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                document.getElementById('modal-overlay').style.display = 'none';
            }
        });
    </script>
</body>
</html>'''

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html_template)

    print(f"Saved interactive map: {output_path}")


def main():
    print("=" * 60)
    print("CREATING INTERACTIVE MOP MAP (ALL MOPS)")
    print("=" * 60)

    # Get survey data extent
    with open('data/processed/surveys.json', 'r') as f:
        surveys = json.load(f)

    all_bounds = []
    for s in surveys['surveys']:
        b = s['bounds']
        all_bounds.append((b['min_lat'], b['max_lat'], b['min_lon'], b['max_lon']))

    # Survey extent with small buffer
    survey_lat_range = (min(b[0] for b in all_bounds) - 0.01,
                        max(b[1] for b in all_bounds) + 0.01)
    survey_lon_range = (min(b[2] for b in all_bounds) - 0.01,
                        max(b[3] for b in all_bounds) + 0.01)

    print(f"\nSurvey data extent:")
    print(f"  Lat: {survey_lat_range[0]:.4f} to {survey_lat_range[1]:.4f}")
    print(f"  Lon: {survey_lon_range[0]:.4f} to {survey_lon_range[1]:.4f}")

    # 1. Parse MOP lines within survey extent
    print("\n[1/4] Parsing MOP lines from KML...")
    mop_lines = parse_mop_lines(
        'data/raw/MOPS/MOPs-SD.kml',
        lat_range=survey_lat_range,
        lon_range=survey_lon_range
    )
    print(f"  Found {len(mop_lines)} MOP lines in survey area")

    # 2. Load all LLH data
    print("\n[2/4] Loading LLH files...")
    llh_files = parse_all_llh_files('data/raw/LLH')
    print(f"  Loaded {len(llh_files)} files")

    # Organize points by date
    all_points_by_date = defaultdict(list)
    total_points = 0
    for llh_file in llh_files:
        date_str = llh_file.survey_date.strftime('%Y-%m-%d')
        for p in llh_file.points:
            all_points_by_date[date_str].append((p.lon, p.lat, p.height))
            total_points += 1

    print(f"  {total_points:,} points organized into {len(all_points_by_date)} survey dates")

    # 3. Compute time series for each MOP
    print("\n[3/4] Computing time series for each MOP line...")
    mop_data = {}

    for i, (mop_name, mop) in enumerate(mop_lines.items()):
        if (i + 1) % 25 == 0 or (i + 1) == len(mop_lines):
            print(f"  Processing {i + 1}/{len(mop_lines)}...")

        ts = compute_mop_timeseries(mop, all_points_by_date)
        if ts:
            mop_data[mop_name] = ts

    print(f"\n  {len(mop_data)} MOP lines have survey data")

    # Summary of data coverage
    if mop_data:
        avg_dates = np.mean([d['num_dates'] for d in mop_data.values()])
        max_dates = max(d['num_dates'] for d in mop_data.values())
        print(f"  Average surveys per MOP: {avg_dates:.1f}")
        print(f"  Max surveys for a MOP: {max_dates}")

    # 4. Generate HTML map
    print("\n[4/4] Generating interactive HTML map...")
    generate_html_map(mop_lines, mop_data, 'figures/mop_interactive_map.html')

    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print(f"\nMOP lines in area: {len(mop_lines)}")
    print(f"MOPs with data: {len(mop_data)}")
    print("\nOpen figures/mop_interactive_map.html in your browser")
    print("Click any blue MOP line to see its time series profile")


if __name__ == '__main__':
    main()
