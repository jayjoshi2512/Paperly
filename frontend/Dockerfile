# Build stage
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
# Copy the built assets
COPY --from=build /app/dist /usr/share/nginx/html
# Nginx default conf will serve these files on port 80
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
