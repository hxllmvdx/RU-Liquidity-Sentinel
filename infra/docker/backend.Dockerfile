FROM golang:1.22-alpine
WORKDIR /app
COPY backend ./backend
WORKDIR /app/backend
CMD ["go", "run", "./cmd/api-gateway"]
