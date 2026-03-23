import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.CORE_API_INTERNAL_URL || "http://core_api:8000"}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
