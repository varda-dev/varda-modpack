package serverinstaller

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

var Version = "dev"

var payloadFS fs.FS

func SetPayloadFS(fsys fs.FS) fs.FS {
	old := payloadFS
	payloadFS = fsys
	return old
}

func ExtractPayload(targetDir string) error {
	if payloadFS == nil {
		return fmt.Errorf("payload filesystem not initialized")
	}

	return fs.WalkDir(payloadFS, "payload", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		rel := strings.TrimPrefix(path, "payload")
		rel = strings.TrimPrefix(rel, "/")
		if rel == "" {
			return nil
		}

		switch rel {
		case "README-SERVER.txt":
			return writePayloadFile(targetDir, rel, path)
		case "mods-list.txt", "neoforge-url.txt":
			return writePayloadFile(vardaDir(targetDir), rel, path)
		}

		target := filepath.Join(targetDir, filepath.FromSlash(rel))
		if d.IsDir() {
			return os.MkdirAll(target, 0o755)
		}

		return writePayloadFile(targetDir, rel, path)
	})
}

func writePayloadFile(baseDir, rel, path string) error {
	data, err := fs.ReadFile(payloadFS, path)
	if err != nil {
		return err
	}

	target := filepath.Join(baseDir, filepath.FromSlash(rel))
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return err
	}

	if err := os.WriteFile(target, data, 0o644); err != nil {
		return fmt.Errorf("write embedded file %s: %w", target, err)
	}

	return nil
}

func WriteDiagnostics(targetDir string) error {
	diagDir := vardaDir(targetDir)
	if err := os.MkdirAll(diagDir, 0o755); err != nil {
		return err
	}

	if err := os.WriteFile(installerVersionPath(targetDir), []byte(Version+"\n"), 0o644); err != nil {
		return err
	}

	return cleanupRootMetadata(targetDir)
}

func cleanupRootMetadata(targetDir string) error {
	for _, name := range []string{"mods-list.txt", "neoforge-url.txt"} {
		if err := os.Remove(filepath.Join(targetDir, name)); err != nil && !os.IsNotExist(err) {
			return err
		}
	}
	return nil
}

func WriteJvmArgs(targetDir string) error {
	const content = "# JVM memory settings for Varda.\n" +
		"# Adjust these based on available server RAM.\n" +
		"-Xms4G\n" +
		"-Xmx6G\n"

	return os.WriteFile(filepath.Join(targetDir, "user_jvm_args.txt"), []byte(content), 0o644)
}

func readFirstDataLine(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}

	for _, rawLine := range strings.Split(string(data), "\n") {
		line := strings.TrimSpace(rawLine)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		return line, nil
	}

	return "", fmt.Errorf("%s does not contain a value", path)
}
