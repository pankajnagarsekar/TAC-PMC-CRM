FROM node:20-alpine AS base
RUN npm install -g pnpm@10.30.3

FROM base AS builder
WORKDIR /repo

# Force hoisting so standalone build can find and copy dependencies correctly in a pnpm monorepo
RUN echo "shamefully-hoist=true" > .npmrc

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

# Next.js standalone in a monorepo preserves the directory structure.
# The server.js entry point will be at apps/web/server.js inside the standalone folder.
COPY --from=builder /repo/apps/web/.next/standalone ./
COPY --from=builder /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /repo/apps/web/public ./apps/web/public

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Note: server.js is located within the preserved apps/web path
CMD ["node", "apps/web/server.js"]
