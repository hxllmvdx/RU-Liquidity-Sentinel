package postgres

import "github.com/jmoiron/sqlx"

type DB struct {
	conn *sqlx.DB
}

func NewDB(conn *sqlx.DB) *DB {
	return &DB{conn: conn}
}

func (db *DB) Close() error {
	if db.conn == nil {
		return nil
	}
	return db.conn.Close()
}

func (db *DB) Conn() *sqlx.DB {
	return db.conn
}
