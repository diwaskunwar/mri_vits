# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Set build argument for API URL
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM node:20-alpine

# Install serve
RUN npm install -g serve

# Copy built files from builder
COPY --from=builder /app/dist /app/dist

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 3000

# Start serve
CMD ["serve", "-s", "dist", "-l", "3000"]
