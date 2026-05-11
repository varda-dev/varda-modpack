package serverinstaller

import (
	"fmt"
	"net/url"
	"path"
	"path/filepath"
	"strings"
)

func targetPath(targetDir string, parts ...string) string {
	items := append([]string{targetDir}, parts...)
	return filepath.Join(items...)
}

func desiredNeoForgeURLPath(targetDir string) string {
	return vardaFile(targetDir, "neoforge-url.txt")
}

func desiredModsListPath(targetDir string) string {
	return vardaFile(targetDir, "mods-list.txt")
}

func installerVersionPath(targetDir string) string {
	return vardaFile(targetDir, "installer-version.txt")
}

func vardaDir(targetDir string) string {
	return targetPath(targetDir, ".varda")
}

func vardaFile(targetDir, name string) string {
	return targetPath(vardaDir(targetDir), name)
}

func desiredNeoForgeRoot(targetDir string) string {
	return targetPath(targetDir, "libraries", "net", "neoforged", "neoforge")
}

func installedNeoForgeVersionDir(targetDir, version string) string {
	return filepath.Join(desiredNeoForgeRoot(targetDir), version)
}

func modsDir(targetDir string) string {
	return targetPath(targetDir, "mods")
}

func isSafeModFilename(name string) bool {
	if name == "" || filepath.IsAbs(name) {
		return false
	}
	if strings.Contains(name, "/") || strings.Contains(name, "\\") {
		return false
	}
	if strings.Contains(name, "..") {
		return false
	}
	return strings.HasSuffix(strings.ToLower(name), ".jar")
}

func inferFilenameFromURL(raw string) (string, error) {
	parsed, err := url.Parse(raw)
	if err != nil {
		return "", err
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" && parsed.Scheme != "file" {
		return "", fmt.Errorf("unsupported URL scheme: %s", parsed.Scheme)
	}
	name := path.Base(parsed.Path)
	if name == "." || name == "/" || name == "" {
		return "", fmt.Errorf("URL does not contain a file name: %s", raw)
	}
	return url.PathUnescape(name)
}

func inferNeoForgeVersionFromURL(raw string) (string, error) {
	parsed, err := url.Parse(raw)
	if err != nil {
		return "", err
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return "", fmt.Errorf("unsupported NeoForge URL scheme: %s", parsed.Scheme)
	}

	installerName := path.Base(parsed.Path)
	versionDir := path.Base(path.Dir(parsed.Path))
	expected := fmt.Sprintf("neoforge-%s-installer.jar", versionDir)
	if installerName != expected {
		return "", fmt.Errorf("could not infer NeoForge version from URL: %s", raw)
	}

	if !strings.Contains(parsed.Path, "/releases/net/neoforged/neoforge/") {
		return "", fmt.Errorf("could not infer NeoForge version from URL: %s", raw)
	}

	return url.PathUnescape(versionDir)
}
