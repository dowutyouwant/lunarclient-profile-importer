# Lunar Client Profile Importer

A simple CLI tool to import Lunar Client profiles from a local file or a MediaFire download link.

## Features

- Import profiles from `.zip`, `.rar`, `.7z` archives or raw `.json` files
- Download directly from a **MediaFire** link
- Supports both **single-file** profiles (`modSettings`) and **multi-file** profiles (`mods.json`, `controls.json`, etc.)
- Automatically registers the profile in Lunar Client's profile manager
- Creates a timestamped backup of `profilemanager.json` before any changes
- Auto-installs its own Python dependencies on first run (no manual `pip install` needed)

## Requirements

- **Python 3.8+**
- **Lunar Client** installed (run it once to create the settings directory)
- For `.rar` / `.7z` archives: **7-Zip** or **WinRAR** must be on your `PATH`

## Usage

### Double-click (Windows)

Double-click `run.bat`. The script will install missing dependencies automatically on the first run.

### Command line

```
python importer.py
```

When prompted, paste a **MediaFire link** or drag & drop a profile file into the terminal, then press Enter.

## Supported input formats

| Input | Description |
|-------|-------------|
| MediaFire URL | Direct download link (`https://www.mediafire.com/...`) |
| `.zip` / `.rar` / `.7z` | Archive containing profile files |
| `.json` | Raw single-file Lunar Client profile |

## How it works

1. Downloads or reads the provided file.
2. Detects whether the profile is a single JSON or a folder of settings files.
3. Copies the files to `~/.lunarclient/settings/game/<profile-name>/`.
4. Patches `profilemanager.json` so the profile appears inside Lunar Client.

## Notes

- Close Lunar Client before running the importer — the tool will wait and remind you if it is still open.
- The original `profilemanager.json` is backed up as `profilemanager.json.bak.<timestamp>` before any write.
