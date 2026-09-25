#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import pty
import select
import signal
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", required=True)
    parser.add_argument("--delay-ms", type=float, default=350)
    parser.add_argument("--window-seconds", type=float, default=2.5)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="codex-query-split-") as temp:
        root = pathlib.Path(temp)
        work = root / "untrusted-work"
        log = root / "log"
        work.mkdir()
        log.mkdir()

        master, slave = pty.openpty()
        env = os.environ.copy()
        env.pop("CODEX_TUI_DISABLE_KEYBOARD_ENHANCEMENT", None)
        env["TERM"] = "xterm-256color"
        command = [
            args.codex,
            "--no-alt-screen",
            "-c",
            f"log_dir={log}",
            "-C",
            str(work),
        ]
        proc = subprocess.Popen(
            command,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env=env,
            close_fds=True,
            start_new_session=True,
        )
        os.close(slave)

        output = bytearray()
        sent = {"cursor": False, "colors": False, "keyboard": False, "da": False}
        start = time.monotonic()
        try:
            while time.monotonic() - start < args.window_seconds:
                readable, _, _ = select.select([master], [], [], 0.02)
                if readable:
                    try:
                        data = os.read(master, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    output.extend(data)
                    if not sent["cursor"] and b"\x1b[6n" in output:
                        os.write(master, b"\x1b[9;1R")
                        sent["cursor"] = True
                    if not sent["colors"] and b"\x1b]10;?" in output and b"\x1b]11;?" in output:
                        os.write(master, b"\x1b]10;rgb:f5f5/f5f5/f5f5\x1b\\")
                        os.write(master, b"\x1b]11;rgb:1e1e/1e1e/1e1e\x1b\\")
                        sent["colors"] = True
                    if not sent["keyboard"] and b"\x1b[?u" in output:
                        os.write(master, b"\x1b[?7u")
                        sent["keyboard"] = True
                    if not sent["da"] and b"\x1b[c" in output:
                        os.write(master, b"\x1b[?61;4;6;7;14;21;2")
                        time.sleep(args.delay_ms / 1000)
                        os.write(master, b"2;23;24;28;32;42;52c")
                        sent["da"] = True
                if proc.poll() is not None:
                    break

            survived = proc.poll() is None
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=2)
            os.close(master)

        startup_lines = []
        log_path = log / "codex-tui.log"
        if log_path.exists():
            startup_lines = [
                line.rstrip()
                for line in log_path.read_text(errors="replace").splitlines()
                if "terminal startup probes completed" in line
            ]

        print(
            json.dumps(
                {
                    "codex_version": subprocess.check_output([args.codex, "--version"], text=True).strip(),
                    "delay_ms": args.delay_ms,
                    "sent": sent,
                    "survived_until_harness_end": survived,
                    "exit_code_before_cleanup": None if survived else proc.returncode,
                    "startup_log": startup_lines,
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
