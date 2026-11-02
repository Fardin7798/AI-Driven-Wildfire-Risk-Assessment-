import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Sandbox preview via Cloudflare quick tunnel
  devIndicators: false,
  allowedDevOrigins: ["*.trycloudflare.com"],
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
