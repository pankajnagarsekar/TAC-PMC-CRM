FROM node:20-alpine AS base
RUN npm install -g pnpm@10.30.3

FROM base AS builder
WORKDIR /repo

# IMPROVED: Ensure a completely flat node_modules structure so Next.js standalone 
# can correctly resolve and copy all dependencies into the build artifact.
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

# The standalone folder contains the minimal server and node_modules
COPY --from=builder /repo/apps/web/.next/standalone ./
COPY --from=builder /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /repo/apps/web/public ./apps/web/public

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Note: In monorepos, the entry point remains at the original subpath
CMD ["node", "apps/web/server.js"]
