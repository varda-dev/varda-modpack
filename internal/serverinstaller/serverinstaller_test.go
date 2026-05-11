package serverinstaller

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestParseJavaVersion(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name    string
		output  string
		want    int
		wantErr bool
	}{
		{
			name:   "modern",
			output: `openjdk version "21.0.4" 2024-07-16`,
			want:   21,
		},
		{
			name:   "legacy",
			output: `java version "1.8.0_402"`,
			want:   8,
		},
		{
			name:    "invalid",
			output:  `java version`,
			wantErr: true,
		},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			got, err := ParseJavaVersion(tc.output)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error")
				}
				return
			}
			if err != nil {
				t.Fatalf("ParseJavaVersion() error = %v", err)
			}
			if got != tc.want {
				t.Fatalf("ParseJavaVersion() = %d, want %d", got, tc.want)
			}
		})
	}
}

func TestInferNeoForgeVersionFromURL(t *testing.T) {
	t.Parallel()

	got, err := inferNeoForgeVersionFromURL("https://maven.neoforged.net/releases/net/neoforged/neoforge/21.1.83/neoforge-21.1.83-installer.jar")
	if err != nil {
		t.Fatalf("inferNeoForgeVersionFromURL() error = %v", err)
	}
	if got != "21.1.83" {
		t.Fatalf("inferNeoForgeVersionFromURL() = %q, want %q", got, "21.1.83")
	}
}

func TestParseModsList(t *testing.T) {
	t.Parallel()

	file, err := os.CreateTemp(t.TempDir(), "mods-list-*.txt")
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()

	sourceURL := "https://example.invalid/mods/alpha.jar"
	if _, err := file.WriteString(strings.Join([]string{
		"# comment",
		sourceURL,
		"beta.jar\thttps://example.invalid/mods/beta.jar",
		"",
	}, "\n")); err != nil {
		t.Fatal(err)
	}
	if _, err := file.Seek(0, 0); err != nil {
		t.Fatal(err)
	}

	mods, err := ParseModsList(file)
	if err != nil {
		t.Fatalf("ParseModsList() error = %v", err)
	}
	if len(mods) != 2 {
		t.Fatalf("ParseModsList() len = %d, want 2", len(mods))
	}
	if mods[0].FileName != "alpha.jar" || mods[1].FileName != "beta.jar" {
		t.Fatalf("ParseModsList() file names = %#v", mods)
	}
}

func TestParseModsListRejectsUnsafeOrNonJar(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name  string
		line  string
		match string
	}{
		{
			name:  "zip",
			line:  "https://example.invalid/mods/shader.zip",
			match: "non-jar",
		},
		{
			name:  "unsafe",
			line:  "../evil.jar\thttps://example.invalid/mods/evil.jar",
			match: "unsafe",
		},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			file, err := os.CreateTemp(t.TempDir(), "mods-list-*.txt")
			if err != nil {
				t.Fatal(err)
			}
			defer file.Close()

			if _, err := file.WriteString(tc.line + "\n"); err != nil {
				t.Fatal(err)
			}
			if _, err := file.Seek(0, 0); err != nil {
				t.Fatal(err)
			}

			_, err = ParseModsList(file)
			if err == nil || !strings.Contains(strings.ToLower(err.Error()), tc.match) {
				t.Fatalf("ParseModsList() error = %v, want match %q", err, tc.match)
			}
		})
	}
}

func TestReconcileModsRemovesUnmanagedFiles(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	modsDirPath := filepath.Join(root, "mods")
	if err := os.MkdirAll(modsDirPath, 0o755); err != nil {
		t.Fatal(err)
	}

	source := filepath.Join(root, "source.jar")
	if err := os.WriteFile(source, []byte("payload"), 0o644); err != nil {
		t.Fatal(err)
	}

	modList := strings.Join([]string{
		"source.jar\t" + fileURL(source),
	}, "\n") + "\n"
	if err := os.MkdirAll(filepath.Join(root, ".varda"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".varda", "mods-list.txt"), []byte(modList), 0o644); err != nil {
		t.Fatal(err)
	}

	if err := os.WriteFile(filepath.Join(modsDirPath, "extra.jar"), []byte("extra"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(modsDirPath, "shader.zip"), []byte("zip"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(modsDirPath, "notes.txt"), []byte("keep"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(modsDirPath, ".hidden"), []byte("hidden"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(modsDirPath, "nested"), 0o755); err != nil {
		t.Fatal(err)
	}

	if err := ReconcileMods(root, false, 6); err != nil {
		t.Fatalf("ReconcileMods() error = %v", err)
	}

	if _, err := os.Stat(filepath.Join(modsDirPath, "source.jar")); err != nil {
		t.Fatalf("source.jar missing after reconcile: %v", err)
	}
	if _, err := os.Stat(filepath.Join(modsDirPath, "extra.jar")); !os.IsNotExist(err) {
		t.Fatalf("extra.jar still present after reconcile: %v", err)
	}
	for _, name := range []string{"shader.zip", "notes.txt", ".hidden"} {
		if _, err := os.Stat(filepath.Join(modsDirPath, name)); !os.IsNotExist(err) {
			t.Fatalf("%s still present after reconcile: %v", name, err)
		}
	}
	if _, err := os.Stat(filepath.Join(modsDirPath, "nested")); !os.IsNotExist(err) {
		t.Fatalf("nested directory still present after reconcile: %v", err)
	}
	if _, err := os.Stat(filepath.Join(modsDirPath, ".varda-desired-mods.txt")); !os.IsNotExist(err) {
		t.Fatalf(".varda-desired-mods.txt should not be created: %v", err)
	}
}

func TestParseModsListRejectsZipDesiredEntry(t *testing.T) {
	t.Parallel()

	file, err := os.CreateTemp(t.TempDir(), "mods-list-*.txt")
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()

	if _, err := file.WriteString("shader.zip\thttps://example.invalid/mods/shader.zip\n"); err != nil {
		t.Fatal(err)
	}
	if _, err := file.Seek(0, 0); err != nil {
		t.Fatal(err)
	}

	_, err = ParseModsList(file)
	if err == nil || !strings.Contains(strings.ToLower(err.Error()), "non-jar") {
		t.Fatalf("ParseModsList() error = %v, want non-jar rejection", err)
	}
}

func TestExtractPayloadRoutesMetadataIntoVarda(t *testing.T) {
	payloadRoot := t.TempDir()
	if err := os.MkdirAll(filepath.Join(payloadRoot, "payload"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(payloadRoot, "payload", "README-SERVER.txt"), []byte("readme"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(payloadRoot, "payload", "mods-list.txt"), []byte("mod.jar\thttps://example.invalid/mod.jar"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(payloadRoot, "payload", "neoforge-url.txt"), []byte("https://example.invalid/neoforge.jar"), 0o644); err != nil {
		t.Fatal(err)
	}

	old := SetPayloadFS(os.DirFS(payloadRoot))
	defer SetPayloadFS(old)

	root := t.TempDir()
	if err := ExtractPayload(root); err != nil {
		t.Fatalf("ExtractPayload() error = %v", err)
	}

	if _, err := os.Stat(filepath.Join(root, "mods-list.txt")); !os.IsNotExist(err) {
		t.Fatalf("root mods-list.txt still present: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, "neoforge-url.txt")); !os.IsNotExist(err) {
		t.Fatalf("root neoforge-url.txt still present: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, ".varda", "mods-list.txt")); err != nil {
		t.Fatalf(".varda/mods-list.txt missing: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, ".varda", "neoforge-url.txt")); err != nil {
		t.Fatalf(".varda/neoforge-url.txt missing: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, "README-SERVER.txt")); err != nil {
		t.Fatalf("README-SERVER.txt missing: %v", err)
	}
}

func TestWriteDiagnosticsRemovesRootMetadata(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "mods-list.txt"), []byte("stale"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "neoforge-url.txt"), []byte("stale"), 0o644); err != nil {
		t.Fatal(err)
	}

	oldVersion := Version
	Version = "test-123"
	defer func() { Version = oldVersion }()

	if err := WriteDiagnostics(root); err != nil {
		t.Fatalf("WriteDiagnostics() error = %v", err)
	}

	if _, err := os.Stat(filepath.Join(root, "mods-list.txt")); !os.IsNotExist(err) {
		t.Fatalf("root mods-list.txt still present: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, "neoforge-url.txt")); !os.IsNotExist(err) {
		t.Fatalf("root neoforge-url.txt still present: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, ".varda", "installer-version.txt")); err != nil {
		t.Fatalf("installer-version.txt missing: %v", err)
	}
}

func TestPatchLaunchersIncludesNogui(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	version := "21.1.83"
	if err := PatchLaunchers(root, version); err != nil {
		t.Fatalf("PatchLaunchers() error = %v", err)
	}

	runSh, err := os.ReadFile(filepath.Join(root, "run.sh"))
	if err != nil {
		t.Fatal(err)
	}
	runBat, err := os.ReadFile(filepath.Join(root, "run.bat"))
	if err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(string(runSh), "nogui") || !strings.Contains(string(runBat), "nogui") {
		t.Fatalf("launchers missing nogui:\nrun.sh=%s\nrun.bat=%s", runSh, runBat)
	}
	if _, err := os.Stat(filepath.Join(root, "run.ps1")); !os.IsNotExist(err) {
		t.Fatalf("run.ps1 should not be generated: %v", err)
	}

	if runtime.GOOS != "windows" {
		info, err := os.Stat(filepath.Join(root, "run.sh"))
		if err != nil {
			t.Fatal(err)
		}
		if info.Mode()&0o111 == 0 {
			t.Fatalf("run.sh not executable")
		}
	}
}

func TestPatchRunBatAcceptsRealWorldForwardSlashes(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	version := "21.1.228"
	content := strings.Join([]string{
		"@echo off",
		"REM Forge requires a configured set of both JVM and program arguments.",
		"REM Add custom JVM arguments to the user_jvm_args.txt",
		"REM Add custom program arguments {such as nogui} to this file in the next line before the %* or",
		"REM  pass them to this script directly",
		"java @user_jvm_args.txt @libraries/net/neoforged/neoforge/21.1.228/win_args.txt %*",
		"pause",
		"",
	}, "\r\n")
	if err := os.WriteFile(filepath.Join(root, "run.bat"), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}

	if err := patchRunBat(root, version); err != nil {
		t.Fatalf("patchRunBat() error = %v", err)
	}

	after, err := os.ReadFile(filepath.Join(root, "run.bat"))
	if err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(string(after), "pause") {
		t.Fatalf("patched run.bat lost pause:\n%s", after)
	}
	if countLaunchNogui(strings.Split(string(after), "\r\n")) != 1 {
		t.Fatalf("expected exactly one nogui launch line:\n%s", after)
	}
	if !strings.Contains(string(after), "@libraries/net/neoforged/neoforge/21.1.228/win_args.txt nogui %*") {
		t.Fatalf("patched run.bat missing forward-slash launch line:\n%s", after)
	}

	if err := patchRunBat(root, version); err != nil {
		t.Fatalf("second patchRunBat() error = %v", err)
	}
	again, err := os.ReadFile(filepath.Join(root, "run.bat"))
	if err != nil {
		t.Fatal(err)
	}
	if countLaunchNogui(strings.Split(string(again), "\r\n")) != 1 {
		t.Fatalf("idempotency failed, nogui duplicated:\n%s", again)
	}
}

func TestPatchRunBatAcceptsBackslashes(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	version := "21.1.228"
	content := "@echo off\r\njava @user_jvm_args.txt @libraries\\net\\neoforged\\neoforge\\21.1.228\\win_args.txt %*\r\npause\r\n"
	if err := os.WriteFile(filepath.Join(root, "run.bat"), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}

	if err := patchRunBat(root, version); err != nil {
		t.Fatalf("patchRunBat() error = %v", err)
	}

	after, err := os.ReadFile(filepath.Join(root, "run.bat"))
	if err != nil {
		t.Fatal(err)
	}
	if countLaunchNogui(strings.Split(string(after), "\r\n")) != 1 {
		t.Fatalf("expected exactly one nogui launch line:\n%s", after)
	}
}

func TestCleanupNeoForgeInstallerArtifacts(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	files := []string{
		"neoforge-21.1.228-installer.jar",
		"neoforge-21.1.228-installer.jar.log",
		"installer.log",
	}
	for _, name := range files {
		if err := os.WriteFile(filepath.Join(root, name), []byte("x"), 0o644); err != nil {
			t.Fatal(err)
		}
	}

	if err := cleanupNeoForgeInstallerArtifacts(root); err != nil {
		t.Fatalf("cleanupNeoForgeInstallerArtifacts() error = %v", err)
	}

	for _, name := range files {
		if _, err := os.Stat(filepath.Join(root, name)); !os.IsNotExist(err) {
			t.Fatalf("%s still present after cleanup: %v", name, err)
		}
	}
}

func TestReplaceFileRestoresExistingTarget(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "artifact.jar")
	temp := filepath.Join(root, "artifact.jar.tmp")

	if err := os.WriteFile(target, []byte("old"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(temp, []byte("new"), 0o644); err != nil {
		t.Fatal(err)
	}

	if err := replaceFile(temp, target); err != nil {
		t.Fatalf("replaceFile() error = %v", err)
	}

	data, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != "new" {
		t.Fatalf("replaceFile() wrote %q, want %q", data, "new")
	}
	if _, err := os.Stat(target + ".bak"); !os.IsNotExist(err) {
		t.Fatalf("backup file still present: %v", err)
	}
}

func TestReplaceFileCreatesMissingTarget(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "artifact.jar")
	temp := filepath.Join(root, "artifact.jar.tmp")

	if err := os.WriteFile(temp, []byte("new"), 0o644); err != nil {
		t.Fatal(err)
	}

	if err := replaceFile(temp, target); err != nil {
		t.Fatalf("replaceFile() error = %v", err)
	}

	data, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != "new" {
		t.Fatalf("replaceFile() wrote %q, want %q", data, "new")
	}
}

func TestReplaceFilePropagatesStatErrors(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "artifact.jar")
	temp := filepath.Join(root, "artifact.jar.tmp")

	if err := os.WriteFile(temp, []byte("new"), 0o644); err != nil {
		t.Fatal(err)
	}

	oldStat := statFile
	statFile = func(string) (os.FileInfo, error) {
		return nil, os.ErrPermission
	}
	defer func() { statFile = oldStat }()

	if err := replaceFile(temp, target); !os.IsPermission(err) {
		t.Fatalf("replaceFile() error = %v, want permission error", err)
	}

	if _, err := os.Stat(temp); err != nil {
		t.Fatalf("temp file should remain after stat failure cleanup path: %v", err)
	}
}

func TestParseOptionsDefaultDownloadWorkers(t *testing.T) {
	t.Parallel()

	opts, err := parseOptions(nil)
	if err != nil {
		t.Fatalf("parseOptions() error = %v", err)
	}
	if opts.DownloadWorkers != 6 {
		t.Fatalf("parseOptions() DownloadWorkers = %d, want 6", opts.DownloadWorkers)
	}
}

func TestParseOptionsRejectsInvalidDownloadWorkers(t *testing.T) {
	t.Parallel()

	if _, err := parseOptions([]string{"--download-workers", "0"}); err == nil {
		t.Fatalf("parseOptions() accepted 0 workers")
	}
	if _, err := parseOptions([]string{"--download-workers", "17"}); err == nil {
		t.Fatalf("parseOptions() accepted 17 workers")
	}
}

func fileURL(path string) string {
	slashes := filepath.ToSlash(path)
	if strings.HasPrefix(slashes, "/") {
		return "file://" + slashes
	}
	return "file:///" + slashes
}

func countLaunchNogui(lines []string) int {
	count := 0
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(strings.ToLower(line), "java ") {
			continue
		}
		if strings.Count(strings.ToLower(line), " nogui ") == 1 {
			count++
		}
	}
	return count
}
