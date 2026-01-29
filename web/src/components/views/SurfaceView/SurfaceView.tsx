import { Suspense, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment } from '@react-three/drei';
import { useStore } from '../../../store';
import { useSurfacesIndex, useSurfaceData } from '../../../hooks/useSurfaceData';
import { BeachTerrain } from './BeachTerrain';
import { Timeline } from '../../shared/Timeline';
import { ElevationLegend } from '../../shared/ElevationLegend';

function LoadingIndicator() {
  return (
    <mesh>
      <boxGeometry args={[100, 100, 100]} />
      <meshStandardMaterial color="#666" wireframe />
    </mesh>
  );
}

function Scene() {
  const { currentDate, isLoading } = useStore();
  const surfaceData = useSurfaceData(currentDate);

  // Calculate camera target based on surface bounds
  const cameraTarget = useMemo(() => {
    if (!surfaceData) return [0, 0, 0] as [number, number, number];
    const { bounds } = surfaceData.metadata;
    const centerX = (bounds.x_min + bounds.x_max) / 2;
    const centerY = (bounds.y_min + bounds.y_max) / 2;
    return [centerX, 0, -centerY] as [number, number, number];
  }, [surfaceData]);

  // Calculate camera position based on surface size
  const cameraPosition = useMemo(() => {
    if (!surfaceData) return [0, 2000, 2000] as [number, number, number];
    const { bounds } = surfaceData.metadata;
    const width = bounds.x_max - bounds.x_min;
    const height = bounds.y_max - bounds.y_min;
    const maxDim = Math.max(width, height);
    const distance = maxDim * 0.8;
    const centerX = (bounds.x_min + bounds.x_max) / 2;
    const centerY = (bounds.y_min + bounds.y_max) / 2;
    return [centerX, distance, -centerY + distance] as [number, number, number];
  }, [surfaceData]);

  return (
    <>
      <PerspectiveCamera
        makeDefault
        position={cameraPosition}
        fov={50}
        near={1}
        far={50000}
      />
      <OrbitControls
        target={cameraTarget}
        enableDamping
        dampingFactor={0.05}
        minDistance={100}
        maxDistance={20000}
        maxPolarAngle={Math.PI / 2.1}
      />

      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[1000, 2000, 1000]}
        intensity={1}
        castShadow
      />
      <directionalLight
        position={[-500, 1000, -500]}
        intensity={0.3}
      />

      {/* Sky/environment */}
      <Environment preset="sunset" background={false} />
      <color attach="background" args={['#1a1a2e']} />

      {/* Terrain */}
      <Suspense fallback={<LoadingIndicator />}>
        {surfaceData && !isLoading && (
          <BeachTerrain data={surfaceData} verticalScale={3} />
        )}
      </Suspense>

      {/* Ground plane for context */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -50, 0]}>
        <planeGeometry args={[50000, 50000]} />
        <meshStandardMaterial color="#0a1628" transparent opacity={0.5} />
      </mesh>
    </>
  );
}

export function SurfaceView() {
  const { error, isLoading } = useStore();
  const surfacesIndex = useSurfacesIndex();

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-red-500 text-center">
          <h2 className="text-xl font-bold mb-2">Error Loading Data</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!surfacesIndex) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-white text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4" />
          <p>Loading survey data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-gray-900">
      {/* 3D Canvas */}
      <Canvas>
        <Scene />
      </Canvas>

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center pointer-events-none">
          <div className="text-white text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2" />
            <p>Loading surface...</p>
          </div>
        </div>
      )}

      {/* Timeline control (bottom) */}
      <div className="absolute bottom-4 left-4 right-4">
        <Timeline />
      </div>

      {/* Elevation legend (top right) */}
      <div className="absolute top-4 right-4">
        <ElevationLegend />
      </div>

      {/* Title (top left) */}
      <div className="absolute top-4 left-4">
        <h1 className="text-white text-2xl font-bold">Oceanside Beach Survey</h1>
        <p className="text-gray-400 text-sm">3D Surface Visualization</p>
      </div>

      {/* Controls help (bottom right) */}
      <div className="absolute bottom-20 right-4 text-gray-400 text-xs">
        <p>Drag to rotate | Scroll to zoom | Shift+drag to pan</p>
      </div>
    </div>
  );
}
