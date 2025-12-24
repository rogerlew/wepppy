# syntax=docker/dockerfile:1
FROM node:20-alpine

WORKDIR /app

COPY services/cap/package.json services/cap/package-lock.json ./
RUN npm ci --omit=dev

COPY services/cap/server.js ./

ENV NODE_ENV=production

EXPOSE 3000

CMD ["node", "server.js"]
