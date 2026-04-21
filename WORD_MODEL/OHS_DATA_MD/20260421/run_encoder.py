# -*- coding: utf-8 -*-
"""CLI wrapper that reuses encoder.py decoder functions (headless, no Tk)."""
import sys
import os
from pathlib import Path

ENC_DIR = "/home/user/ASAS/WORD_MODEL/OHS_DATA_MD/20260421"
sys.path.insert(0, ENC_DIR)

# Stub tkinter so import of encoder.py succeeds in headless environment
import types
_tk = types.ModuleType("tkinter")
_tk.Tk = object
_tk.StringVar = object
_tk.TclError = Exception
_tk.END = "end"
sys.modules["tkinter"] = _tk
for sub in ("ttk", "filedialog", "scrolledtext", "messagebox"):
    sys.modules[f"tkinter.{sub}"] = types.ModuleType(f"tkinter.{sub}")

import encoder  # noqa: E402

def log(msg):
    print(msg, flush=True)

def main(src, dst_dir):
    src = Path(src)
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    header, b64_text = encoder.parse_text_file(src, log)
    data = encoder.decode_base64(b64_text, log)

    expected_size = int(header.get("size", 0))
    if expected_size and len(data) != expected_size:
        log(f"    [WARN] size mismatch: expected {expected_size:,} / actual {len(data):,}")

    expected_sha = header.get("sha256", "")
    if expected_sha:
        encoder.verify_hash(data, expected_sha, log)

    out_path = dst_dir / header["filename"]
    encoder.write_binary(data, out_path, log)
    log(f"\n[OK] Restored: {out_path} ({len(data):,} bytes)")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
