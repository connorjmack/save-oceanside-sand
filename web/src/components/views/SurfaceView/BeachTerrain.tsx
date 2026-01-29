import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { DEMData } from '../../../types/dem';
import { interpolateColor, BEACH_COLOR_RAMP } from '../../../utils/color-ramps';

interface BeachTerrainProps {
  data: DEMData;
  verticalScale?: number;
}

export function BeachTerrain({ data, verticalScale = 1 }: BeachTerrainProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  const geometry = useMemo(() => {
    const { metadata, heights } = data;
    const { n_rows, n_cols, bounds, nodata_value } = metadata;

    // Calculate dimensions in local coordinates
    const width = bounds.x_max - bounds.x_min;
    const height = bounds.y_max - bounds.y_min;

    // Create geometry
    const geo = new THREE.PlaneGeometry(
      width,
      height,
      n_cols - 1,
      n_rows - 1
    );

    // Get position attribute
    const positions = geo.attributes.position.array as Float32Array;
    const colorArray = new Float32Array(positions.length);

    // Track elevation range for valid cells
    let validMin = Infinity;
    let validMax = -Infinity;

    // First pass: find elevation range
    for (let row = 0; row < n_rows; row++) {
      for (let col = 0; col < n_cols; col++) {
        const dataIndex = row * n_cols + col;
        const z = heights[dataIndex];

        if (z !== nodata_value && !isNaN(z) && isFinite(z)) {
          validMin = Math.min(validMin, z);
          validMax = Math.max(validMax, z);
        }
      }
    }

    // Second pass: set positions and colors
    for (let row = 0; row < n_rows; row++) {
      for (let col = 0; col < n_cols; col++) {
        // PlaneGeometry vertices are ordered by rows (bottom to top)
        const vertexIndex = row * n_cols + col;
        const posIndex = vertexIndex * 3;

        // Get height from DEM (row-major, top to bottom)
        const dataRow = n_rows - 1 - row;  // Flip row order
        const dataIndex = dataRow * n_cols + col;
        let z = heights[dataIndex];

        // Handle nodata
        if (z === nodata_value || isNaN(z) || !isFinite(z)) {
          z = validMin;  // Use minimum valid elevation for nodata
        }

        // Set Z position (scaled)
        positions[posIndex + 2] = z * verticalScale;

        // Set color based on elevation
        const color = interpolateColor(z, BEACH_COLOR_RAMP);
        colorArray[posIndex] = color.r;
        colorArray[posIndex + 1] = color.g;
        colorArray[posIndex + 2] = color.b;
      }
    }

    // Update position attribute
    geo.attributes.position.needsUpdate = true;

    // Add color attribute
    geo.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));

    // Compute normals for lighting
    geo.computeVertexNormals();

    return geo;
  }, [data, verticalScale]);

  // Center position based on bounds
  const position = useMemo(() => {
    const { bounds } = data.metadata;
    const centerX = (bounds.x_min + bounds.x_max) / 2;
    const centerY = (bounds.y_min + bounds.y_max) / 2;
    return [centerX, centerY, 0] as [number, number, number];
  }, [data.metadata]);

  return (
    <mesh
      ref={meshRef}
      geometry={geometry}
      position={position}
      rotation={[-Math.PI / 2, 0, 0]}  // Rotate to horizontal
    >
      <meshStandardMaterial
        vertexColors
        side={THREE.DoubleSide}
        flatShading={false}
      />
    </mesh>
  );
}
