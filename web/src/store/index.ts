import { create } from 'zustand';
import type { DEMData, SurfacesIndex } from '../types/dem';

interface AppState {
  // Timeline state
  currentDate: string | null;
  availableDates: string[];
  isAnimating: boolean;
  animationSpeed: number;

  // Surface data
  surfacesIndex: SurfacesIndex | null;
  surfaceCache: Map<string, DEMData>;
  isLoading: boolean;
  error: string | null;

  // Camera state (persisted across date changes)
  cameraPosition: [number, number, number];
  cameraTarget: [number, number, number];

  // Actions
  setCurrentDate: (date: string) => void;
  setAvailableDates: (dates: string[]) => void;
  setSurfacesIndex: (index: SurfacesIndex) => void;
  cacheSurface: (date: string, data: DEMData) => void;
  getCachedSurface: (date: string) => DEMData | undefined;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setAnimating: (animating: boolean) => void;
  setAnimationSpeed: (speed: number) => void;
  setCameraPosition: (position: [number, number, number]) => void;
  setCameraTarget: (target: [number, number, number]) => void;
  nextDate: () => void;
  prevDate: () => void;
}

const MAX_CACHE_SIZE = 5;

export const useStore = create<AppState>((set, get) => ({
  // Initial state
  currentDate: null,
  availableDates: [],
  isAnimating: false,
  animationSpeed: 1000,
  surfacesIndex: null,
  surfaceCache: new Map(),
  isLoading: false,
  error: null,
  cameraPosition: [0, 500, 1000],
  cameraTarget: [0, 0, 0],

  // Actions
  setCurrentDate: (date) => set({ currentDate: date }),

  setAvailableDates: (dates) => {
    set({ availableDates: dates });
    if (dates.length > 0 && !get().currentDate) {
      set({ currentDate: dates[0] });
    }
  },

  setSurfacesIndex: (index) => {
    set({ surfacesIndex: index });
    const dates = index.surfaces.map((s) => s.date).sort();
    get().setAvailableDates(dates);
  },

  cacheSurface: (date, data) => {
    const cache = new Map(get().surfaceCache);

    // Evict oldest entries if cache is full
    if (cache.size >= MAX_CACHE_SIZE) {
      const firstKey = cache.keys().next().value;
      if (firstKey) {
        cache.delete(firstKey);
      }
    }

    cache.set(date, data);
    set({ surfaceCache: cache });
  },

  getCachedSurface: (date) => get().surfaceCache.get(date),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  setAnimating: (animating) => set({ isAnimating: animating }),

  setAnimationSpeed: (speed) => set({ animationSpeed: speed }),

  setCameraPosition: (position) => set({ cameraPosition: position }),

  setCameraTarget: (target) => set({ cameraTarget: target }),

  nextDate: () => {
    const { availableDates, currentDate } = get();
    if (!currentDate || availableDates.length === 0) return;

    const currentIndex = availableDates.indexOf(currentDate);
    const nextIndex = (currentIndex + 1) % availableDates.length;
    set({ currentDate: availableDates[nextIndex] });
  },

  prevDate: () => {
    const { availableDates, currentDate } = get();
    if (!currentDate || availableDates.length === 0) return;

    const currentIndex = availableDates.indexOf(currentDate);
    const prevIndex = currentIndex === 0 ? availableDates.length - 1 : currentIndex - 1;
    set({ currentDate: availableDates[prevIndex] });
  },
}));
