FROM node:20-alpine

WORKDIR /app

# Copy package configurations
COPY package.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy app files
COPY . .

EXPOSE 3000

# Run in development mode by default for Buildathon hot-reloading
CMD ["npm", "run", "dev"]
