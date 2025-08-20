# Use Node.js 18 Alpine image
FROM node:18-alpine

# Declare a build-time variable
ARG REACT_APP_API_BASE_URL

# make it a runtime ENV too
ENV REACT_APP_API_BASE_URL=$REACT_APP_API_BASE_URL

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache curl


# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy project files
COPY . .

# Build the app for production
RUN npm run build

# Install serve to run the application
RUN npm install -g serve

# Expose port
EXPOSE 3000

# Start the application
CMD ["serve", "-s", "build", "-l", "3000"]
