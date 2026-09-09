import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.unsplash.com" },
      { protocol: "http", hostname: "localhost" },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:5000/api/:path*",
      },
      {
        source: "/output/:path*",
        destination: "http://localhost:5000/output/:path*",
      },
      {
        source: "/input/:path*",
        destination: "http://localhost:5000/input/:path*",
      },
    ];
  },
};

export default nextConfig;
