/** @type {import('next').NextConfig} */

const configuredApiUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
let configuredApiOrigin = "";
try {
  configuredApiOrigin = configuredApiUrl ? new URL(configuredApiUrl).origin : "";
} catch {
  // Invalid API URLs fail when requested; do not weaken CSP to accommodate one.
}

const connectSources = [
  "'self'",
  "http://localhost:*",
  "http://127.0.0.1:*",
  configuredApiOrigin,
].filter(Boolean);

const scriptSources = ["'self'", "'unsafe-inline'"];
if (process.env.NODE_ENV !== "production") {
  // Next.js development tooling uses eval for source maps and Fast Refresh.
  scriptSources.push("'unsafe-eval'");
}

const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src ${scriptSources.join(" ")}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src ${connectSources.join(" ")}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=()" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains",
  },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
];

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Standalone output for the Docker image: only the files actually needed at
  // runtime are copied into the final layer.
  output: "standalone",
  // Surface type and lint errors at build time rather than shipping past them.
  eslint: { ignoreDuringBuilds: false },
  typescript: { ignoreBuildErrors: false },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
