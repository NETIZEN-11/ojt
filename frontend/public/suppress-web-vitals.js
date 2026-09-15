// ULTRA-AGGRESSIVE Web Vitals Error Suppression
// This runs BEFORE any other script

(function() {
  'use strict';
  
  // Store original functions
  const originalConsoleError = console.error;
  const originalConsoleWarn = console.warn;
  
  // Create a whitelist of error patterns to suppress
  const suppressPatterns = [
    'startTime',
    'reportAllChanges',
    '<anonymous>:2:',
    'VM',
    'web-vitals',
    'et.reportAllChanges'
  ];
  
  // Helper to check if error should be suppressed
  function shouldSuppress(args) {
    const message = args.map(arg => String(arg)).join(' ');
    return suppressPatterns.some(pattern => message.includes(pattern));
  }
  
  // Override console.error
  console.error = function(...args) {
    if (shouldSuppress(args)) {
      return; // Completely suppress
    }
    originalConsoleError.apply(console, args);
  };
  
  // Override console.warn
  console.warn = function(...args) {
    if (shouldSuppress(args)) {
      return;
    }
    originalConsoleWarn.apply(console, args);
  };
  
  // Intercept global error handler
  window.addEventListener('error', function(event) {
    if (event.message) {
      const msg = String(event.message);
      if (suppressPatterns.some(pattern => msg.includes(pattern))) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        return false;
      }
    }
  }, true); // Use capture phase to run before other handlers
  
  // Intercept unhandled rejections
  window.addEventListener('unhandledrejection', function(event) {
    if (event.reason) {
      const msg = String(event.reason.message || event.reason);
      if (suppressPatterns.some(pattern => msg.includes(pattern))) {
        event.preventDefault();
        event.stopPropagation();
        return false;
      }
    }
  }, true);
  
  // Monkey-patch Error constructor to catch errors at creation
  const OriginalError = Error;
  Error = function(...args) {
    const err = new OriginalError(...args);
    const message = String(args[0] || '');
    if (suppressPatterns.some(pattern => message.includes(pattern))) {
      // Mark this error as suppressed
      Object.defineProperty(err, '__suppressed__', {
        value: true,
        writable: false,
        enumerable: false
      });
    }
    return err;
  };
  Error.prototype = OriginalError.prototype;
  Error.captureStackTrace = OriginalError.captureStackTrace;
  
  // Wrap setTimeout and setInterval to catch errors
  const originalSetTimeout = window.setTimeout;
  const originalSetInterval = window.setInterval;
  
  window.setTimeout = function(fn, ...args) {
    const wrappedFn = function() {
      try {
        return fn.apply(this, arguments);
      } catch (e) {
        if (!shouldSuppress([e.message || e])) {
          throw e;
        }
      }
    };
    return originalSetTimeout(wrappedFn, ...args);
  };
  
  window.setInterval = function(fn, ...args) {
    const wrappedFn = function() {
      try {
        return fn.apply(this, arguments);
      } catch (e) {
        if (!shouldSuppress([e.message || e])) {
          throw e;
        }
      }
    };
    return originalSetInterval(wrappedFn, ...args);
  };
  
  // Wrap requestIdleCallback specifically
  if (window.requestIdleCallback) {
    const originalRequestIdleCallback = window.requestIdleCallback;
    window.requestIdleCallback = function(callback, options) {
      const wrappedCallback = function(deadline) {
        try {
          return callback(deadline);
        } catch (e) {
          if (!shouldSuppress([e.message || e])) {
            throw e;
          }
          // Suppress web vitals errors silently
        }
      };
      return originalRequestIdleCallback(wrappedCallback, options);
    };
  }
  
  console.log('%c[Web Vitals Suppressor] Loaded', 'color: green; font-weight: bold');
})();
