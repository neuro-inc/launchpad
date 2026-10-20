# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc,required=true \
    --mount=type=secret,id=npm_token,env=FONTAWESOME_NPM_AUTH_TOKEN,required=true \
    npm ci
COPY . .
ARG COMMIT_SHA
ENV APP_COMMIT_SHA=$COMMIT_SHA NEXT_PUBLIC_ENVIRONMENT=production NEXT_TELEMETRY_DISABLED=1
RUN test "${#COMMIT_SHA}" -eq 40 && npm run build

FROM node:22-bookworm-slim AS runtime
LABEL org.opencontainers.image.source="https://github.com/neuro-inc/launchpad"
WORKDIR /app
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3000 NEXT_TELEMETRY_DISABLED=1
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
COPY --chown=node:node deploy/start.mjs ./start.mjs
USER node
EXPOSE 3000
CMD ["node", "start.mjs"]
