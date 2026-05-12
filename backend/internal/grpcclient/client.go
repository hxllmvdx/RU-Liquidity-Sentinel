package grpcclient

import (
	"context"
	"fmt"
	"time"

	pb "github.com/ru-liquidity-sentinel/backend/gen/go/liquidity/v1"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type LiquidityClient struct {
	conn   *grpc.ClientConn
	client pb.LiquidityServiceClient
}

func NewLiquidityClient(addr string) (*LiquidityClient, error) {

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	conn, err := grpc.DialContext(
		ctx,
		addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		return nil, fmt.Errorf("connect to ML gRPC service: %w", err)
	}
	client := pb.NewLiquidityServiceClient(conn)
	return &LiquidityClient{
		conn:   conn,
		client: client,
	}, nil

}

func (c *LiquidityClient) Close() error {

	if c.conn != nil {
		return c.conn.Close()
	}
	return nil

}
