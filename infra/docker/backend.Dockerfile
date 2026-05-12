FROM golang:1.25-alpine AS builder

WORKDIR /app

RUN apk add --no-cache bash protobuf

COPY backend/go.mod backend/go.sum ./backend/
WORKDIR /app/backend
RUN go mod download

RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.36.11 \
    && go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.6.1

WORKDIR /app
COPY scripts ./scripts
COPY proto ./proto
COPY backend ./backend

ENV PATH="/go/bin:${PATH}"
RUN bash ./scripts/generate_proto.sh --go-only

WORKDIR /app/backend
RUN go build -o /out/api-gateway ./cmd/api-gateway

FROM alpine:3.22

WORKDIR /app

COPY --from=builder /out/api-gateway /app/api-gateway

CMD ["/app/api-gateway"]
