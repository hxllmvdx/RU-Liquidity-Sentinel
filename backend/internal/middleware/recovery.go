package middleware

import "net/http"

func Recovery(next http.Handler) http.Handler {
	return next
}
