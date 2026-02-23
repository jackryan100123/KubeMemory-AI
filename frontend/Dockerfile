# Stage 1: Node builder
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
# Use npm install so build works with or without package-lock.json
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Nginx runtime
FROM nginx:1.25-alpine AS runtime
RUN apk add --no-cache wget
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=5s --retries=3 --start-period=5s \
  CMD wget -q -O /dev/null http://localhost:80/ || exit 1
