#!/usr/bin/env python3
"""
Ubuntu System Update - GUI
A simple Tkinter front-end for the apt/snap/flatpak update routine.

Requirements:
    - python3 (with tkinter)   -> sudo apt install python3-tk
    - zenity (graphical sudo password prompt) -> sudo apt install zenity

Run it with:
    python3 ubuntu_update_gui.py
"""

import os
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

# ---------------------------------------------------------------------------
# The actual update logic (same steps as the original bash script), split
# into labeled stages so the GUI can show progress for each one.
# ---------------------------------------------------------------------------
STAGES = [
    ("Updating APT package lists...", "sudo -A apt update"),
    ("Upgrading installed packages...", "sudo -A apt full-upgrade -y"),
    ("Removing unused dependencies...", "sudo -A apt autoremove -y"),
    ("Cleaning APT cache...", "sudo -A apt clean"),
    ("Refreshing Snap packages...",
     "command -v snap >/dev/null && sudo -A snap refresh || echo 'snap not installed, skipping'"),
    ("Refreshing Flatpak packages...",
     "command -v flatpak >/dev/null && flatpak update -y || echo 'flatpak not installed, skipping'"),
]


def make_askpass_script():
    """
    Creates a temporary SUDO_ASKPASS helper that pops up a graphical
    password dialog (via zenity) instead of asking in a terminal.
    Returns the path to the helper script.
    """
    if not shutil.which("zenity"):
        return None

    fd, path = tempfile.mkstemp(prefix="askpass_", suffix=".sh")
    with os.fdopen(fd, "w") as f:
        f.write(
            "#!/bin/sh\n"
            'zenity --password --title="Authentication required" 2>/dev/null\n'
        )
    os.chmod(path, 0o700)
    return path


class UpdateGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ubuntu System Update")
        self.geometry("620x480")
        self.resizable(True, True)

        self.askpass_path = None
        self.proc = None
        self.running = False

        self._build_ui()

    # -- UI construction ----------------------------------------------
    def _build_ui(self):
        header = tk.Label(
            self,
            text="UBUNTU SYSTEM UPDATE",
            font=("Sans", 16, "bold"),
            fg="white",
            bg="#1f4fd6",
            pady=12,
        )
        header.pack(fill="x")

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack(fill="x")

        self.run_btn = tk.Button(
            btn_frame,
            text="▶  Run Update",
            font=("Sans", 11, "bold"),
            bg="#2e9e3f",
            fg="white",
            padx=16,
            pady=6,
            command=self.start_update,
        )
        self.run_btn.pack(side="left", padx=12)

        self.status_label = tk.Label(btn_frame, text="Idle", font=("Sans", 10, "italic"))
        self.status_label.pack(side="left", padx=8)

        self.log = scrolledtext.ScrolledText(
            self, wrap="word", bg="#111", fg="#ddd", insertbackground="#ddd",
            font=("Monospace", 10)
        )
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log.configure(state="disabled")

        # tag colors for log lines
        self.log.tag_config("stage", foreground="#ffd93d")
        self.log.tag_config("ok", foreground="#6bff6b")
        self.log.tag_config("err", foreground="#ff6b6b")

    # -- logging helpers -------------------------------------------------
    def log_write(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text, tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    # -- update flow -------------------------------------------------
    def start_update(self):
        if self.running:
            return
        self.running = True
        self.run_btn.configure(state="disabled", text="Running...")
        self.status_label.configure(text="Starting...")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

        self.askpass_path = make_askpass_script()
        if self.askpass_path is None:
            messagebox.showwarning(
                "zenity not found",
                "zenity is not installed, so sudo password prompts may appear "
                "in the terminal instead of a graphical dialog.\n\n"
                "Install it with: sudo apt install zenity",
            )

        threading.Thread(target=self._run_all_stages, daemon=True).start()

    def _run_all_stages(self):
        env = os.environ.copy()
        if self.askpass_path:
            env["SUDO_ASKPASS"] = self.askpass_path

        all_ok = True
        for i, (label, cmd) in enumerate(STAGES, start=1):
            self.status_label.configure(text=f"Step {i}/{len(STAGES)}")
            self.log_write(f"\n[+] {label}\n", "stage")

            proc = subprocess.Popen(
                cmd,
                shell=True,
                executable="/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
            )
            self.proc = proc
            for line in proc.stdout:
                self.log_write(line)
            proc.wait()

            if proc.returncode != 0:
                all_ok = False
                self.log_write(f"[!] Step failed (exit code {proc.returncode})\n", "err")
                # keep going with remaining steps rather than aborting entirely

        if all_ok:
            self.log_write("\n=== UPDATE COMPLETE! ===\n", "ok")
            self.status_label.configure(text="Done")
        else:
            self.log_write("\n=== UPDATE FINISHED WITH ERRORS ===\n", "err")
            self.status_label.configure(text="Finished with errors")

        if self.askpass_path and os.path.exists(self.askpass_path):
            os.remove(self.askpass_path)

        self.running = False
        self.run_btn.configure(state="normal", text="▶  Run Update")


if __name__ == "__main__":
    app = UpdateGUI()
    app.mainloop()
