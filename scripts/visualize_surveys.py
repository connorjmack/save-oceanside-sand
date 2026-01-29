"""
Phase 1 Visualizations for Oceanside Beach Survey Data

Generates:
1. Interactive map with all transects (HTML)
2. Sample elevation profiles (PNG)
3. Survey statistics dashboard (PNG)
"""

import os
import json
from datetime import datetime
from collections import defaultdict

import folium
from folium import plugins
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


def load_survey_data():
    """Load processed survey data"""
    with open('processed/surveys.json', 'r') as f:
        surveys = json.load(f)

    with open('processed/transects.geojson', 'r') as f:
        transects = json.load(f)

    return surveys, transects


def create_interactive_map(transects, output_path='visualizations/transects_map.html'):
    """
    Create an interactive Folium map with all transects.

    Color-codes transects by survey date for temporal comparison.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Calculate center point from all transects
    all_lats = []
    all_lons = []
    for feature in transects['features']:
        coords = feature['geometry']['coordinates']
        for lon, lat, *_ in coords:
            all_lats.append(lat)
            all_lons.append(lon)

    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles=None
    )

    # Add tile layers
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False
    ).add_to(m)

    folium.TileLayer(
        tiles='OpenStreetMap',
        name='Street Map',
        overlay=False
    ).add_to(m)

    # Get unique dates and create color map
    dates = sorted(set(f['properties']['survey_date'] for f in transects['features']))
    colors = plt.cm.viridis(np.linspace(0, 1, len(dates)))
    color_map = {date: f'#{int(c[0]*255):02x}{int(c[1]*255):02x}{int(c[2]*255):02x}'
                 for date, c in zip(dates, colors)}

    # Create feature groups by date
    date_groups = defaultdict(list)
    for feature in transects['features']:
        date = feature['properties']['survey_date']
        date_groups[date].append(feature)

    # Add transects grouped by date
    for date in sorted(date_groups.keys()):
        fg = folium.FeatureGroup(name=f'{date} ({len(date_groups[date])} transects)')

        for feature in date_groups[date]:
            coords = feature['geometry']['coordinates']
            # Convert to lat/lon format for folium
            latlngs = [[lat, lon] for lon, lat, *_ in coords]

            props = feature['properties']
            popup_html = f"""
            <b>Transect:</b> {props['transect_id']}<br>
            <b>Date:</b> {props['survey_date']}<br>
            <b>Points:</b> {props['point_count']}<br>
            <b>Length:</b> {props['length_meters']:.1f} m<br>
            <b>RTK Fix:</b> {props['rtk_fix_percentage']:.1f}%<br>
            <b>Elevation:</b> {props['min_elevation']:.2f} to {props['max_elevation']:.2f} m
            """

            folium.PolyLine(
                latlngs,
                color=color_map[date],
                weight=3,
                opacity=0.8,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(fg)

        fg.add_to(m)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Add fullscreen button
    plugins.Fullscreen().add_to(m)

    # Add minimap
    plugins.MiniMap(toggle_display=True).add_to(m)

    m.save(output_path)
    print(f"Interactive map saved to: {output_path}")
    return output_path


def create_elevation_profiles(output_path='visualizations/elevation_profiles.png'):
    """
    Create sample elevation profiles from different survey dates.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Get list of profile files
    profile_dir = 'processed/profiles'
    profile_files = os.listdir(profile_dir)

    # Group by date
    profiles_by_date = defaultdict(list)
    for f in profile_files:
        if f.endswith('.json'):
            # Extract date from filename (YYYYMMDD_...)
            date_str = f[:8]
            profiles_by_date[date_str].append(f)

    # Select 6 representative dates (spread across time range)
    sorted_dates = sorted(profiles_by_date.keys())
    if len(sorted_dates) >= 6:
        indices = np.linspace(0, len(sorted_dates) - 1, 6, dtype=int)
        selected_dates = [sorted_dates[i] for i in indices]
    else:
        selected_dates = sorted_dates

    # Create figure
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    colors = plt.cm.tab10(np.linspace(0, 1, 10))

    for idx, date_str in enumerate(selected_dates):
        ax = axes[idx]

        # Load first few profiles for this date
        date_profiles = profiles_by_date[date_str][:5]

        for i, profile_file in enumerate(date_profiles):
            filepath = os.path.join(profile_dir, profile_file)
            with open(filepath, 'r') as f:
                profile = json.load(f)

            distances = profile['distances']
            elevations = profile['elevations']

            ax.plot(distances, elevations,
                   color=colors[i % 10],
                   alpha=0.7,
                   linewidth=1.5,
                   label=profile['transect_id'].split('_')[-1])

        # Format date for title
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        ax.set_title(f'Survey: {formatted_date}', fontsize=12, fontweight='bold')
        ax.set_xlabel('Distance (m)')
        ax.set_ylabel('Elevation (m)')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc='upper right')

        # Set reasonable y-axis limits
        ax.set_ylim(-40, 10)

    plt.suptitle('Beach Elevation Profiles - Oceanside, CA',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"Elevation profiles saved to: {output_path}")
    return output_path


def create_statistics_dashboard(surveys, output_path='visualizations/survey_statistics.png'):
    """
    Create a dashboard showing survey statistics over time.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    survey_list = surveys['surveys']

    # Extract data
    dates = [datetime.strptime(s['date'], '%Y-%m-%d') for s in survey_list]
    transect_counts = [s['total_transects'] for s in survey_list]
    point_counts = [s['total_points'] for s in survey_list]
    rtk_percentages = [s['rtk_fix_percentage'] for s in survey_list]
    total_lengths = [s['transect_stats']['total_length_meters'] / 1000 for s in survey_list]  # Convert to km

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Transects per survey
    ax1 = axes[0, 0]
    bars1 = ax1.bar(dates, transect_counts, color='steelblue', alpha=0.8, width=15)
    ax1.set_ylabel('Number of Transects', fontsize=11)
    ax1.set_title('Transects per Survey Date', fontsize=12, fontweight='bold')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar, val in zip(bars1, transect_counts):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                str(val), ha='center', va='bottom', fontsize=8)

    # 2. Points per survey
    ax2 = axes[0, 1]
    bars2 = ax2.bar(dates, [p/1000 for p in point_counts], color='coral', alpha=0.8, width=15)
    ax2.set_ylabel('Points (thousands)', fontsize=11)
    ax2.set_title('GPS Points per Survey Date', fontsize=12, fontweight='bold')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    ax2.grid(axis='y', alpha=0.3)

    # 3. RTK Fix Percentage
    ax3 = axes[1, 0]
    colors_rtk = ['green' if p >= 90 else 'orange' if p >= 70 else 'red' for p in rtk_percentages]
    bars3 = ax3.bar(dates, rtk_percentages, color=colors_rtk, alpha=0.8, width=15)
    ax3.axhline(y=90, color='green', linestyle='--', alpha=0.5, label='Excellent (90%)')
    ax3.axhline(y=70, color='orange', linestyle='--', alpha=0.5, label='Good (70%)')
    ax3.set_ylabel('RTK Fix Percentage (%)', fontsize=11)
    ax3.set_title('Data Quality (RTK Fix Rate)', fontsize=12, fontweight='bold')
    ax3.set_ylim(0, 105)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
    ax3.legend(loc='lower right', fontsize=9)
    ax3.grid(axis='y', alpha=0.3)

    # 4. Total surveyed length
    ax4 = axes[1, 1]
    bars4 = ax4.bar(dates, total_lengths, color='mediumpurple', alpha=0.8, width=15)
    ax4.set_ylabel('Total Length (km)', fontsize=11)
    ax4.set_title('Total Transect Length per Survey', fontsize=12, fontweight='bold')
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')
    ax4.grid(axis='y', alpha=0.3)

    # Add summary text box
    summary = surveys['summary']
    summary_text = (
        f"Summary Statistics\n"
        f"─────────────────\n"
        f"Survey Dates: {summary['total_survey_dates']}\n"
        f"Total Transects: {summary['total_transects']:,}\n"
        f"Total Points: {summary['total_points']:,}\n"
        f"Date Range: {summary['date_range']['start']}\n"
        f"         to {summary['date_range']['end']}"
    )

    fig.text(0.98, 0.02, summary_text, transform=fig.transFigure,
             fontsize=10, verticalalignment='bottom', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8),
             family='monospace')

    plt.suptitle('Oceanside Beach Survey Statistics (2022-2026)',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"Statistics dashboard saved to: {output_path}")
    return output_path


def main():
    """Generate all visualizations"""
    print("="*60)
    print("GENERATING PHASE 1 VISUALIZATIONS")
    print("="*60)

    # Load data
    print("\nLoading processed data...")
    surveys, transects = load_survey_data()
    print(f"  Loaded {len(surveys['surveys'])} surveys")
    print(f"  Loaded {len(transects['features'])} transects")

    # Create visualizations
    print("\n[1/3] Creating interactive map...")
    map_path = create_interactive_map(transects)

    print("\n[2/3] Creating elevation profiles...")
    profiles_path = create_elevation_profiles()

    print("\n[3/3] Creating statistics dashboard...")
    stats_path = create_statistics_dashboard(surveys)

    print("\n" + "="*60)
    print("VISUALIZATIONS COMPLETE!")
    print("="*60)
    print(f"\nOutput files in 'visualizations/' directory:")
    print(f"  - transects_map.html  (open in browser)")
    print(f"  - elevation_profiles.png")
    print(f"  - survey_statistics.png")


if __name__ == '__main__':
    main()
