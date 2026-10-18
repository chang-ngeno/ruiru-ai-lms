# ---- build ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_DEV_AUTH=false
ARG VITE_SITE_URL
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID VITE_DEV_AUTH=$VITE_DEV_AUTH
ENV VITE_SITE_URL=${VITE_SITE_URL:-https://learn.imperialenterprise.co.ke}
RUN npm run build

# ---- serve ----
FROM nginx:1.27-alpine
# nginx fills the *.template files in /etc/nginx/templates from these variables at start-up.
# Defaults suit docker-compose; on Render set BACKEND_URL / BACKEND_HOST to your API service.
ENV PORT=80 \
    BACKEND_URL=http://backend:5000 \
    BACKEND_HOST=backend:5000 \
    RESOLVER="1.1.1.1 8.8.8.8" \
    NGINX_ENVSUBST_FILTER="^(PORT|BACKEND_URL|BACKEND_HOST|RESOLVER)$"
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
