#!/usr/bin/env python3
"""
Ubuntu System Update - GUI
A Tkinter front-end for the apt/snap/flatpak update routine.

Requirements:
    - python3 (with tkinter)   -> sudo apt install python3-tk
    - zenity (graphical sudo password prompt) -> sudo apt install zenity

Run it with:
    python3 ubuntu_update_gui.py
"""

import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

# ---------------------------------------------------------------------------
# The actual update logic (same steps as the original bash script), split
# into labeled stages so the GUI can show progress for each one.
# ---------------------------------------------------------------------------
STAGES = [
    ("Updating APT package lists...", "apt update"),
    ("Upgrading installed packages...", "apt full-upgrade -y"),
    ("Removing unused dependencies...", "apt autoremove -y"),
    ("Cleaning APT cache...", "apt clean"),
    ("Refreshing Snap packages...", "__SNAP_REFRESH__"),
    ("Refreshing Flatpak packages...", "__FLATPAK_UPDATE__"),
]


def make_askpass_script():
    """
    Creates a temporary SUDO_ASKPASS helper that pops up a graphical
    password dialog (via zenity) instead of asking in a terminal.
    Returns the path to the helper script, or None if zenity is missing.
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
        self.geometry("680x560")
        self.minsize(520, 400)

        self.askpass_path = None
        self.proc = None
        self.running = False
        self.cancelled = False
        self.start_time = None
        self.autoscroll = tk.BooleanVar(value=True)
        self.has_snap = shutil.which("snap") is not None
        self.has_flatpak = shutil.which("flatpak") is not None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Return>", lambda e: self.start_update())

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
        btn_frame.pack(fill="x", padx=10)

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
        self.run_btn.pack(side="left")

        self.cancel_btn = tk.Button(
            btn_frame,
            text="■  Cancel",
            font=("Sans", 11, "bold"),
            bg="#c0392b",
            fg="white",
            padx=16,
            pady=6,
            state="disabled",
            command=self.cancel_update,
        )
        self.cancel_btn.pack(side="left", padx=8)

        self.save_btn = tk.Button(
            btn_frame, text="Save Log...", command=self.save_log
        )
        self.save_btn.pack(side="left", padx=8)

        autoscroll_chk = tk.Checkbutton(
            btn_frame, text="Auto-scroll", variable=self.autoscroll
        )
        autoscroll_chk.pack(side="right")

        # Status row: label + elapsed time
        status_frame = tk.Frame(self)
        status_frame.pack(fill="x", padx=12)
        self.status_label = tk.Label(status_frame, text="Idle", font=("Sans", 10, "italic"))
        self.status_label.pack(side="left")
        self.timer_label = tk.Label(status_frame, text="", font=("Sans", 10))
        self.timer_label.pack(side="right")

        # Progress bar
        self.progress = ttk.Progressbar(
            self, orient="horizontal", mode="determinate", maximum=len(STAGES)
        )
        self.progress.pack(fill="x", padx=12, pady=(4, 8))

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
        self.log.tag_config("info", foreground="#7fb0ff")

        if not self.has_snap:
            self.log_write("[i] Snap not detected — that step will be skipped.\n", "info")
        if not self.has_flatpak:
            self.log_write("[i] Flatpak not detected — that step will be skipped.\n", "info")

    # -- logging helpers -------------------------------------------------
    def log_write(self, text, tag=None):
        def _write():
            self.log.configure(state="normal")
            self.log.insert("end", text, tag)
            if self.autoscroll.get():
                self.log.see("end")
            self.log.configure(state="disabled")
        self.after(0, _write)

    def save_log(self):
        content = self.log.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showinfo("Save Log", "There's nothing to save yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Log",
            defaultextension=".txt",
            initialfile="ubuntu-update-log.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w") as f:
                f.write(content)
        except OSError as e:
            messagebox.showerror("Save Log", f"Could not save log:\n{e}")

    # -- window lifecycle -------------------------------------------------
    def _on_close(self):
        if self.running:
            if not messagebox.askyesno(
                "Update in progress",
                "An update is still running. Cancel it and quit?",
            ):
                return
            self.cancel_update()
        self._cleanup_askpass()
        self.destroy()

    def _cleanup_askpass(self):
        if self.askpass_path and os.path.exists(self.askpass_path):
            try:
                os.remove(self.askpass_path)
            except OSError:
                pass
            self.askpass_path = None

    # -- timer -------------------------------------------------
    def _tick_timer(self):
        if self.running and self.start_time is not None:
            elapsed = int(time.time() - self.start_time)
            mins, secs = divmod(elapsed, 60)
            self.timer_label.configure(text=f"Elapsed: {mins:02d}:{secs:02d}")
            self.after(1000, self._tick_timer)

    # -- update flow -------------------------------------------------
    def start_update(self):
        if self.running:
            return
        self.running = True
        self.cancelled = False
        self.start_time = time.time()
        self.run_btn.configure(state="disabled", text="Running...")
        self.cancel_btn.configure(state="normal")
        self.status_label.configure(text="Starting...")
        self.progress.configure(value=0)
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

        self._tick_timer()
        threading.Thread(target=self._run_all_stages, daemon=True).start()

    def cancel_update(self):
        if not self.running:
            return
        self.cancelled = True
        self.log_write("\n[!] Cancelling...\n", "err")
        if self.proc and self.proc.poll() is None:
            try:
                pgid = os.getpgid(self.proc.pid)
                os.killpg(pgid, signal.SIGTERM)
                time.sleep(0.5)
                if self.proc.poll() is None:
                    os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.cancel_btn.configure(state="disabled")

    def _stage_command(self, cmd_key):
        if cmd_key == "__SNAP_REFRESH__":
            if not self.has_snap:
                return None
            return "sudo -A snap refresh"
        if cmd_key == "__FLATPAK_UPDATE__":
            if not self.has_flatpak:
                return None
            return "flatpak update -y"
        return f"sudo -A {cmd_key}"

    def _run_all_stages(self):
        env = os.environ.copy()
        env["DEBIAN_FRONTEND"] = "noninteractive"
        if self.askpass_path:
            env["SUDO_ASKPASS"] = self.askpass_path

        all_ok = True
        for i, (label, cmd_key) in enumerate(STAGES, start=1):
            if self.cancelled:
                break

            cmd = self._stage_command(cmd_key)
            self.after(0, lambda i=i: self.progress.configure(value=i - 1))
            self.status_label.configure(text=f"Step {i}/{len(STAGES)}")

            if cmd is None:
                self.log_write(f"\n[+] {label}\n", "stage")
                self.log_write("[i] Skipped — tool not installed.\n", "info")
                self.after(0, lambda i=i: self.progress.configure(value=i))
                continue

            self.log_write(f"\n[+] {label}\n", "stage")

            try:
                proc = subprocess.Popen(
                    cmd,
                    shell=True,
                    executable="/bin/bash",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=env,
                    text=True,
                    start_new_session=True,  # own process group, so cancel can kill sudo's children too
                )
            except OSError as e:
                all_ok = False
                self.log_write(f"[!] Failed to start step: {e}\n", "err")
                continue

            self.proc = proc
            for line in proc.stdout:
                self.log_write(line)
            proc.wait()

            if proc.returncode != 0:
                all_ok = False
                if self.cancelled:
                    self.log_write("[!] Step cancelled by user\n", "err")
                else:
                    self.log_write(f"[!] Step failed (exit code {proc.returncode})\n", "err")
                if self.cancelled:
                    break
                # keep going with remaining steps rather than aborting entirely

        final_value = len(STAGES) if all_ok else self.progress["value"]
        self.after(0, lambda: self.progress.configure(value=final_value))

        if self.cancelled:
            self.log_write("\n=== UPDATE CANCELLED ===\n", "err")
            self.status_label.configure(text="Cancelled")
        elif all_ok:
            self.log_write("\n=== UPDATE COMPLETE! ===\n", "ok")
            self.status_label.configure(text="Done")
        else:
            self.log_write("\n=== UPDATE FINISHED WITH ERRORS ===\n", "err")
            self.status_label.configure(text="Finished with errors")

        self._cleanup_askpass()

        self.running = False
        self.proc = None
        self.run_btn.configure(state="normal", text="▶  Run Update")
        self.cancel_btn.configure(state="disabled")


if __name__ == "__main__":
    app = UpdateGUI()
    app.mainloop()
