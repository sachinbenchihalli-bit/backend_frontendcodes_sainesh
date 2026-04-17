/** @type {import('next').NextConfig} */
const nextConfig = {
    basePath: '/dashboard',
    output: "standalone",
    transpilePackages: ["@repo/ui"],
    eslint: {
        ignoreDuringBuilds: true,
    },
    typescript: {
        // Disable TypeScript errors during build
        ignoreBuildErrors: true,
    },
    sassOptions: {
        includePaths: ["./app/ui"],
        prependData: `@import "@repo/sass-config/mainSass.scss";`,
    },
    images: {
        remotePatterns: [
            {
                protocol: "https",
                hostname: "lh3.googleusercontent.com",
                port: "",
                pathname: "/a/**",
            },
        ],
    },
};

export default nextConfig;
