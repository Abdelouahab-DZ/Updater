# Ubuntu System Update GUI

A graphical updater for Ubuntu systems built with Python and Tkinter. It automates the most common update tasks in one simple interface and shows progress as each step runs.

This project includes a GUI version of the standard system update workflow for:

- APT package updates
- Full system upgrades
- Dependency cleanup
- APT cache cleanup
- Snap refreshes
- Flatpak updates

## Features

- Simple desktop interface with a Run Update button
- Progress tracking by stage
- Live log output in a scrollable panel
- Graphical sudo password prompt via `zenity` when available
- Automatic skip for missing Snap or Flatpak tools

## Requirements

- Python 3
- Tkinter (`python3-tk`)
- `zenity` (recommended for graphical sudo prompts)
- `sudo` access enabled for your user

Install the packages on Ubuntu or Debian:

```bash
sudo apt update
sudo apt install python3-tk zenity
```

## Run

```bash
python3 ubuntu_update_gui.py
```

## What the script does

The GUI runs the following commands in sequence:

```bash
sudo -A apt update
sudo -A apt full-upgrade -y
sudo -A apt autoremove -y
sudo -A apt clean
command -v snap >/dev/null && sudo -A snap refresh || echo 'snap not installed, skipping'
command -v flatpak >/dev/null && flatpak update -y || echo 'flatpak not installed, skipping'
```

## Notes

- If `zenity` is not installed, the script will still work, but the sudo password prompt may appear in the terminal instead of a graphical dialog.
- The script is designed for Ubuntu-based systems.
- Use with care on production or critical systems; upgrades can affect package versions and installed software.

## License

This project is provided as-is for personal or system maintenance use.
