<div align="center">

# 🖥️ Ubuntu System Update GUI

**A one-click graphical updater for Ubuntu — APT, Snap, and Flatpak, all in one window.**

![Platform](https://img.shields.io/badge/platform-Ubuntu%20%7C%20Debian-E95420?logo=ubuntu&logoColor=white)
![Python](https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-informational)
![License](https://img.shields.io/badge/license-as--is-lightgrey)

</div>

---

## ✨ Description

Ubuntu System Update GUI wraps the everyday Ubuntu maintenance routine — updating APT, cleaning up old packages, and refreshing Snap and Flatpak — into a single desktop window. Instead of remembering and running six separate commands in a terminal, you click one button and watch each stage complete in a live, color-coded log, with sudo authentication handled through a graphical password prompt instead of the command line.

A graphical updater for Ubuntu systems built with Python and Tkinter. It automates the most common update tasks in one simple interface and shows progress as each step runs.

This project includes a GUI version of the standard system update workflow for:

| Task | Command |
|---|---|
| 📦 APT package updates | `apt update` |
| ⬆️ Full system upgrade | `apt full-upgrade` |
| 🧹 Dependency cleanup | `apt autoremove` |
| 🗑️ APT cache cleanup | `apt clean` |
| 🔄 Snap refresh | `snap refresh` |
| 🔄 Flatpak update | `flatpak update` |

---

## 🚀 Features

- 🖱️ **One-click updates** — a single "Run Update" button drives the whole workflow
- 📊 **Stage-by-stage progress** — always know which step is running
- 📜 **Live scrollable log** — full command output, color-coded for success/failure
- 🔐 **Graphical sudo prompt** — via `zenity`, no password typed into a terminal
- 🧠 **Smart tool detection** — automatically skips Snap or Flatpak if not installed

---

## 📋 Requirements

| Dependency | Purpose | Install |
|---|---|---|
| Python 3 | Runs the GUI | usually preinstalled |
| `python3-tk` | Tkinter GUI toolkit | `sudo apt install python3-tk` |
| `zenity` | Graphical sudo prompt (recommended) | `sudo apt install zenity` |
| `sudo` access | Required for package operations | — |

Install everything at once:

```bash
sudo apt update
sudo apt install python3-tk zenity
```

---

## ▶️ Run

```bash
python3 ubuntu_update_gui.py
```

---

## ⚙️ What it does under the hood

The GUI runs the following commands in sequence, streaming their output live into the log panel:

```bash
sudo -A apt update
sudo -A apt full-upgrade -y
sudo -A apt autoremove -y
sudo -A apt clean
command -v snap >/dev/null && sudo -A snap refresh || echo 'snap not installed, skipping'
command -v flatpak >/dev/null && flatpak update -y || echo 'flatpak not installed, skipping'
```

---

## 📝 Notes

> [!NOTE]
> If `zenity` isn't installed, the app still works — the sudo password prompt just falls back to appearing in the terminal instead of a graphical dialog.

> [!WARNING]
> Use with care on production or critical systems. Full upgrades can change package versions and installed software.

- Designed for Ubuntu-based systems (Debian derivatives should work too).

---

## 📄 License

This project is provided **as-is** for personal or system maintenance use.
