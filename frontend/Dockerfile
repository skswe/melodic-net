FROM node:21-alpine AS BUILD_IMAGE
WORKDIR /app
COPY package.json .
RUN npm install
COPY . . 
RUN npm run build

# Stage 2: Serve the app using NGINX
FROM nginx:alpine AS PRODUCTION_IMAGE

# Remove default NGINX configuration
RUN rm -rf /usr/share/nginx/html/*

# Copy the built app from the previous stage to NGINX's html directory
COPY --from=BUILD_IMAGE /app/dist /usr/share/nginx/html

# Copy custom NGINX configuration to set the listening port
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Start NGINX to serve the app
CMD ["nginx", "-g", "daemon off;"]