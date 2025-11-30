############## STAGE 1: Build Angular app ##############

FROM node:20 AS build-stage

# Set working directory
WORKDIR /app

# Copy package.json + lock file first (better caching)
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy the rest of the app source
COPY . .

# Build Angular app (adjust if your project name is different)
#RUN npm run build --configuration production
RUN npx ng build agentUI --configuration production



############## STAGE 2: Serve Angular app with Nginx ##############

FROM nginx:alpine AS production-stage

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy your NGINX config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build output to nginx html folder
COPY --from=build-stage /app/dist/agent-ui/browser/ /usr/share/nginx/html/
# Expose port
EXPOSE 80

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]