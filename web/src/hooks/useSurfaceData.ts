import { useEffect, useState } from 'react';
import { useStore } from '../store';
import type { DEMData, DEMMetadata, SurfacesIndex } from '../types/dem';

const SURFACES_BASE_PATH = '/processed/surfaces';

async function loadSurfacesIndex(): Promise<SurfacesIndex> {
  const response = await fetch(`${SURFACES_BASE_PATH}/surfaces_index.json`);
  if (!response.ok) {
    throw new Error(`Failed to load surfaces index: ${response.statusText}`);
  }
  return response.json();
}

async function loadDEMMetadata(date: string): Promise<DEMMetadata> {
  const response = await fetch(`${SURFACES_BASE_PATH}/${date}.dem.json`);
  if (!response.ok) {
    throw new Error(`Failed to load DEM metadata for ${date}: ${response.statusText}`);
  }
  return response.json();
}

async function loadDEMBinary(date: string): Promise<ArrayBuffer> {
  const response = await fetch(`${SURFACES_BASE_PATH}/${date}.dem.bin`);
  if (!response.ok) {
    throw new Error(`Failed to load DEM binary for ${date}: ${response.statusText}`);
  }
  return response.arrayBuffer();
}

export async function loadSurfaceData(date: string): Promise<DEMData> {
  const [metadata, buffer] = await Promise.all([
    loadDEMMetadata(date),
    loadDEMBinary(date),
  ]);

  const heights = new Float32Array(buffer);
  return { metadata, heights };
}

export function useSurfacesIndex() {
  const { surfacesIndex, setSurfacesIndex, setError } = useStore();

  useEffect(() => {
    if (surfacesIndex) return;

    loadSurfacesIndex()
      .then(setSurfacesIndex)
      .catch((err) => setError(err.message));
  }, [surfacesIndex, setSurfacesIndex, setError]);

  return surfacesIndex;
}

export function useSurfaceData(date: string | null) {
  const { getCachedSurface, cacheSurface, setLoading, setError } = useStore();
  const [data, setData] = useState<DEMData | null>(null);

  useEffect(() => {
    if (!date) {
      setData(null);
      return;
    }

    // Check cache first
    const cached = getCachedSurface(date);
    if (cached) {
      setData(cached);
      return;
    }

    // Load from server
    setLoading(true);
    setError(null);

    loadSurfaceData(date)
      .then((loaded) => {
        cacheSurface(date, loaded);
        setData(loaded);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [date, getCachedSurface, cacheSurface, setLoading, setError]);

  return data;
}
