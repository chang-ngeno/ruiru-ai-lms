FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_DEV_AUTH=false
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID VITE_DEV_AUTH=$VITE_DEV_AUTH
RUN npm run build

FROM nginx:1.27-alpine
ENV PORT=80 \
    BACKEND_URL=http://backend:5000 \
    BACKEND_HOST=backend:5000 \
    RESOLVER="1.1.1.1 8.8.8.8" \
    NGINX_ENVSUBST_FILTER="^(PORT|BACKEND_URL|BACKEND_HOST|RESOLVER)$"
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
