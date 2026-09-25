#!/usr/bin/env python3
import os
import select
import sys
import termios
import time
import tty


output_path = sys.argv[1]
duration = float(sys.argv[2])
ready_path = f"{output_path}.ready"

fd = sys.stdin.fileno()
previous = termios.tcgetattr(fd)
data = bytearray()
try:
    tty.setraw(fd)
    open(ready_path, "xb").close()
    deadline = time.monotonic() + duration
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        readable, _, _ = select.select([fd], [], [], remaining)
        if not readable:
            break
        chunk = os.read(fd, 4096)
        if not chunk:
            break
        data.extend(chunk)
finally:
    termios.tcsetattr(fd, termios.TCSANOW, previous)

with open(output_path, "wb") as stream:
    stream.write(data)
