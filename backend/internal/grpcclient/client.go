package grpcclient

type Client struct {
	Address string
}

func New(address string) *Client {
	return &Client{Address: address}
}
