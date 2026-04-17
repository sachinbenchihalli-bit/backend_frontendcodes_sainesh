FROM node:20-alpine AS base

FROM base AS builder
RUN apk add --no-cache libc6-compat
RUN apk update
# Set working directory
WORKDIR /app
RUN npm install -g turbo
COPY . .
RUN turbo prune media_dashboard --docker

# Add lockfile and package.json's of isolated subworkspace
FROM base AS installer
RUN apk add --no-cache libc6-compat
RUN apk update
WORKDIR /app

# First install the dependencies (as they change less often)
COPY .gitignor[e] .gitignore
COPY --from=builder /app/out/json/ .
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN npm cache clear --force 
RUN npm ci

# Build the project
COPY --from=builder /app/out/full/ .
COPY turbo.json turbo.json
RUN npx --yes turbo run build --filter=media_dashboard...

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Don't run production as root
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
USER nextjs

COPY --from=installer /app/apps/media_dashboard/next.config.mjs .
COPY --from=installer /app/apps/media_dashboard/package.json .

# Automatically leverage output traces to reduce image size
COPY --from=installer --chown=nextjs:nodejs /app/apps/media_dashboard/.next/standalone ./
COPY --from=installer --chown=nextjs:nodejs /app/apps/media_dashboard/.next/static ./apps/media_dashboard/.next/static
COPY --from=installer --chown=nextjs:nodejs /app/apps/media_dashboard/public ./apps/media_dashboard/public

USER nextjs

EXPOSE 3003

ENV PORT=3003

CMD ["node", "apps/media_dashboard/server.js"]