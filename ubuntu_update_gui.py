#!/usr/bin/env python3
"""
Ubuntu System Update - GTK GUI
A GTK 3 (PyGObject) front-end for the apt/snap/flatpak update routine.

Requirements:
    - python3-gi + GTK 3 typelibs -> sudo apt install python3-gi gir1.2-gtk-3.0
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

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango

# ---------------------------------------------------------------------------
# Update stages. "__SNAP_REFRESH__" / "__FLATPAK_UPDATE__" are resolved at
# run time depending on which tools are actually installed.
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


class UpdateWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Ubuntu System Update")
        self.set_default_size(700, 560)
        self.set_size_request(520, 400)

        self.askpass_path = None
        self.proc = None
        self.running = False
        self.cancelled = False
        self.start_time = None
        self.has_snap = shutil.which("snap") is not None
        self.has_flatpak = shutil.which("flatpak") is not None

        self.connect("delete-event", self.on_close)

        self._build_ui()

        if not self.has_snap:
            self.log_write("[i] Snap not detected — that step will be skipped.\n", "info")
        if not self.has_flatpak:
            self.log_write("[i] Flatpak not detected — that step will be skipped.\n", "info")

    # -- UI construction ----------------------------------------------
    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root)

        # Header bar (title band)
        header = Gtk.EventBox()
        header_css = Gtk.CssProvider()
        header_css.load_from_data(b"""
            box.header { background-color: #1f4fd6; }
            label.header { color: white; font-weight: bold; font-size: 18px; }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), header_css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.get_style_context().add_class("header")
        header_label = Gtk.Label(label="UBUNTU SYSTEM UPDATE")
        header_label.get_style_context().add_class("header")
        header_label.set_margin_top(14)
        header_label.set_margin_bottom(14)
        header_box.set_halign(Gtk.Align.CENTER)
        header_box.pack_start(header_label, True, True, 0)
        header.add(header_box)
        root.pack_start(header, False, False, 0)

        # Button row
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_margin_top(10)
        btn_box.set_margin_bottom(6)
        btn_box.set_margin_start(10)
        btn_box.set_margin_end(10)
        root.pack_start(btn_box, False, False, 0)

        self.run_btn = Gtk.Button(label="▶  Run Update")
        self.run_btn.get_style_context().add_class("suggested-action")
        self.run_btn.connect("clicked", self.start_update)
        btn_box.pack_start(self.run_btn, False, False, 0)

        self.cancel_btn = Gtk.Button(label="■  Cancel")
        self.cancel_btn.get_style_context().add_class("destructive-action")
        self.cancel_btn.set_sensitive(False)
        self.cancel_btn.connect("clicked", self.cancel_update)
        btn_box.pack_start(self.cancel_btn, False, False, 0)

        self.save_btn = Gtk.Button(label="Save Log...")
        self.save_btn.connect("clicked", self.save_log)
        btn_box.pack_start(self.save_btn, False, False, 0)

        self.autoscroll_chk = Gtk.CheckButton(label="Auto-scroll")
        self.autoscroll_chk.set_active(True)
        btn_box.pack_end(self.autoscroll_chk, False, False, 0)

        # Status row
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.set_margin_start(12)
        status_box.set_margin_end(12)
        root.pack_start(status_box, False, False, 0)

        self.status_label = Gtk.Label(label="Idle")
        self.status_label.set_halign(Gtk.Align.START)
        status_box.pack_start(self.status_label, True, True, 0)

        self.timer_label = Gtk.Label(label="")
        self.timer_label.set_halign(Gtk.Align.END)
        status_box.pack_end(self.timer_label, False, False, 0)

        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.set_margin_start(12)
        self.progress.set_margin_end(12)
        self.progress.set_margin_top(4)
        self.progress.set_margin_bottom(8)
        self.progress.set_show_text(True)
        root.pack_start(self.progress, False, False, 0)

        # Log view
        scroller = Gtk.ScrolledWindow()
        scroller.set_margin_start(10)
        scroller.set_margin_end(10)
        scroller.set_margin_bottom(10)
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        root.pack_start(scroller, True, True, 0)

        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.07, 0.07, 0.07, 1))
        self.textview.modify_font(Pango.FontDescription("Monospace 10"))
        scroller.add(self.textview)

        self.buffer = self.textview.get_buffer()
        self.tag_stage = self.buffer.create_tag("stage", foreground="#ffd93d")
        self.tag_ok = self.buffer.create_tag("ok", foreground="#6bff6b")
        self.tag_err = self.buffer.create_tag("err", foreground="#ff6b6b")
        self.tag_info = self.buffer.create_tag("info", foreground="#7fb0ff")
        self.tag_default = self.buffer.create_tag("default", foreground="#dddddd")

    # -- logging helpers -------------------------------------------------
    def log_write(self, text, tag_name=None):
        def _write():
            end_iter = self.buffer.get_end_iter()
            tag = getattr(self, f"tag_{tag_name}", self.tag_default) if tag_name else self.tag_default
            self.buffer.insert_with_tags(end_iter, text, tag)
            if self.autoscroll_chk.get_active():
                end_iter = self.buffer.get_end_iter()
                mark = self.buffer.create_mark(None, end_iter, False)
                self.textview.scroll_mark_onscreen(mark)
            return False
        GLib.idle_add(_write)

    def save_log(self, _btn=None):
        start, end = self.buffer.get_bounds()
        content = self.buffer.get_text(start, end, True)
        if not content.strip():
            self._show_dialog(Gtk.MessageType.INFO, "Save Log", "There's nothing to save yet.")
            return

        dialog = Gtk.FileChooserDialog(
            title="Save Log", parent=self, action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK,
        )
        dialog.set_current_name("ubuntu-update-log.txt")
        dialog.set_do_overwrite_confirmation(True)
        response = dialog.run()
        path = dialog.get_filename() if response == Gtk.ResponseType.OK else None
        dialog.destroy()

        if not path:
            return
        try:
            with open(path, "w") as f:
                f.write(content)
        except OSError as e:
            self._show_dialog(Gtk.MessageType.ERROR, "Save Log", f"Could not save log:\n{e}")

    def _show_dialog(self, msg_type, title, text):
        dialog = Gtk.MessageDialog(
            transient_for=self, flags=0, message_type=msg_type,
            buttons=Gtk.ButtonsType.OK, text=title,
        )
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()

    def _ask_yes_no(self, title, text):
        dialog = Gtk.MessageDialog(
            transient_for=self, flags=0, message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO, text=title,
        )
        dialog.format_secondary_text(text)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    # -- window lifecycle -------------------------------------------------
    def on_close(self, *_args):
        if self.running:
            if not self._ask_yes_no(
                "Update in progress",
                "An update is still running. Cancel it and quit?",
            ):
                return True  # block the close
            self.cancel_update()
        self._cleanup_askpass()
        return False  # allow close

    def _cleanup_askpass(self):
        if self.askpass_path and os.path.exists(self.askpass_path):
            try:
                os.remove(self.askpass_path)
            except OSError:
                pass
            self.askpass_path = None

    # -- timer -------------------------------------------------
    def _tick_timer(self):
        if not self.running or self.start_time is None:
            return False
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        self.timer_label.set_text(f"Elapsed: {mins:02d}:{secs:02d}")
        return True  # keep the GLib timeout going

    # -- update flow -------------------------------------------------
    def start_update(self, _btn=None):
        if self.running:
            return
        self.running = True
        self.cancelled = False
        self.start_time = time.time()
        self.run_btn.set_sensitive(False)
        self.run_btn.set_label("Running...")
        self.cancel_btn.set_sensitive(True)
        self.status_label.set_text("Starting...")
        self.progress.set_fraction(0.0)
        self.progress.set_text("")
        self.buffer.set_text("")

        self.askpass_path = make_askpass_script()
        if self.askpass_path is None:
            self._show_dialog(
                Gtk.MessageType.WARNING,
                "zenity not found",
                "zenity is not installed, so sudo password prompts may appear "
                "in the terminal instead of a graphical dialog.\n\n"
                "Install it with: sudo apt install zenity",
            )

        GLib.timeout_add(1000, self._tick_timer)
        threading.Thread(target=self._run_all_stages, daemon=True).start()

    def cancel_update(self, _btn=None):
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
        self.cancel_btn.set_sensitive(False)

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

    def _set_progress(self, i):
        def _update():
            self.progress.set_fraction(i / len(STAGES))
            self.progress.set_text(f"Step {i}/{len(STAGES)}")
            return False
        GLib.idle_add(_update)

    def _set_status(self, text):
        def _update():
            self.status_label.set_text(text)
            return False
        GLib.idle_add(_update)

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
            self._set_progress(i - 1)
            self._set_status(f"Step {i}/{len(STAGES)}")

            if cmd is None:
                self.log_write(f"\n[+] {label}\n", "stage")
                self.log_write("[i] Skipped — tool not installed.\n", "info")
                self._set_progress(i)
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

        self._set_progress(len(STAGES) if all_ok else int(self.progress.get_fraction() * len(STAGES)))

        if self.cancelled:
            self.log_write("\n=== UPDATE CANCELLED ===\n", "err")
            self._set_status("Cancelled")
        elif all_ok:
            self.log_write("\n=== UPDATE COMPLETE! ===\n", "ok")
            self._set_status("Done")
        else:
            self.log_write("\n=== UPDATE FINISHED WITH ERRORS ===\n", "err")
            self._set_status("Finished with errors")

        self._cleanup_askpass()

        def _finish():
            self.running = False
            self.proc = None
            self.run_btn.set_sensitive(True)
            self.run_btn.set_label("▶  Run Update")
            self.cancel_btn.set_sensitive(False)
            return False
        GLib.idle_add(_finish)


def main():
    win = UpdateWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
