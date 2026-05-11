package serverinstaller

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
)

type ModSpec struct {
	FileName string
	URL      string
}

func ReadDesiredMods(targetDir string) ([]ModSpec, error) {
	file, err := os.Open(desiredModsListPath(targetDir))
	if err != nil {
		return nil, err
	}
	defer file.Close()

	return ParseModsList(file)
}

func ParseModsList(file *os.File) ([]ModSpec, error) {
	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

	seen := make(map[string]struct{})
	var mods []ModSpec

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		fileName, rawURL, err := parseModListLine(line)
		if err != nil {
			return nil, err
		}

		key := strings.ToLower(fileName)
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}
		mods = append(mods, ModSpec{FileName: fileName, URL: rawURL})
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	sort.Slice(mods, func(i, j int) bool {
		if strings.ToLower(mods[i].FileName) == strings.ToLower(mods[j].FileName) {
			return mods[i].URL < mods[j].URL
		}
		return strings.ToLower(mods[i].FileName) < strings.ToLower(mods[j].FileName)
	})

	return mods, nil
}

func parseModListLine(line string) (string, string, error) {
	var fileName, rawURL string

	if strings.Contains(line, "\t") {
		parts := strings.SplitN(line, "\t", 2)
		if len(parts) != 2 {
			return "", "", fmt.Errorf("invalid mod list line: %s", line)
		}
		fileName = strings.TrimSpace(parts[0])
		rawURL = strings.TrimSpace(parts[1])
	} else {
		rawURL = strings.TrimSpace(line)
		var err error
		fileName, err = inferFilenameFromURL(rawURL)
		if err != nil {
			return "", "", err
		}
	}

	if !strings.HasPrefix(rawURL, "http://") && !strings.HasPrefix(rawURL, "https://") && !strings.HasPrefix(rawURL, "file://") {
		return "", "", fmt.Errorf("invalid mod URL in mods-list.txt: %s", line)
	}

	if !isSafeModFilename(fileName) {
		return "", "", fmt.Errorf("unsafe or non-jar mod filename in mods-list.txt: %s", fileName)
	}

	return fileName, rawURL, nil
}

func ReconcileMods(targetDir string, force bool, workerCount int) error {
	if workerCount < 1 || workerCount > 16 {
		return fmt.Errorf("download worker count must be between 1 and 16")
	}

	modsPath := modsDir(targetDir)
	if err := os.MkdirAll(modsPath, 0o755); err != nil {
		return err
	}

	mods, err := ReadDesiredMods(targetDir)
	if err != nil {
		return err
	}
	if len(mods) == 0 {
		return fmt.Errorf("mods-list.txt did not contain any server mod jars")
	}

	desired := make(map[string]ModSpec, len(mods))
	var downloads []ModSpec
	for _, mod := range mods {
		desired[strings.ToLower(mod.FileName)] = mod
		target := filepath.Join(modsPath, mod.FileName)
		if !force {
			info, err := os.Stat(target)
			if err == nil {
				if info.IsDir() {
					return fmt.Errorf("target mod path is a directory: %s", target)
				}
				if info.Size() > 0 {
					fmt.Printf("Keeping current mod: %s\n", mod.FileName)
					continue
				}
			}
			if err != nil && !os.IsNotExist(err) {
				return err
			}
		}
		downloads = append(downloads, mod)
	}

	if err := downloadMods(targetDir, downloads, force, workerCount); err != nil {
		return err
	}

	entries, err := os.ReadDir(modsPath)
	if err != nil {
		return err
	}

	known := make(map[string]struct{}, len(desired))
	for key := range desired {
		known[key] = struct{}{}
	}

	for _, entry := range entries {
		name := entry.Name()
		path := filepath.Join(modsPath, name)
		if _, ok := known[strings.ToLower(name)]; ok {
			continue
		}
		if entry.IsDir() {
			fmt.Printf("Removing unmanaged directory from mods/: %s\n", name)
			if err := os.RemoveAll(path); err != nil {
				return err
			}
			continue
		}

		fmt.Printf("Removing unmanaged file from mods/: %s\n", name)
		if err := os.Remove(path); err != nil {
			return err
		}
	}

	return nil
}

func downloadMods(targetDir string, mods []ModSpec, force bool, workerCount int) error {
	if len(mods) == 0 {
		return nil
	}

	modsPath := modsDir(targetDir)
	jobs := make(chan ModSpec)
	var wg sync.WaitGroup
	var mu sync.Mutex
	var errs []error

	worker := func() {
		defer wg.Done()
		for mod := range jobs {
			target := filepath.Join(modsPath, mod.FileName)
			if err := downloadToFile(mod.URL, target, force, mod.FileName); err != nil {
				mu.Lock()
				errs = append(errs, fmt.Errorf("%s: %w", mod.FileName, err))
				mu.Unlock()
			}
		}
	}

	wg.Add(workerCount)
	for i := 0; i < workerCount; i++ {
		go worker()
	}

	for _, mod := range mods {
		jobs <- mod
	}
	close(jobs)
	wg.Wait()

	if len(errs) > 0 {
		return errors.Join(errs...)
	}

	return nil
}
