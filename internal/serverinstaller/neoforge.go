package serverinstaller

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
)

func ReadDesiredNeoForgeState(targetDir string) (string, string, error) {
	url, err := readFirstDataLine(desiredNeoForgeURLPath(targetDir))
	if err != nil {
		return "", "", err
	}

	version, err := inferNeoForgeVersionFromURL(url)
	if err != nil {
		return "", "", err
	}

	return url, version, nil
}

func InstallOrUpdateNeoForge(targetDir string, force bool) (string, error) {
	url, version, err := ReadDesiredNeoForgeState(targetDir)
	if err != nil {
		return "", err
	}

	desiredDir := installedNeoForgeVersionDir(targetDir, version)
	installed, err := installedNeoForgeVersions(targetDir)
	if err != nil {
		return "", err
	}

	if dirExists(desiredDir) && !force {
		fmt.Printf("NeoForge %s already installed; skipping install.\n", version)
		if err := cleanupOldNeoForgeVersions(targetDir, version); err != nil {
			return "", err
		}
		return version, nil
	}

	switch {
	case len(installed) == 0:
		fmt.Printf("Installing NeoForge %s...\n", version)
	case force:
		fmt.Printf("Reinstalling NeoForge %s due to --force...\n", version)
	default:
		fmt.Printf("Updating NeoForge to %s...\n", version)
	}

	tempDir, err := os.MkdirTemp("", "varda-neoforge-")
	if err != nil {
		return "", err
	}
	defer os.RemoveAll(tempDir)

	installerName, err := inferFilenameFromURL(url)
	if err != nil {
		return "", err
	}
	installerPath := filepath.Join(tempDir, installerName)
	if err := downloadToFile(url, installerPath, force, "NeoForge installer"); err != nil {
		return "", err
	}

	cmd := exec.Command("java", "-jar", installerPath, "--installServer")
	cmd.Dir = targetDir
	output, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("NeoForge installer failed: %w\n%s", err, string(output))
	}

	if !dirExists(desiredDir) {
		return "", fmt.Errorf("NeoForge install completed but expected version directory is missing: %s", version)
	}

	if err := cleanupOldNeoForgeVersions(targetDir, version); err != nil {
		return "", err
	}

	return version, nil
}

func cleanupNeoForgeInstallerArtifacts(targetDir string) error {
	patterns := []string{
		filepath.Join(targetDir, "neoforge-*-installer.jar"),
		filepath.Join(targetDir, "neoforge-*-installer.jar.log"),
		filepath.Join(targetDir, "installer.log"),
	}

	for _, pattern := range patterns {
		matches, err := filepath.Glob(pattern)
		if err != nil {
			return err
		}

		for _, match := range matches {
			if err := os.Remove(match); err != nil && !os.IsNotExist(err) {
				return err
			}
		}
	}

	return nil
}

func installedNeoForgeVersions(targetDir string) ([]string, error) {
	root := desiredNeoForgeRoot(targetDir)
	entries, err := os.ReadDir(root)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}

	var versions []string
	for _, entry := range entries {
		if entry.IsDir() {
			versions = append(versions, entry.Name())
		}
	}
	sort.Strings(versions)
	return versions, nil
}

func cleanupOldNeoForgeVersions(targetDir, desired string) error {
	root := desiredNeoForgeRoot(targetDir)
	entries, err := os.ReadDir(root)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	for _, entry := range entries {
		if !entry.IsDir() || entry.Name() == desired {
			continue
		}
		oldPath := filepath.Join(root, entry.Name())
		fmt.Printf("Removing old NeoForge version: %s\n", entry.Name())
		if err := os.RemoveAll(oldPath); err != nil {
			return err
		}
	}

	return nil
}

func dirExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}
