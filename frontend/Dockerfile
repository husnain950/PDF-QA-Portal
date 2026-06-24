FROM node:20-alpine

WORKDIR /app

# Copy package lock and package json for cache leverage
COPY package*.json ./

RUN npm install

# Copy frontend source code
COPY . .

# Expose Vite development server port
EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
