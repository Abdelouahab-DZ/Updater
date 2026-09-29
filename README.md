<div align="center">

# 🖥️ Ubuntu System Update GUI

**A sleek GTK 3 graphical updater for Ubuntu — APT, Snap, and Flatpak, all in one beautiful window.**

![Platform](https://img.shields.io/badge/platform-Ubuntu%20%7C%20Debian-E95420?logo=ubuntu&logoColor=white)
![Python](https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white)
![GTK](https://img.shields.io/badge/GUI-GTK%203-informational)
![License](https://img.shields.io/badge/license-as--is-lightgrey)

</div>

---

## ✨ Overview

Ubuntu System Update GUI brings a polished, modern interface to the everyday Ubuntu maintenance routine. Instead of juggling multiple terminal commands and remembering complex flags, this desktop application:

- **Runs all updates in sequence** — APT, Snap, and Flatpak in one window
- **Shows live progress** — watch each stage complete in real-time
- **Handles authentication elegantly** — graphical password prompt via `zenity`
- **Detects installed tools** — skips Snap or Flatpak if they're not on your system
- **Saves logs** — export the full update history for troubleshooting

Built on **GTK 3** with **PyGObject**, it integrates seamlessly with the GNOME desktop and other GTK-based environments.

---

## 📸 Screenshots

![Ubuntu Update GUI](ubuntu-update-gui.png)

*Live update progress with color-coded output: yellow for stages, green for success, red for errors.*

---

## 🎯 Features

| Feature | Benefit |
|---------|---------|
| 🖱️ **One-Click Updates** | No need to remember command flags; a single button drives the entire workflow |
| 📊 **Live Progress Bar** | Visual feedback shows which step is running and how many remain |
| 📜 **Color-Coded Log** | Output is syntax-highlighted (stages in yellow, success in green, errors in red, info in blue) |
| 🔐 **Graphical Auth** | Password prompt appears in a desktop dialog, not a terminal |
| 🧠 **Smart Detection** | Automatically skips Snap or Flatpak if not installed; shows why it's skipping |
| ⏱️ **Elapsed Timer** | Tracks how long the update takes |
| 💾 **Save Logs** | Export the full update log as a text file for debugging or records |
| 🚫 **Cancel Anytime** | Cleanly terminate the update and kill all child processes |

---

## 📋 Requirements

| Dependency | Purpose | Install |
|---|---|---|
| **Python 3.6+** | Runs the application | Pre-installed on Ubuntu |
| **python3-gi** | Provides GTK bindings for Python | `sudo apt install python3-gi` |
| **gir1.2-gtk-3.0** | GTK 3 type libraries | `sudo apt install gir1.2-gtk-3.0` |
| **zenity** | Graphical password dialog | `sudo apt install zenity` *(optional)* |
| **sudo** | Required for package operations | Pre-installed on Ubuntu |

### Quick Setup

Install all dependencies with a single command:

```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-3.0 zenity
```

---

## ▶️ Installation & Usage

### Option 1: Direct Execution (Recommended for Testing)

Clone the repository and run the Python script directly:

```bash
git clone https://github.com/Abdelouahab-DZ/Updater.git
cd Updater
python3 bin/ubuntu-update-gui
```

### Option 2: Install as Desktop Application

To make it available in your applications menu:

```bash
# Copy the executable to system PATH
sudo cp bin/ubuntu-update-gui /usr/local/bin/

# Copy the desktop entry (for app menus)
sudo cp ubuntu-update-gui.desktop /usr/share/applications/

# Copy the icon (if applicable)
sudo cp ubuntu-update-gui.png /usr/share/icons/hicolor/256x256/apps/
```

Then search for "Ubuntu Update GUI" in your applications menu.

---

## 🔧 How It Works

The application runs this sequence of commands, each in its own stage:

```bash
sudo -A apt update                              # Refresh package lists
sudo -A apt full-upgrade -y                     # Install all updates
sudo -A apt autoremove -y                       # Remove unused dependencies
sudo -A apt clean                               # Free up disk space
sudo -A snap refresh                            # Refresh Snap packages (if installed)
flatpak update -y                               # Update Flatpak apps (if installed)
```

Each command's output streams live into the color-coded log panel, so you always see what's happening.

**Key design choices:**
- Uses `SUDO_ASKPASS` to pop up a graphical password dialog instead of terminal input
- Runs each stage in a separate process with its own process group (easier to kill cleanly if cancelled)
- Sets `DEBIAN_FRONTEND=noninteractive` to prevent package managers from hanging on prompts
- Detects `snap` and `flatpak` at startup; skips them if not found

---

## 🎨 UI Overview

### Top: Header
- Bold title banner with Ubuntu blue background

### Upper Section: Controls
| Control | Purpose |
|---------|---------|
| **▶ Run Update** | Start the update sequence |
| **■ Cancel** | Stop the current update (disabled when idle) |
| **Save Log...** | Export the log to a text file |
| **Auto-scroll** | Toggle auto-scroll in the log (on by default) |

### Middle: Status & Progress
- **Status line** (left): Current stage or overall status
- **Timer** (right): Elapsed time in `MM:SS` format
- **Progress bar**: Visual indicator of steps completed

### Bottom: Log Panel
- Large scrollable text area with monospace font
- Color-coded lines:
  - **Yellow** (`[+]`): Stage headers
  - **Green** (`[✓]`): Success messages
  - **Red** (`[!]`): Errors or cancellation
  - **Blue** (`[i]`): Info messages (e.g., tool skipped)
  - **Gray**: Standard command output

---

## ⚙️ Advanced Configuration

### Environment Variables

You can control the app's behavior with environment variables:

```bash
# Override SUDO_ASKPASS behavior
SUDO_ASKPASS=/path/to/custom/askpass python3 bin/ubuntu-update-gui

# Set a custom frontend
DEBIAN_FRONTEND=noninteractive python3 bin/ubuntu-update-gui
```

### Customizing Stages

To edit which commands run, modify the `STAGES` list in `bin/ubuntu-update-gui`:

```python
STAGES = [
    ("Label here", "command to run"),
    ("Updating APT...", "apt update"),
    # ... add your own stages
]
```

---

## 📝 Troubleshooting

### zenity not found
If `zenity` isn't installed, password prompts fall back to the terminal. Install it:
```bash
sudo apt install zenity
```

### Permission denied or sudo timeout
Ensure your user is in the `sudoers` file and has NOPASSWD configured (optional, but recommended):
```bash
sudo visudo
# Add this line (replace USERNAME with your login):
# USERNAME ALL=(ALL) NOPASSWD: /usr/bin/apt, /usr/bin/snap
```

### GTK errors or missing dependencies
Reinstall GTK and PyGObject:
```bash
sudo apt install python3-gi gir1.2-gtk-3.0
```

### App hangs during update
If the app seems stuck, click **Cancel** to terminate the current operation. The process cleanup is automatic.

---

## 🏗️ Project Structure

```
Updater/
├── bin/
│   └── ubuntu-update-gui      # Main GTK application (executable)
├── AppRun                      # AppImage launcher (compatibility wrapper)
├── ubuntu-update-gui.desktop   # Desktop entry for app menus
├── ubuntu-update-gui.png       # Application icon
└── README.md                   # This file
```

---

## 🔐 Security & Safety

- **Passwords are never logged** — the app only captures command output, not stdin
- **Sudo access is required** — the app enforces privilege escalation for package operations
- **Graceful termination** — cancelling kills the entire process group, not just the shell
- **Tested on production systems** — safe for everyday use, but always back up critical data before major upgrades

---

## 🤝 Contributing

Found a bug? Have a suggestion?
- Open an [issue](https://github.com/Abdelouahab-DZ/Updater/issues)
- Submit a [pull request](https://github.com/Abdelouahab-DZ/Updater/pulls)

---

## ⚠️ Warnings

> [!IMPORTANT]
> **Back up critical data before running full system upgrades.** While this app is designed for everyday use, major version upgrades can change system behavior or break dependencies.

> [!WARNING]
> **On production or mission-critical systems,** test updates in a sandbox or staging environment first. Full upgrades can introduce breaking changes.

> [!NOTE]
> If `zenity` is unavailable, password prompts appear in the terminal — still secure, just less graphical.

---

## 📄 License

This project is provided **as-is** for personal or system maintenance use. Feel free to fork, modify, and use as needed.

---

## 🚀 What's Next?

Potential improvements:
- [ ] AppImage packaging for easy distribution
- [ ] Schedule automatic updates
- [ ] Support for other package managers (pacman, dnf, etc.)
- [ ] Rollback capability for failed upgrades
- [ ] Dark/light theme toggle

---

<div align="center">

**Built with ❤️ for Ubuntu users everywhere.**

</div>
