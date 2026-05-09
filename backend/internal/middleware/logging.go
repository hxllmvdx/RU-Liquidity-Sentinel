package middleware

import (
	"log"
	"time"

	"github.com/gin-gonic/gin"
)

func Logging() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		method := c.Request.Method
		path := c.Request.URL.Path
		clientIP := c.ClientIP()
		requestID := GetRequestID(c)

		c.Next()

		status := c.Writer.Status()
		latency := time.Since(start)

		if len(c.Errors) > 0 {
			log.Printf(
				"request_id=%s method=%s path=%s status=%d ip=%s duration=%s errors=%s",
				requestID,
				method,
				path,
				status,
				clientIP,
				latency,
				c.Errors.String(),
			)
			return
		}

		log.Printf(
			"request_id=%s method=%s path=%s status=%d ip=%s duration=%s",
			requestID,
			method,
			path,
			status,
			clientIP,
			latency,
		)
	}
}
