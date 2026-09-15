'use client';

import { useEffect } from 'react';
import { initWebVitals } from './web-vitals';

/**
 * Client component wrapper for Web Vitals initialization
 * Ensures proper timing and error handling
 */
export function WebVitalsWrapper() {
  useEffect(() => {
    // Initialize web vitals after component mount
    // This ensures the performance API is fully ready
    const timer = setTimeout(() => {
      initWebVitals();
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  return null; // This component doesn't render anything
}
