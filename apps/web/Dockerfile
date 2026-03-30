FROM node:20-alpine AS base
RUN npm install -g pnpm@10.30.3

FROM base AS builder
WORKDIR /repo

# Ensure flat node_modules for proper dependency resolution
RUN echo "shamefully-hoist=true" > .npmrc && \
    echo "public-hoist-pattern[]=*;" >> .npmrc

COPY pnpm-workspace.yaml package.json pnpm-lock.yaml turbo.json ./
COPY packages/ ./packages/
COPY apps/web/ ./apps/web/

RUN pnpm install --frozen-lockfile

ARG NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL
RUN pnpm --filter tac-pmc-web build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy standalone output
COPY --from=builder /repo/apps/web/.next/standalone ./

# Copy static files and public assets
COPY --from=builder /repo/apps/web/.next/static ./.next/static
COPY --from=builder /repo/apps/web/public ./public

# Copy production node_modules from builder (required for Next.js server)
COPY --from=builder /repo/node_modules ./node_modules

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
