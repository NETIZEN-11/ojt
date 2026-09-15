/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // Disable strict mode to reduce web vitals
  experimental: {
    optimizePackageImports: ["lucide-react", "@radix-ui/react-icons"],
  },
  images: {
    domains: ["localhost"],
  },
  // Production optimizations
  productionBrowserSourceMaps: false,
  // Suppress non-critical errors in development
  onDemandEntries: {
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
  },
  // Webpack config to exclude web-vitals
  webpack: (config, { dev, isServer }) => {
    if (!isServer) {
      // Completely remove web-vitals from bundle
      config.resolve.alias = {
        ...config.resolve.alias,
        'next/dist/compiled/web-vitals': false,
        'web-vitals': false,
      };
      
      // DefinePlugin skipped (web-vitals aliased to false above is sufficient)
    }
    return config;
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
      },
    ];
  },
};

export default nextConfig;
