FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
ARG BACKEND_URL=http://lionsforge-backend
ENV BACKEND_URL=${BACKEND_URL}
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs \
    && rm -rf /usr/local/lib/node_modules/npm \
       /usr/local/lib/node_modules/corepack \
       /usr/local/bin/npm \
       /usr/local/bin/npx \
       /usr/local/bin/corepack \
       /usr/local/bin/yarn \
       /usr/local/bin/yarnpkg \
       /usr/local/bin/pnpm \
       /usr/local/bin/pnpx
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
