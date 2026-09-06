#  Debian/Ubuntu Ultimate Update Script 🚀

A comprehensive, automated bash script designed to keep your Ubuntu system fully up-to-date. It handles native `apt` system packages, `snap` packages, and `flatpak` packages in one smooth run, complete with a clean, color-coded terminal UI and a pause prompt so the window doesn't close automatically.

---

## ✨ Features

- **All-in-One Updates:** Automatically refreshes and upgrades APT packages, Snap packages, and Flatpak apps.
- **System Cleanup:** Removes orphaned dependencies (`autoremove`) and clears local package caches (`clean`) to free up disk space.
- **Smart Detection:** Gracefully checks if Snap and Flatpak are installed on your system before attempting to update them.
- **Terminal UI Polish:** Features bold, color-coded headers and step indicators for clear visual feedback.
- **Interactive Exit:** Pauses at the end so you can review the update logs before closing the terminal window.

---

## 🛠️ Prerequisites

Make sure you have `sudo` privileges and (optionally) Snap or Flatpak installed if you plan on updating those ecosystems.

---

## 📥 Setup

chmod +x update.sh
sudo ./update.sh
Open your terminal and create a new file named `update.sh`:
```bash
nano update.sh
