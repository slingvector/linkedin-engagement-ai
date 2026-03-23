# apps/web/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

ENV NEXT_PUBLIC_API_URL=/api/v1

# Install dependencies based on package.json
COPY package*.json ./
RUN npm install

# Copy source and build the Next.js application for production
COPY . .
RUN npm run build

# Production runner stage
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Copy necessary build artifacts from builder stage (standalone deployment)
COPY --from=builder /app/package.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

# Start the published application
CMD ["npm", "start"]
