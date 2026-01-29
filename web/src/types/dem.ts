export interface DEMBounds {
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
  min_lat: number;
  max_lat: number;
  min_lon: number;
  max_lon: number;
}

export interface DEMMetadata {
  survey_date: string;
  n_rows: number;
  n_cols: number;
  resolution: number;
  bounds: DEMBounds;
  origin: {
    lat: number;
    lon: number;
  };
  nodata_value: number;
  point_count: number;
  elevation_stats: {
    min: number;
    max: number;
    mean: number;
  };
  valid_cell_count: number;
  total_cell_count: number;
}

export interface DEMData {
  metadata: DEMMetadata;
  heights: Float32Array;
}

export interface SurfaceIndexEntry {
  date: string;
  point_count: number;
  n_rows: number;
  n_cols: number;
  valid_cells: number;
  elevation_min: number;
  elevation_max: number;
  bounds: DEMBounds;
}

export interface SurfacesIndex {
  surfaces: SurfaceIndexEntry[];
  resolution: number;
  method: string;
  origin: {
    lat: number;
    lon: number;
  };
}
