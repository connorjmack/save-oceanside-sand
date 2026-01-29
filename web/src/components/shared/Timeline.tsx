import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '../../store';

export function Timeline() {
  const {
    currentDate,
    availableDates,
    isAnimating,
    animationSpeed,
    setCurrentDate,
    setAnimating,
    nextDate,
    prevDate,
  } = useStore();

  const animationRef = useRef<number | null>(null);

  const currentIndex = currentDate ? availableDates.indexOf(currentDate) : 0;

  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const index = parseInt(e.target.value, 10);
      if (availableDates[index]) {
        setCurrentDate(availableDates[index]);
      }
    },
    [availableDates, setCurrentDate]
  );

  const toggleAnimation = useCallback(() => {
    setAnimating(!isAnimating);
  }, [isAnimating, setAnimating]);

  // Animation loop
  useEffect(() => {
    if (!isAnimating) {
      if (animationRef.current) {
        clearInterval(animationRef.current);
        animationRef.current = null;
      }
      return;
    }

    animationRef.current = window.setInterval(() => {
      nextDate();
    }, animationSpeed);

    return () => {
      if (animationRef.current) {
        clearInterval(animationRef.current);
      }
    };
  }, [isAnimating, animationSpeed, nextDate]);

  if (availableDates.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-900 bg-opacity-90 p-4 rounded-lg shadow-lg">
      <div className="flex items-center gap-4">
        {/* Previous button */}
        <button
          onClick={prevDate}
          disabled={isAnimating}
          className="p-2 rounded-full bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Previous date"
        >
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* Play/Pause button */}
        <button
          onClick={toggleAnimation}
          className="p-2 rounded-full bg-blue-600 hover:bg-blue-500 transition-colors"
          title={isAnimating ? 'Pause' : 'Play'}
        >
          {isAnimating ? (
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6" />
            </svg>
          ) : (
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            </svg>
          )}
        </button>

        {/* Next button */}
        <button
          onClick={nextDate}
          disabled={isAnimating}
          className="p-2 rounded-full bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Next date"
        >
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>

        {/* Slider */}
        <div className="flex-1 mx-4">
          <input
            type="range"
            min={0}
            max={availableDates.length - 1}
            value={currentIndex}
            onChange={handleSliderChange}
            disabled={isAnimating}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer disabled:cursor-not-allowed accent-blue-500"
          />
        </div>

        {/* Date display */}
        <div className="min-w-[120px] text-right">
          <span className="text-white font-mono text-lg">
            {currentDate || '--'}
          </span>
          <div className="text-gray-400 text-xs">
            {currentIndex + 1} / {availableDates.length}
          </div>
        </div>
      </div>
    </div>
  );
}
