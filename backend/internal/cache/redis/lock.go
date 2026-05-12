package redis

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"log"

	goredis "github.com/redis/go-redis/v9"
)

var ErrLockAlreadyHeld = errors.New("lock already held")

var releaseLockScript = goredis.NewScript(`
if redis.call("GET", KEYS[1]) == ARGV[1] then
	return redis.call("DEL", KEYS[1])
end
return 0
`)

func (c *Cache) AcquireRecalculationLock(ctx context.Context) (string, error) {
	if !c.Enabled() {
		return "", nil
	}

	token, err := randomToken()
	if err != nil {
		return "", err
	}

	ok, err := c.client.SetNX(ctx, RecalculationLockKey(), token, c.cfg.LockTTL).Result()
	if err != nil {
		log.Printf("redis lock acquire error key=%s err=%v", RecalculationLockKey(), err)
		return "", err
	}
	if !ok {
		return "", ErrLockAlreadyHeld
	}

	log.Printf("redis lock acquired key=%s", RecalculationLockKey())
	return token, nil
}

func (c *Cache) ReleaseRecalculationLock(ctx context.Context, token string) error {
	if !c.Enabled() || token == "" {
		return nil
	}

	if _, err := releaseLockScript.Run(ctx, c.client, []string{RecalculationLockKey()}, token).Result(); err != nil {
		log.Printf("redis lock release error key=%s err=%v", RecalculationLockKey(), err)
		return err
	}

	log.Printf("redis lock released key=%s", RecalculationLockKey())
	return nil
}

func randomToken() (string, error) {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return "", fmt.Errorf("generate lock token: %w", err)
	}
	return hex.EncodeToString(buf), nil
}
