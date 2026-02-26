# frontend/Dockerfile
# ─────────────────────────────────────────────────────────────
#  Wieloetapowy build Reacta → Nginx
# ─────────────────────────────────────────────────────────────

# Etap 1: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Etap 2: serwowanie przez Nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# Konfiguracja Nginx dla React SPA (obsługa client-side routingu)
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    gzip on; \
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2|woff|ttf)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
}' > /etc/nginx/conf.d/default.conf
EXPOSE 80
