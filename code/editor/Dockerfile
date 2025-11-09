# Quanto mango Image Editor - Docker Container
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S qwen -u 1001

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --only=production && \
    npm cache clean --force

# Copy application files
COPY . .

# Create public directory and set permissions
RUN mkdir -p public && \
    chown -R qwen:nodejs /app

# Switch to non-root user  
USER qwen

# Expose port
EXPOSE 3002

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3002/health || exit 1

# Start application
CMD ["npm", "start"]