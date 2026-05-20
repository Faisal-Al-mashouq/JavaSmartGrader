FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --ignore-scripts

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
