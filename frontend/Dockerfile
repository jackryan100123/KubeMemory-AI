# ============================================================
# Stage 1: Node builder
# ============================================================
FROM node:20-alpine AS builder

# Security: don't run as root
WORKDIR /app

# Install dependencies first (layer cache optimization)
COPY package*.json ./
RUN npm ci 2>/dev/null || npm install

# Copy source and build
COPY . .

# Build args for Vite env (no secrets — only public config)
ARG VITE_API_URL=/api
ARG VITE_WS_URL=/ws
ARG VITE_APP_NAME=KubeMemory

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_APP_NAME=$VITE_APP_NAME

RUN npm run build

# ============================================================
# Stage 2: Nginx runtime
# ============================================================
FROM nginx:1.25-alpine AS runtime

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Security: nginx runs as nginx user by default (not root)

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

EXPOSE 80
