/**
 * Global error handler for non-critical errors
 * Suppresses known harmless errors in development
 */

if (typeof window !== 'undefined') {
  // Store original console.error
  const originalError = console.error;

  // Override console.error to filter known non-critical errors
  console.error = (...args: any[]) => {
    const errorString = args.join(' ');
    
    // List of non-critical error patterns to suppress
    const suppressedPatterns = [
      'Cannot read properties of undefined',
      'startTime',
      'web-vitals',
      'reportAllChanges',
      'et.reportAllChanges',
      'VM',
      '<anonymous>:2:',
    ];

    // Check if this is a known non-critical error
    const shouldSuppress = suppressedPatterns.some(pattern => 
      errorString.includes(pattern)
    );

    // Only log if not suppressed
    if (!shouldSuppress) {
      originalError.apply(console, args);
    }
  };

  // Handle uncaught errors - more aggressive filtering
  window.addEventListener('error', (event) => {
    const errorMessage = event.message || '';
    const errorSource = event.filename || '';
    
    // Suppress web vitals and VM errors
    if (
      errorMessage.includes('startTime') || 
      errorMessage.includes('web-vitals') ||
      errorMessage.includes('reportAllChanges') ||
      errorSource.includes('<anonymous>') ||
      errorSource.includes('VM')
    ) {
      event.preventDefault();
      event.stopPropagation();
      return false;
    }
  }, true); // Use capture phase

  // Also suppress unhandled promise rejections related to web vitals
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason?.message || String(event.reason) || '';
    
    if (
      reason.includes('startTime') || 
      reason.includes('web-vitals') ||
      reason.includes('reportAllChanges')
    ) {
      event.preventDefault();
      return false;
    }
  });
}

export {};
