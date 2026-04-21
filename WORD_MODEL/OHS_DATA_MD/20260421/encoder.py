# -*- coding: utf-8 -*-
"""
encoder.py — Base64 텍스트(.txt) → 원본 압축 파일 복원
- decoder.py가 만든 텍스트 파일을 원래 zip/7z/rar 등으로 복원
- SHA256 해시로 무결성 검증
- 헤더에서 원본 파일명 자동 추출
"""

import os
import re
import base64
import hashlib
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from pathlib import Path


HEADER_RE = {
    'filename': re.compile(r'^#\s*filename:\s*(.+?)\s*$'),
    'size':     re.compile(r'^#\s*size:\s*(\d+)\s*$'),
    'sha256':   re.compile(r'^#\s*sha256:\s*([0-9a-fA-F]{64})\s*$'),
    'version':  re.compile(r'^#\s*FOLDER_ARCHIVE_BASE64\s+(\S+)\s*$'),
}
BEGIN_MARK = "# ---BEGIN---"
END_MARK   = "# ---END---"


def parse_text_file(txt_path: Path, log):
    """텍스트 파일 파싱: 헤더 + Base64 본문 분리"""
    log(f"[1/4] 텍스트 파일 읽는 중: {txt_path.name}")
    header = {}
    body_lines = []
    in_body = False

    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\r\n')

            if line.strip() == BEGIN_MARK:
                in_body = True
                continue
            if line.strip() == END_MARK:
                in_body = False
                break

            if not in_body:
                # 헤더 파싱
                for key, pat in HEADER_RE.items():
                    m = pat.match(line)
                    if m:
                        header[key] = m.group(1)
                        break
            else:
                # 본문 (Base64 데이터)
                if line and not line.startswith('#'):
                    body_lines.append(line)

    if 'filename' not in header:
        raise ValueError("헤더에 filename이 없습니다. 올바른 decoder.py 출력 파일인지 확인하세요.")
    if not body_lines:
        raise ValueError("Base64 본문을 찾을 수 없습니다.")

    log(f"    → 파일명: {header.get('filename')}")
    log(f"    → 원본 크기: {int(header.get('size', 0)):,} bytes")
    log(f"    → 버전: {header.get('version', '?')}")

    b64_text = ''.join(body_lines)
    return header, b64_text


def decode_base64(b64_text: str, log):
    """Base64 → 바이너리 복원"""
    log(f"[2/4] Base64 디코딩 중... ({len(b64_text):,} chars)")
    try:
        data = base64.b64decode(b64_text, validate=True)
    except Exception as e:
        raise ValueError(f"Base64 디코딩 실패: {e}")
    return data


def verify_hash(data: bytes, expected_sha: str, log):
    """SHA256 무결성 검증"""
    log(f"[3/4] SHA256 무결성 검증 중...")
    actual = hashlib.sha256(data).hexdigest()
    if expected_sha and actual.lower() != expected_sha.lower():
        raise ValueError(
            f"해시 불일치! 파일이 손상되었거나 복사 중 일부 누락되었을 수 있습니다.\n"
            f"  기대값: {expected_sha}\n  실제값: {actual}"
        )
    log(f"    → 해시 일치 ✓  ({actual[:16]}...)")
    return actual


def write_binary(data: bytes, dst: Path, log):
    """바이너리 파일로 저장"""
    log(f"[4/4] 바이너리 저장 중: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(data)


class EncoderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Archive Encoder — Base64 텍스트 → ZIP 복원")
        self.root.geometry("760x520")

        self.log_queue = queue.Queue()
        self.worker = None
        self._build_ui()
        self._poll_log()

    def _build_ui(self):
        pad = {'padx': 8, 'pady': 4}

        # 입력 TXT
        frm1 = ttk.Frame(self.root); frm1.pack(fill='x', **pad)
        ttk.Label(frm1, text="TXT 파일:", width=12).pack(side='left')
        self.var_src = tk.StringVar()
        ttk.Entry(frm1, textvariable=self.var_src).pack(side='left', fill='x', expand=True, padx=4)
        ttk.Button(frm1, text="찾기", command=self._browse_src).pack(side='left')
        ttk.Button(frm1, text="클립보드에서", command=self._load_from_clipboard).pack(side='left', padx=4)

        # 출력 폴더
        frm2 = ttk.Frame(self.root); frm2.pack(fill='x', **pad)
        ttk.Label(frm2, text="출력 폴더:", width=12).pack(side='left')
        self.var_dst = tk.StringVar()
        ttk.Entry(frm2, textvariable=self.var_dst).pack(side='left', fill='x', expand=True, padx=4)
        ttk.Button(frm2, text="찾기", command=self._browse_dst).pack(side='left')

        # 실행
        frm3 = ttk.Frame(self.root); frm3.pack(fill='x', **pad)
        self.btn_run = ttk.Button(frm3, text="▶ 인코딩 시작 (TEXT → ZIP)", command=self._start)
        self.btn_run.pack(side='left')
        ttk.Button(frm3, text="로그 지우기", command=lambda: self.log_box.delete('1.0', tk.END)).pack(side='left', padx=6)

        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(fill='x', padx=8, pady=4)

        self.log_box = scrolledtext.ScrolledText(self.root, height=22, font=('Consolas', 10))
        self.log_box.pack(fill='both', expand=True, padx=8, pady=6)

        self.var_status = tk.StringVar(value="대기")
        ttk.Label(self.root, textvariable=self.var_status, relief='sunken', anchor='w').pack(fill='x', side='bottom')

    def _browse_src(self):
        path = filedialog.askopenfilename(
            title="Base64 텍스트 파일 선택",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
        )
        if path:
            self.var_src.set(path)
            if not self.var_dst.get():
                self.var_dst.set(str(Path(path).parent))

    def _browse_dst(self):
        path = filedialog.askdirectory(title="출력 폴더 선택")
        if path:
            self.var_dst.set(path)

    def _load_from_clipboard(self):
        """클립보드의 Base64 텍스트를 임시 파일로 저장해서 사용"""
        try:
            content = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("알림", "클립보드가 비어있습니다.")
            return

        if "FOLDER_ARCHIVE_BASE64" not in content:
            messagebox.showwarning("알림", "클립보드 내용이 올바른 형식이 아닙니다.")
            return

        # 임시 파일 저장
        tmp_dir = Path.home() / ".folder_decoder_tmp"
        tmp_dir.mkdir(exist_ok=True)
        tmp_path = tmp_dir / "from_clipboard.txt"
        tmp_path.write_text(content, encoding='utf-8')
        self.var_src.set(str(tmp_path))
        if not self.var_dst.get():
            self.var_dst.set(str(tmp_dir))
        self._log(f"→ 클립보드에서 로드됨 ({len(content):,}자) → {tmp_path}")

    def _log(self, msg):
        self.log_queue.put(msg)

    def _poll_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_box.insert(tk.END, msg + '\n')
                self.log_box.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log)

    def _start(self):
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("진행 중", "작업 중입니다.")
            return

        src = self.var_src.get().strip()
        dst = self.var_dst.get().strip()
        if not src or not Path(src).is_file():
            messagebox.showerror("오류", "TXT 파일을 선택해주세요.")
            return
        if not dst:
            messagebox.showerror("오류", "출력 폴더를 지정해주세요.")
            return

        self.worker = threading.Thread(
            target=self._run, args=(Path(src), Path(dst)), daemon=True,
        )
        self.btn_run.config(state='disabled')
        self.progress.start(10)
        self.worker.start()

    def _run(self, src: Path, dst_dir: Path):
        try:
            self.var_status.set("인코딩 중...")
            self._log(f"{'='*60}")

            header, b64_text = parse_text_file(src, self._log)
            data = decode_base64(b64_text, self._log)

            # 크기 검증 (부가적)
            expected_size = int(header.get('size', 0))
            if expected_size and len(data) != expected_size:
                self._log(f"    ⚠ 크기 불일치: 기대 {expected_size:,} / 실제 {len(data):,}")

            expected_sha = header.get('sha256', '')
            if expected_sha:
                verify_hash(data, expected_sha, self._log)
            else:
                self._log("[3/4] SHA256 헤더 없음 → 검증 스킵")

            out_path = dst_dir / header['filename']
            # 파일이 이미 있으면 _restored 추가
            if out_path.exists():
                stem = out_path.stem
                suffix = out_path.suffix
                out_path = out_path.with_name(f"{stem}_restored{suffix}")
                self._log(f"    → 동일 파일 존재, 이름 변경: {out_path.name}")

            write_binary(data, out_path, self._log)

            self._log(f"\n✔ 완료")
            self._log(f"  복원 파일:  {out_path}")
            self._log(f"  크기:       {len(data):,} bytes")
            self._log(f"{'='*60}")
            self.var_status.set(f"완료 - {out_path.name} ({len(data):,} bytes)")
        except Exception as e:
            self._log(f"\n✘ 실패: {type(e).__name__}: {e}")
            self.var_status.set(f"실패: {e}")
        finally:
            self.root.after(0, lambda: (self.btn_run.config(state='normal'), self.progress.stop()))


if __name__ == '__main__':
    root = tk.Tk()
    app = EncoderApp(root)
    root.mainloop()
