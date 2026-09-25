#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import pty
import select
import signal
import struct
import subprocess
import tempfile
import termios
import time


OSC10_QUERY_ST = b"\x1b]10;?\x1b\\"
OSC11_QUERY_ST = b"\x1b]11;?\x1b\\"
OSC10_RESPONSE = b"\x1b]10;rgb:f5f5/f5f5/f5f5\x1b\\"
OSC11_RESPONSE = b"\x1b]11;rgb:1e1e/1e1e/1e1e\x1b\\"
DA1_RESPONSE = b"\x1b[?61;4;6;7;14;21;22;23;24;28;32;42;52c"
DA2_RESPONSE = b"\x1b[>0;10;1c"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tmux", required=True)
    parser.add_argument("--escape-time", type=int, required=True)
    parser.add_argument("--split", type=int, required=True)
    parser.add_argument("--delay-ms", type=float, required=True)
    parser.add_argument("--capture-seconds", type=float, default=1.2)
    return parser.parse_args()


def send_once(master, output, needle, response, state, name):
    if not state[name] and needle in output:
        os.write(master, response)
        state[name] = True


def main():
    args = parse_args()
    if args.split < 0 or args.split > len(OSC11_RESPONSE):
        raise SystemExit(f"split must be between 0 and {len(OSC11_RESPONSE)}")

    script_dir = pathlib.Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="tmux-query-split-") as temp:
        temp_path = pathlib.Path(temp)
        capture_path = temp_path / "pane-input.bin"
        config_path = temp_path / "tmux.conf"
        config_path.write_text(
            f"set -sg escape-time {args.escape_time}\n"
            "set -g status off\n",
            encoding="ascii",
        )

        master, slave = pty.openpty()
        termios.tcsetwinsize(slave, (24, 80))
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env.pop("TMUX", None)
        socket_name = f"query-split-{os.getpid()}-{time.time_ns()}"
        command = [
            args.tmux,
            "-L",
            socket_name,
            "-f",
            str(config_path),
            "new-session",
            "python3",
            str(script_dir / "pane_capture.py"),
            str(capture_path),
            str(args.capture_seconds),
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
        state = {"osc10": False, "osc11": False, "da1": False, "da2": False}
        split_sent_at = None
        deadline = time.monotonic() + 5
        try:
            while time.monotonic() < deadline and proc.poll() is None:
                readable, _, _ = select.select([master], [], [], 0.01)
                if readable:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output.extend(chunk)

                send_once(master, output, b"\x1b[c", DA1_RESPONSE, state, "da1")
                send_once(master, output, b"\x1b[>c", DA2_RESPONSE, state, "da2")
                send_once(master, output, OSC10_QUERY_ST, OSC10_RESPONSE, state, "osc10")

                if not state["osc11"] and OSC11_QUERY_ST in output:
                    ready_deadline = time.monotonic() + 1
                    while not capture_path.with_suffix(".bin.ready").exists() and time.monotonic() < ready_deadline:
                        time.sleep(0.001)
                    prefix = OSC11_RESPONSE[: args.split]
                    suffix = OSC11_RESPONSE[args.split :]
                    if prefix:
                        os.write(master, prefix)
                    split_sent_at = time.monotonic()
                    if args.delay_ms:
                        time.sleep(args.delay_ms / 1000)
                    if suffix:
                        os.write(master, suffix)
                    state["osc11"] = True

            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=1)
        finally:
            os.close(master)
            subprocess.run(
                [args.tmux, "-L", socket_name, "kill-server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

        captured = capture_path.read_bytes() if capture_path.exists() else b""
        print(
            json.dumps(
                {
                    "tmux": subprocess.check_output([args.tmux, "-V"], text=True).strip(),
                    "escape_time_ms": args.escape_time,
                    "split": args.split,
                    "delay_ms": args.delay_ms,
                    "response_length": len(OSC11_RESPONSE),
                    "queries_seen": state,
                    "split_sent": split_sent_at is not None,
                    "captured_hex": captured.hex(),
                    "captured_text": captured.decode("utf-8", "backslashreplace"),
                    "leaked": bool(captured),
                    "tmux_exit_code": proc.returncode,
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
