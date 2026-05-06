import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    unoptimized: true,
  },
  // Allow external image domains (UPI QR code generator)
  remotePatterns: [
    {
      protocol: "https",
      hostname: "api.qrserver.com",
    },
  ],
};

export default nextConfig;
