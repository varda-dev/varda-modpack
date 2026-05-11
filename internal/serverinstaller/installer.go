package serverinstaller

import (
	"errors"
	"flag"
	"fmt"
	"os"
)

type Options struct {
	Force           bool
	SkipMods        bool
	SkipNeoForge    bool
	DownloadWorkers int
	TargetDir       string
}

func Run(args []string) error {
	opts, err := parseOptions(args)
	if err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return nil
		}
		return err
	}

	if opts.TargetDir == "" {
		opts.TargetDir = "."
	}

	if err := os.MkdirAll(opts.TargetDir, 0o755); err != nil {
		return fmt.Errorf("create target dir: %w", err)
	}

	if err := RequireJava21(); err != nil {
		return err
	}

	if err := ExtractPayload(opts.TargetDir); err != nil {
		return err
	}
	if err := WriteDiagnostics(opts.TargetDir); err != nil {
		return err
	}

	_, desiredVersion, err := ReadDesiredNeoForgeState(opts.TargetDir)
	if err != nil {
		return err
	}

	if !opts.SkipNeoForge {
		desiredVersion, err = InstallOrUpdateNeoForge(opts.TargetDir, opts.Force)
		if err != nil {
			return err
		}
	} else {
		fmt.Println("Skipping NeoForge install/update.")
	}

	if err := WriteJvmArgs(opts.TargetDir); err != nil {
		return err
	}
	if err := PatchLaunchers(opts.TargetDir, desiredVersion); err != nil {
		return err
	}
	if err := cleanupNeoForgeInstallerArtifacts(opts.TargetDir); err != nil {
		return err
	}

	if !opts.SkipMods {
		if err := ReconcileMods(opts.TargetDir, opts.Force, opts.DownloadWorkers); err != nil {
			return err
		}
	}

	fmt.Println("Setup complete.")
	return nil
}

func parseOptions(args []string) (Options, error) {
	var opts Options

	fs := flag.NewFlagSet("varda-server-installer", flag.ContinueOnError)
	fs.BoolVar(&opts.Force, "force", false, "re-download/reinstall files")
	fs.BoolVar(&opts.SkipMods, "skip-mods", false, "skip mod reconciliation")
	fs.BoolVar(&opts.SkipNeoForge, "skip-neoforge", false, "skip NeoForge install/update")
	fs.IntVar(&opts.DownloadWorkers, "download-workers", 6, "mod download worker count")
	fs.StringVar(&opts.TargetDir, "dir", ".", "server install directory")

	if err := fs.Parse(args); err != nil {
		return opts, err
	}

	if opts.DownloadWorkers < 1 || opts.DownloadWorkers > 16 {
		return opts, fmt.Errorf("--download-workers must be between 1 and 16")
	}

	return opts, nil
}
