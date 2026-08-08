# Next.js standalone output keeps the runtime image to only what is served.

FROM node:22-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:22-slim AS runtime

RUN useradd --create-home --shell /bin/bash bharatos
WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER bharatos
EXPOSE 3000

CMD ["node", "server.js"]
