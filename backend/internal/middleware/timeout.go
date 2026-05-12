package middleware

import (
	"context"
	"errors"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

func Timeout(timeout time.Duration) gin.HandlerFunc {
	return TimeoutWithOverrides(timeout, nil)
}

func TimeoutWithOverrides(defaultTimeout time.Duration, overrides map[string]time.Duration) gin.HandlerFunc {
	return func(c *gin.Context) {
		timeout := defaultTimeout
		if overrides != nil {
			if override, ok := overrides[c.FullPath()]; ok && override > 0 {
				timeout = override
			}
		}

		ctx, cancel := context.WithTimeout(c.Request.Context(), timeout)
		defer cancel()

		c.Request = c.Request.WithContext(ctx)
		c.Next()

		if errors.Is(ctx.Err(), context.DeadlineExceeded) && !c.Writer.Written() {
			c.AbortWithStatusJSON(http.StatusGatewayTimeout, gin.H{
				"error":      "request timed out",
				"request_id": GetRequestID(c),
			})
		}
	}
}
