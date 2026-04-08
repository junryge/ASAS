"""Tool Router - prompt to tool matching via token scoring."""

from __future__ import annotations

import re

from .models import RoutedMatch
from .registry import ToolRegistry


class ToolRouter:
    """Routes prompts to matching tools using token overlap scoring."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def route(self, prompt: str, limit: int = 5) -> list[RoutedMatch]:
        """Match a prompt to the best tools.

        Algorithm:
        1. Tokenize prompt by /, -, whitespace
        2. For each tool, count token overlap with name + description
        3. Sort by (-score, name) and return top results
        """
        tokens = self._tokenize(prompt)
        if not tokens:
            return []

        scored: list[tuple[int, str, str]] = []
        for tool in self.registry.list_all():
            score = self._score(tokens, tool.name, tool.description)
            scored.append((score, tool.name, tool.description))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [
            RoutedMatch(name=name, score=score, description=desc)
            for score, name, desc in scored[:limit]
            if score > 0
        ]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Split text into lowercase tokens."""
        parts = re.split(r'[/\-\s]+', text.lower())
        return {p for p in parts if p}

    @staticmethod
    def _score(tokens: set[str], name: str, description: str) -> int:
        """Count how many tokens appear in name or description."""
        target = f"{name.lower()} {description.lower()}"
        return sum(1 for t in tokens if t in target)
