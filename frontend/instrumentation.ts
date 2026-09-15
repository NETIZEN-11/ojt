/**
 * Next.js Instrumentation
 * Disables web vitals to prevent console errors
 */

export async function register() {
  // Disable web vitals completely
  if (typeof window !== 'undefined') {
    // Override web vitals functions to do nothing
    (window as any).webVitals = null;
    (window as any).__NEXT_DATA__ = {
      ...(window as any).__NEXT_DATA__,
      props: {
        ...(window as any).__NEXT_DATA__?.props,
        pageProps: {
          ...(window as any).__NEXT_DATA__?.props?.pageProps,
          __N_SSP: false,
        },
      },
    };
  }
}
