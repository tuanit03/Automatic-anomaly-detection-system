# Frontend Dockerfile optimized for docker-compose environment variables
FROM node:16-alpine as build

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy all source files
COPY . ./


ARG REACT_APP_BACKEND_URL=
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}

# Build the React app with the environment variables
RUN npm run build

# Production stage using Nginx
FROM nginx:alpine

# Copy the build files from the build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy the Nginx configuration
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

COPY <<EOF /docker-entrypoint.d/40-replace-env-vars.sh
#!/bin/sh
find /usr/share/nginx/html -type f -name "*.js" -exec sed -i -e "s|http://backend:8000|$REACT_APP_BACKEND_URL|g" {} \;
find /usr/share/nginx/html -type f -name "*.js" -exec sed -i -e "s|http://localhost:8000|$REACT_APP_BACKEND_URL|g" {} \;
echo "Using backend URL: \$REACT_APP_BACKEND_URL"
EOF

# Make the script executable
RUN chmod +x /docker-entrypoint.d/40-replace-env-vars.sh

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]