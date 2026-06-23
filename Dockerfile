FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY backend/package*.json ./

# Install all dependencies (including dev for build)
RUN npm install --legacy-peer-deps

# Copy source code
COPY backend/src ./src
COPY backend/tsconfig.json ./
COPY backend/nodemon.json ./

# Build TypeScript
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY backend/package*.json ./

# Install only production dependencies
RUN npm install --production --legacy-peer-deps

# Copy built app from builder
COPY --from=builder /app/dist ./dist

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3001/health', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})"

# Expose port
EXPOSE 3001

# Start the app
CMD ["node", "dist/index.js"]
