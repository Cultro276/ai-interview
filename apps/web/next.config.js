/** @type {import('next').NextConfig} */
const withBundleAnalyzer = (() => {
  try {
    // Optional: available in dev/build when installed. Falls back to identity wrapper if missing.
    return require('@next/bundle-analyzer')({ enabled: process.env.ANALYZE === 'true' });
  } catch (e) {
    return (config) => config;
  }
})();

const nextConfig = {
  reactStrictMode: true,
};

module.exports = withBundleAnalyzer(nextConfig);