package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func CORS(allowedOrigin string) gin.HandlerFunc {
	allowedMethods := map[string]struct{}{
		http.MethodGet:     {},
		http.MethodPost:    {},
		http.MethodOptions: {},
	}

	allowedMethodsHeader := "GET, POST, OPTIONS"
	allowedHeadersHeader := "Content-Type, Authorization"
	exposedHeadersHeader := RequestIDHeader

	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")

		if origin == allowedOrigin {
			c.Header("Access-Control-Allow-Origin", allowedOrigin)
			c.Header("Vary", "Origin")
			c.Header("Access-Control-Expose-Headers", exposedHeadersHeader)
		}

		c.Header("Access-Control-Allow-Methods", allowedMethodsHeader)
		c.Header("Access-Control-Allow-Headers", allowedHeadersHeader)

		if c.Request.Method == http.MethodOptions {
			if origin != "" && origin != allowedOrigin {
				c.AbortWithStatus(http.StatusForbidden)
				return
			}

			requestMethod := c.GetHeader("Access-Control-Request-Method")
			if requestMethod != "" {
				if _, ok := allowedMethods[requestMethod]; !ok {
					c.AbortWithStatus(http.StatusMethodNotAllowed)
					return
				}
			}

			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
