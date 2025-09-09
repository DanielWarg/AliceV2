/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/orchestrator/:path*',
        destination: 'http://localhost:8001/:path*'
      },
      {
        source: '/api/guardian/:path*', 
        destination: 'http://localhost:8787/:path*'
      },
      {
        source: '/api/nlu/:path*',
        destination: 'http://localhost:9002/:path*'
      },
      {
        source: '/api/voice/:path*',
        destination: 'http://localhost:8002/:path*'
      }
    ];
  },
  images: {
    domains: ['localhost'],
  },
};

module.exports = nextConfig;