/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    serverComponentsExternalPackages: [],
  },
  transpilePackages: ["@alice/ui", "@alice/api", "@alice/types"],
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
    NEXT_PUBLIC_WS_BASE_URL: process.env.NEXT_PUBLIC_WS_BASE_URL || "ws://localhost:8000",
    NEXT_PUBLIC_GUARDIAN_URL: process.env.NEXT_PUBLIC_GUARDIAN_URL || "http://localhost:8787",
  },
};

export default nextConfig;
