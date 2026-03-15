#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
코드 어시스턴트 패널 - 오른쪽 사이드바
임의의 폴더/파일을 열어 AI 코드 분석을 받을 수 있는 패널
"""

import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFileDialog, QFrame,
    QGridLayout
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from .theme import COLORS
from .code_editor import CodeEditorWidget

logger = logging.getLogger(__name__)

# 파일 트리에서 제외할 디렉터리
IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".idea", ".vscode", ".mypy_cache", ".pytest_cache",
    "dist", "build", ".egg-info", ".tox", ".nox"
}

# 지원 파일 확장자 → 언어 매핑
EXT_LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".java": "java", ".cpp": "cpp", ".c": "c", ".go": "go",
    ".rs": "rust", ".sql": "sql", ".html": "html", ".css": "css",
    ".sh": "bash", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".xml": "html", ".md": "html", ".txt": "python",
}

# 대용량 파일 제한 (100KB)
MAX_FILE_SIZE = 100 * 1024


class CodeAssistantPanel(QWidget):
    """코드 어시스턴트 오른쪽 사이드바"""

    # 시그널
    analysis_requested = Signal(str, str, str)  # (action_key, code_text, file_path)
    context_injected = Signal(str, str)          # (file_path, code_text)

    QUICK_ACTIONS = [
        ("코드 설명", "explain", "코드의 전체 구조와 동작을 설명"),
        ("버그 찾기", "find_bugs", "잠재적 버그와 문제점 분석"),
        ("개선 제안", "suggest_improvements", "코드 품질 개선 제안"),
        ("테스트 생성", "generate_tests", "단위 테스트 자동 생성"),
        ("독스트링", "add_docstrings", "함수/클래스 문서화 추가"),
        ("리팩토링", "refactor", "코드 구조 개선 및 리팩토링"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_dir = ""
        self.current_file = ""
        self.setFixedWidth(380)
        self.setStyleSheet(f"""
            background-color: {COLORS['darker']};
            border-left: 1px solid {COLORS['border']};
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # === 타이틀바 ===
        title_bar = QHBoxLayout()
        title_bar.setSpacing(8)

        title_icon = QLabel("🔍")
        title_icon.setStyleSheet("font-size: 18px; background: transparent; border: none;")
        title_bar.addWidget(title_icon)

        title_label = QLabel("Code Assistant")
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {COLORS['teal']};
            background: transparent;
            border: none;
        """)
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_muted']};
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['surface']};
                color: {COLORS['red']};
            }}
        """)
        close_btn.clicked.connect(lambda: self.setVisible(False))
        title_bar.addWidget(close_btn)

        layout.addLayout(title_bar)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px; border: none;")
        layout.addWidget(line)

        # === 폴더 열기 ===
        folder_bar = QHBoxLayout()
        folder_bar.setSpacing(6)

        open_btn = QPushButton("📂 폴더 열기")
        open_btn.setFixedHeight(32)
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 0 14px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
                border-color: {COLORS['teal']};
            }}
        """)
        open_btn.clicked.connect(self._open_folder)
        folder_bar.addWidget(open_btn)

        self.path_label = QLabel("폴더를 선택하세요")
        self.path_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: 11px;
            background: transparent;
            border: none;
        """)
        self.path_label.setWordWrap(True)
        folder_bar.addWidget(self.path_label, stretch=1)

        layout.addLayout(folder_bar)

        # === 메인 스플리터: 파일 트리 + 코드 뷰어 ===
        splitter = QSplitter(Qt.Vertical)

        # 파일 트리
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(4)

        tree_label = QLabel("파일 탐색기")
        tree_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 700;
            color: {COLORS['text_muted']};
            letter-spacing: 1px;
            padding: 4px 0 2px 0;
            background: transparent;
            border: none;
        """)
        tree_layout.addWidget(tree_label)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["파일명", "크기"])
        self.file_tree.setColumnWidth(0, 220)
        self.file_tree.itemClicked.connect(self._on_file_click)
        tree_layout.addWidget(self.file_tree)

        splitter.addWidget(tree_container)

        # 코드 뷰어
        viewer_container = QWidget()
        viewer_layout = QVBoxLayout(viewer_container)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(4)

        self.file_info_label = QLabel("파일을 선택하세요")
        self.file_info_label.setStyleSheet(f"""
            font-size: 11px;
            color: {COLORS['teal']};
            font-weight: 600;
            padding: 2px 0;
            background: transparent;
            border: none;
        """)
        viewer_layout.addWidget(self.file_info_label)

        self.code_viewer = CodeEditorWidget()
        self.code_viewer.editor.setReadOnly(True)
        viewer_layout.addWidget(self.code_viewer)

        splitter.addWidget(viewer_container)
        splitter.setSizes([200, 300])

        layout.addWidget(splitter, stretch=1)

        # === 퀵 액션 ===
        actions_label = QLabel("QUICK ACTIONS")
        actions_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 700;
            color: {COLORS['text_muted']};
            letter-spacing: 1px;
            padding: 6px 0 4px 0;
            background: transparent;
            border: none;
        """)
        layout.addWidget(actions_label)

        actions_grid = QGridLayout()
        actions_grid.setSpacing(6)

        for i, (label, action_key, tooltip) in enumerate(self.QUICK_ACTIONS):
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.setFixedHeight(32)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['surface']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0 8px;
                }}
                QPushButton:hover {{
                    background: {COLORS['surface_hover']};
                    color: {COLORS['teal']};
                    border-color: {COLORS['teal']};
                }}
                QPushButton:pressed {{
                    background: rgba(45, 212, 191, 0.15);
                }}
            """)
            btn.clicked.connect(lambda checked, a=action_key: self._on_action_click(a))
            row, col = divmod(i, 2)
            actions_grid.addWidget(btn, row, col)

        layout.addLayout(actions_grid)

        # === 채팅에 전송 버튼 ===
        send_btn = QPushButton("💬 채팅에 코드 전송")
        send_btn.setFixedHeight(38)
        send_btn.setObjectName("primaryBtn")
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['teal']};
                color: {COLORS['darkest']};
                border: none;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #5eead4;
            }}
            QPushButton:pressed {{
                background-color: #14b8a6;
            }}
        """)
        send_btn.clicked.connect(self._on_send_to_chat)
        layout.addWidget(send_btn)

    # === 폴더 열기 ===

    def _open_folder(self):
        """QFileDialog로 폴더 선택"""
        directory = QFileDialog.getExistingDirectory(
            self, "프로젝트 폴더 선택", self.current_dir or os.path.expanduser("~")
        )
        if directory:
            self.open_directory(directory)

    def open_directory(self, path: str):
        """지정된 디렉터리의 파일 트리 구성"""
        self.current_dir = path
        folder_name = os.path.basename(path)
        self.path_label.setText(f"📁 {folder_name}")
        self.path_label.setToolTip(path)
        self._populate_tree(path)

    def _populate_tree(self, root_path: str):
        """디렉터리를 재귀 탐색하여 트리 구성"""
        self.file_tree.clear()

        try:
            self._add_dir_items(self.file_tree, root_path, root_path, depth=0)
            self.file_tree.expandToDepth(0)
        except Exception as e:
            logger.error(f"파일 트리 구성 오류: {e}")

    def _add_dir_items(self, parent, dir_path: str, root_path: str, depth: int):
        """재귀적으로 디렉터리 아이템 추가 (최대 깊이 4)"""
        if depth > 4:
            return

        try:
            entries = sorted(os.listdir(dir_path))
        except PermissionError:
            return

        # 디렉터리 먼저
        dirs = [e for e in entries if os.path.isdir(os.path.join(dir_path, e)) and e not in IGNORED_DIRS and not e.startswith(".")]
        files = [e for e in entries if os.path.isfile(os.path.join(dir_path, e)) and not e.startswith(".")]

        for d in dirs:
            full_path = os.path.join(dir_path, d)
            rel_path = os.path.relpath(full_path, root_path)
            item = QTreeWidgetItem(["📁 " + d, ""])
            item.setData(0, Qt.UserRole, {"type": "dir", "path": full_path})

            if isinstance(parent, QTreeWidget):
                parent.addTopLevelItem(item)
            else:
                parent.addChild(item)

            self._add_dir_items(item, full_path, root_path, depth + 1)

        for f in files:
            full_path = os.path.join(dir_path, f)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0

            item = QTreeWidgetItem(["📄 " + f, self._format_size(size)])
            item.setData(0, Qt.UserRole, {"type": "file", "path": full_path})

            if isinstance(parent, QTreeWidget):
                parent.addTopLevelItem(item)
            else:
                parent.addChild(item)

    # === 파일 클릭 ===

    def _on_file_click(self, item, column):
        """파일 클릭 → 코드 뷰어에 표시"""
        data = item.data(0, Qt.UserRole)
        if not data or data["type"] != "file":
            return

        file_path = data["path"]
        self.current_file = file_path
        file_name = os.path.basename(file_path)

        try:
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                self.file_info_label.setText(f"⚠️ {file_name} ({self._format_size(file_size)}) - 100KB 초과, 일부만 표시")
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(MAX_FILE_SIZE)
                content += "\n\n# ... (파일 크기 초과로 잘림) ..."
            else:
                self.file_info_label.setText(f"📄 {file_name} ({self._format_size(file_size)})")
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
        except Exception as e:
            self.file_info_label.setText(f"❌ 읽기 실패: {file_name}")
            content = f"# 파일을 읽을 수 없습니다: {e}"

        self.code_viewer.set_code(content)

        # 언어 자동 감지
        ext = os.path.splitext(file_path)[1].lower()
        lang = EXT_LANG_MAP.get(ext, "python")
        self.code_viewer.set_language(lang)

    # === 퀵 액션 ===

    def _on_action_click(self, action_key: str):
        """퀵 액션 버튼 클릭"""
        code = self._get_code()
        if not code.strip():
            return
        self.analysis_requested.emit(action_key, code, self.current_file)

    def _on_send_to_chat(self):
        """코드를 채팅에 전송"""
        code = self._get_code()
        if not code.strip():
            return
        self.context_injected.emit(self.current_file, code)

    def _get_code(self) -> str:
        """코드 뷰어의 선택 텍스트 또는 전체 텍스트 반환"""
        cursor = self.code_viewer.editor.textCursor()
        if cursor.hasSelection():
            return cursor.selectedText().replace("\u2029", "\n")
        return self.code_viewer.get_code()

    # === 유틸 ===

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
