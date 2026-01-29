import * as THREE from 'three';

export interface ColorStop {
  value: number;
  color: THREE.Color;
}

// Beach elevation color ramp
// Deep water (dark blue) -> shallow water (light blue) -> sand (tan) -> dunes (green)
export const BEACH_COLOR_RAMP: ColorStop[] = [
  { value: -40, color: new THREE.Color(0x0a1628) },  // Deep ocean (dark blue)
  { value: -30, color: new THREE.Color(0x1a4a6e) },  // Deep water
  { value: -20, color: new THREE.Color(0x2d7da8) },  // Mid water
  { value: -10, color: new THREE.Color(0x4ba3c7) },  // Shallow water
  { value: 0, color: new THREE.Color(0x7ec8e3) },    // Very shallow / tidal
  { value: 2, color: new THREE.Color(0xf5deb3) },    // Wet sand
  { value: 5, color: new THREE.Color(0xd4a574) },    // Dry sand
  { value: 10, color: new THREE.Color(0xa8c686) },   // Beach grass / low dunes
  { value: 15, color: new THREE.Color(0x6b8e23) },   // Dunes / vegetation
  { value: 25, color: new THREE.Color(0x556b2f) },   // High dunes
];

export function interpolateColor(
  value: number,
  ramp: ColorStop[] = BEACH_COLOR_RAMP
): THREE.Color {
  // Clamp to ramp range
  const minVal = ramp[0].value;
  const maxVal = ramp[ramp.length - 1].value;
  const clampedValue = Math.max(minVal, Math.min(maxVal, value));

  // Find surrounding color stops
  let lowerStop = ramp[0];
  let upperStop = ramp[ramp.length - 1];

  for (let i = 0; i < ramp.length - 1; i++) {
    if (clampedValue >= ramp[i].value && clampedValue <= ramp[i + 1].value) {
      lowerStop = ramp[i];
      upperStop = ramp[i + 1];
      break;
    }
  }

  // Interpolate between stops
  const range = upperStop.value - lowerStop.value;
  const t = range === 0 ? 0 : (clampedValue - lowerStop.value) / range;

  const result = new THREE.Color();
  result.lerpColors(lowerStop.color, upperStop.color, t);
  return result;
}

export function createColorRampTexture(
  ramp: ColorStop[] = BEACH_COLOR_RAMP,
  width: number = 256
): THREE.DataTexture {
  const data = new Uint8Array(width * 4);
  const minVal = ramp[0].value;
  const maxVal = ramp[ramp.length - 1].value;
  const range = maxVal - minVal;

  for (let i = 0; i < width; i++) {
    const value = minVal + (i / (width - 1)) * range;
    const color = interpolateColor(value, ramp);

    data[i * 4] = Math.floor(color.r * 255);
    data[i * 4 + 1] = Math.floor(color.g * 255);
    data[i * 4 + 2] = Math.floor(color.b * 255);
    data[i * 4 + 3] = 255;
  }

  const texture = new THREE.DataTexture(data, width, 1, THREE.RGBAFormat);
  texture.needsUpdate = true;
  return texture;
}
