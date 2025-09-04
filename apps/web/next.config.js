/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@alice/ui", "@alice/api", "@alice/types"],
  experimental: {
    turbo: {
      rules: {
        "*.css": {
          loaders: ["css-loader"],
          as: "*.css",
        },
      },
    },
  },
};

module.exports = nextConfig;
