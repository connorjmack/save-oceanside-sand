import { BEACH_COLOR_RAMP } from '../../utils/color-ramps';

export function ElevationLegend() {
  const minElev = BEACH_COLOR_RAMP[0].value;
  const maxElev = BEACH_COLOR_RAMP[BEACH_COLOR_RAMP.length - 1].value;

  // Create gradient CSS from color ramp
  const gradientStops = BEACH_COLOR_RAMP.map((stop) => {
    const percent = ((stop.value - minElev) / (maxElev - minElev)) * 100;
    const r = Math.floor(stop.color.r * 255);
    const g = Math.floor(stop.color.g * 255);
    const b = Math.floor(stop.color.b * 255);
    return `rgb(${r}, ${g}, ${b}) ${percent}%`;
  }).join(', ');

  return (
    <div className="bg-gray-900 bg-opacity-90 p-3 rounded-lg shadow-lg">
      <div className="text-white text-xs font-semibold mb-2">Elevation (m)</div>
      <div className="flex items-stretch gap-2">
        {/* Color bar */}
        <div
          className="w-4 h-32 rounded"
          style={{
            background: `linear-gradient(to top, ${gradientStops})`,
          }}
        />
        {/* Labels */}
        <div className="flex flex-col justify-between text-white text-xs font-mono">
          <span>{maxElev}</span>
          <span>0</span>
          <span>{minElev}</span>
        </div>
      </div>
    </div>
  );
}
