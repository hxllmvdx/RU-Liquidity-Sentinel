package service

import "errors"

var ErrRecalculationInProgress = errors.New("recalculation already in progress")
