package main

import (
	"embed"

	"github.com/rannday/varda-modpack/internal/serverinstaller"
)

//go:embed payload/*
var payloadFS embed.FS

func init() {
	serverinstaller.SetPayloadFS(payloadFS)
}
