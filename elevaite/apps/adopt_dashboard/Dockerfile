FROM node:20-alpine AS base

FROM base AS builder
RUN apk add --no-cache libc6-compat
RUN apk update
# Set working directory
WORKDIR /app
RUN npm install -g turbo
COPY . .
RUN turbo prune adopt_dashboard --docker

# Add lockfile and package.json's of isolated subworkspace
FROM base AS installer
RUN apk add --no-cache libc6-compat
RUN apk update
WORKDIR /app

# First install the dependencies (as they change less often)
COPY .gitignore .gitignore
COPY --from=builder /app/out/json/ .
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN npm cache clear --force
RUN npm ci

# Build the project
COPY --from=builder /app/out/full/ .
COPY turbo.json turbo.json

# Debug: Check files before build
RUN echo "=== Files before build ===" && ls -la apps/adopt_dashboard/

# Build the project
RUN npx --yes turbo run build --filter=adopt_dashboard...

# Debug: Check if standalone build was created
RUN echo "=== Files after build ===" && ls -la apps/adopt_dashboard/.next/
RUN echo "=== Checking for standalone ===" && ls -la apps/adopt_dashboard/.next/standalone/ || echo "No standalone directory found"

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Don't run production as root
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
USER nextjs

COPY --from=installer /app/apps/adopt_dashboard/next.config.mjs .
COPY --from=installer /app/apps/adopt_dashboard/package.json .
COPY --from=installer --chown=nextjs:nodejs /app/apps/adopt_dashboard/.next/standalone ./
COPY --from=installer --chown=nextjs:nodejs /app/apps/adopt_dashboard/.next/static ./.next/static
COPY --from=installer --chown=nextjs:nodejs /app/apps/adopt_dashboard/public ./public

# Copy node_modules if standalone build didn't include them
COPY --from=installer --chown=nextjs:nodejs /app/node_modules ./node_modules

USER nextjs

EXPOSE 3005

ENV PORT=3005

CMD ["node", "server.js"]
