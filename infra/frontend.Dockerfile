FROM node:24.15.0-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY src/frontend src/frontend
COPY tsconfig.json vite.config.ts ./
RUN npm run build
FROM caddy:2.10-alpine
COPY --from=build /app/dist /srv
COPY infra/Caddyfile /etc/caddy/Caddyfile
EXPOSE 8080
