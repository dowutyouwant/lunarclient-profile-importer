#!/usr/bin/env python3
import os
import sys
import subprocess
import importlib

_PACKAGES = {
    "mediafiredl": "mediafiredl",
    "requests": "requests",
    "beautifulsoup4": "bs4",
    "patool": "patoolib",
    "colorama": "colorama",
}

_BOOTSTRAP_DONE_ENV = "_IMPORTER_BOOTSTRAPPED"

def _bootstrap():
    if os.environ.get(_BOOTSTRAP_DONE_ENV):
        return
    installed_any = False
    for pip_name, import_name in _PACKAGES.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            print(f"  Installing {pip_name}...")
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", pip_name, "-q"],
                capture_output=True,
            )
            if r.returncode != 0:
                print(f"[x] Failed to install {pip_name}. Run: pip install {pip_name}")
                sys.exit(1)
            installed_any = True
    if installed_any:
        env = os.environ.copy()
        env[_BOOTSTRAP_DONE_ENV] = "1"
        result = subprocess.run([sys.executable] + sys.argv, env=env)
        sys.exit(result.returncode)

_bootstrap()

import copy
import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import colorama
from colorama import Fore, Style
import patoolib as patool

colorama.init(autoreset=True)

VERSION = "1.0.0"

def print_header():
    sep = "=" * 60
    print(Fore.CYAN + "")
    print(Fore.CYAN + f"  {sep}")
    print(Fore.CYAN + "   Lunar Client Profile Importer  v" + VERSION)
    print(Fore.CYAN + f"  {sep}")
    print()

_ICONS = {
    "v": Fore.GREEN + "[v]",
    "!": Fore.YELLOW + "[!]",
    "x": Fore.RED + "[x]",
    "~": Fore.CYAN + "[~]",
}

def print_status(icon, msg):
    prefix = _ICONS.get(icon, f"[{icon}]")
    print(f"{prefix}{Style.RESET_ALL} {msg}")

def is_lunar_running():
    targets = ["Lunar Client.exe", "LunarClient.exe"]
    for target in targets:
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {target}", "/NH"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
            )
            if target.lower() in r.stdout.lower():
                return True
        except Exception:
            pass
    return False

def detect_input_type(raw):
    raw = raw.strip()
    # PowerShell drag-and-drop produces: & 'C:\pathile.zip'
    if raw.startswith("& "):
        raw = raw[2:].strip()
    raw = raw.strip('"').strip("'")
    if raw.startswith("https://") or raw.startswith("http://"):
        return "url", raw
    return "file", raw

def download_mediafire(url, tmp_dir):
    try:
        from mediafiredl import MediafireDL
        filename = MediafireDL.GetName(url) or "profile_download"
        print_status("~", f"Downloading... {filename}")
        MediafireDL.Download(url, tmp_dir, filename)
        out_path = Path(tmp_dir) / filename
        print_status("v", "Download complete.")
        return str(out_path)
    except Exception as e:
        print_status("x", f"Download failed: {e}")
        print_status("!", "Check the URL and your internet connection.")
        sys.exit(1)

_SETTINGS_FILENAMES = {
    "mods.json", "general.json", "controls.json",
    "performance.json", "staff_mods.json",
}

def _scan_extracted(directory):
    single = None
    multi_files = []
    for fpath in Path(directory).rglob("*.json"):
        fname = fpath.name
        if fname in _SETTINGS_FILENAMES:
            multi_files.append((str(fpath), fname))
        else:
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                if "modSettings" in data:
                    single = str(fpath)
            except Exception:
                pass
    if multi_files:
        return "multi", multi_files
    if single:
        return "single", single
    return "unknown", None

def extract_archive(archive_path, tmp_dir):
    extract_dir = Path(tmp_dir) / "extracted"
    extract_dir.mkdir(exist_ok=True)
    print_status("~", "Extracting...")
    try:
        patool.extract_archive(archive_path, outdir=str(extract_dir))
    except Exception as e:
        print_status("x", f"Extraction failed: {e}")
        if Path(archive_path).suffix.lower() in (".rar", ".7z"):
            print_status("!", "For .rar / .7z files, install 7-Zip or WinRAR and make sure it is on your PATH.")
        sys.exit(1)
    fmt, result = _scan_extracted(extract_dir)
    if fmt == "unknown":
        print_status("x", "No valid Lunar Client profile found in archive.")
        sys.exit(1)
    return fmt, result

def _sanitize_name(raw):
    name = raw.strip().replace(" ", "_")
    return re.sub("[^a-zA-Z0-9_-]", "", name)

def _lunar_settings_dir():
    return Path.home() / ".lunarclient" / "settings" / "game"

def _confirm_overwrite(name):
    print_status("!", f'Profile "{name}" already exists. Overwrite? [y/N]:')
    if input("> ").strip().lower() != "y":
        print_status("!", "Import cancelled.")
        sys.exit(0)


def _backup_file(path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_path = Path(str(path) + f".bak.{timestamp}")
    try:
        shutil.copy2(path, bak_path)
    except Exception as e:
        print_status("x", f"Backup failed: {e}. Aborting to protect your data.")
        sys.exit(1)


_PM_FILENAME = "profilemanager.json"


def install_multi(settings_files, display_name):
    settings_dir = _lunar_settings_dir()
    if not settings_dir.exists():
        print_status("x", f"Lunar Client settings directory not found: {settings_dir}")
        print_status("!", "Start Lunar Client once to create it, then close it and run this tool again.")
        sys.exit(1)
    name = _sanitize_name(display_name)
    profile_dir = settings_dir / name
    if profile_dir.exists():
        _confirm_overwrite(name)
        shutil.rmtree(profile_dir)
    profile_dir.mkdir()
    for src_path, fname in settings_files:
        shutil.copy2(src_path, profile_dir / fname)
        print_status("v", f"Installed {fname}")
    pm_path = settings_dir / _PM_FILENAME
    if not pm_path.exists():
        print_status("!", f"{_PM_FILENAME} not found - profile installed but not registered in profile manager.")
    else:
        _backup_file(pm_path)
        with open(pm_path, "r", encoding="utf-8") as f:
            pm_data = json.load(f)
        pm_data = [p for p in pm_data if p.get("name") != name]
        pm_data.append({
            "name": name,
            "displayName": display_name,
            "default": False,
            "active": False,
            "iconName": "",
            "server": "",
        })
        with open(pm_path, "w", encoding="utf-8") as f:
            json.dump(pm_data, f, indent=2)
    return display_name

def patch_profilemanager(profile_path, display_name):
    settings_dir = _lunar_settings_dir()
    pm_path = settings_dir / _PM_FILENAME
    if not pm_path.exists():
        print_status("x", f"{_PM_FILENAME} not found.")
        print_status("!", "Start Lunar Client once to create it, then close it and run this tool again.")
        sys.exit(1)
    with open(pm_path, "r", encoding="utf-8") as f:
        pm_data = json.load(f)
    profiles = pm_data.get("profiles", [])
    name = _sanitize_name(display_name)
    existing = next((p for p in profiles if p.get("name") == name), None)
    if existing:
        _confirm_overwrite(name)
        profiles.remove(existing)
    _backup_file(pm_path)
    dest_path = settings_dir / f"{name}.json"
    shutil.copy2(profile_path, dest_path)
    default_entry = next((p for p in profiles if p.get("default", False)), None)
    if default_entry is None and profiles:
        default_entry = profiles[0]
    if default_entry is None:
        new_entry = {"name": name, "displayName": display_name, "default": False}
    else:
        new_entry = copy.deepcopy(default_entry)
        new_entry["name"] = name
        new_entry["displayName"] = display_name
        new_entry["default"] = False
    profiles.append(new_entry)
    pm_data["profiles"] = profiles
    with open(pm_path, "w", encoding="utf-8") as f:
        json.dump(pm_data, f, indent=2)
    return display_name

def main():
    print_header()
    print("Paste a MediaFire link or drag & drop your profile file, then press Enter:")
    raw = input("> ").strip()
    if not raw:
        print_status("x", "No input provided.")
        sys.exit(1)
    input_type, value = detect_input_type(raw)
    while is_lunar_running():
        print_status("!", "Lunar Client is running. Please close it and press Enter to continue...")
        input()
    with tempfile.TemporaryDirectory() as tmp_dir:
        if input_type == "url":
            file_path = download_mediafire(value, tmp_dir)
        else:
            file_path = value.strip()
            if not Path(file_path).exists():
                print_status("x", f"File not found: {file_path}")
                sys.exit(1)
        ext = Path(file_path).suffix.lower()
        if ext in (".zip", ".rar", ".7z"):
            fmt, result = extract_archive(file_path, tmp_dir)
        elif ext == ".json":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "modSettings" not in data:
                    print_status("x", "This JSON file does not appear to be a Lunar Client profile.")
                    sys.exit(1)
            except Exception as e:
                print_status("x", f"Could not read profile: {e}")
                sys.exit(1)
            fmt, result = "single", file_path
        else:
            print_status("x", f"Unsupported file type: {ext}")
            sys.exit(1)

        if fmt == "multi":
            fnames = [f for _, f in result]
            print_status("~", f"Found settings files: {"".join(fnames)}")
            suggested = Path(file_path).stem
            print(f"Display name [{suggested}]: ", end="", flush=True)
            display_name = input().strip() or suggested
            final_name = install_multi(result, display_name)
            print_status("v", f'Profile "{final_name}" applied to active settings.')
            print_status("!", "These settings are now active - launch Lunar Client to use them.")
        else:
            suggested = Path(result).stem
            print(f"Display name [{suggested}]: ", end="", flush=True)
            display_name = input().strip() or suggested
            final_name = patch_profilemanager(result, display_name)
            print_status("v", f'Profile "{final_name}" imported successfully!')

    print("")
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
