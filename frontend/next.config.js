/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  // OSS/CDN resolves directory indexes reliably. This emits /try/index.html
  // rather than try.html, so extensionless product links work without a
  // provider-specific rewrite rule.
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

module.exports = nextConfig;
