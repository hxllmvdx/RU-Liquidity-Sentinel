package handlers

import (
	"fmt"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
)

type errorEnvelope struct {
	Error errorBody `json:"error"`
}

type errorBody struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

func parseBoolQuery(c *gin.Context, name string, defaultValue bool) bool {
	value := c.Query(name)
	if value == "" {
		return defaultValue
	}
	parsed, err := strconv.ParseBool(value)
	if err != nil {
		return defaultValue
	}
	return parsed
}

func parseIntQuery(c *gin.Context, name string, defaultValue int) (int, error) {
	value := c.Query(name)
	if value == "" {
		return defaultValue, nil
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return 0, fmt.Errorf("invalid %s", name)
	}
	return parsed, nil
}

func requireQuery(c *gin.Context, name string) (string, bool) {
	value := c.Query(name)
	if value == "" {
		writeError(c, 400, "BAD_REQUEST", fmt.Sprintf("%s is required", name))
		return "", false
	}
	return value, true
}

func writeError(c *gin.Context, status int, code string, message string) {
	c.AbortWithStatusJSON(status, errorEnvelope{
		Error: errorBody{
			Code:    code,
			Message: message,
		},
	})
}

func validateDateString(s string) bool {
	if s == "" {
		return false
	}
	_, err := time.Parse("2006-01-02", s)
	return err == nil
}

func validateDateRange(from, to string) bool {
	if !validateDateString(from) || !validateDateString(to) {
		return false
	}
	fromDate, _ := time.Parse("2006-01-02", from)
	toDate, _ := time.Parse("2006-01-02", to)
	return !fromDate.After(toDate)
}
