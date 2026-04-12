from __future__ import annotations

from .models import RoutedMatch
from .registry import ToolRegistry


class ToolRouter:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def route(self, prompt: str, limit: int = 5) -> list[RoutedMatch]:
        tokens = {
            token.lower()
            for token in prompt.replace('/', ' ').replace('-', ' ').split()
            if token
        }
        if not tokens:
            return []

        scored: list[RoutedMatch] = []
        for tool in self._registry.list_all():
            score = self._score(tokens, tool.name, tool.description)
            if score > 0:
                scored.append(RoutedMatch(name=tool.name, score=score, description=tool.description))

        scored.sort(key=lambda m: (-m.score, m.name))
        return scored[:limit]

    @staticmethod
    def _score(tokens: set[str], name: str, description: str) -> int:
        haystacks = [name.lower(), description.lower()]
        score = 0
        for token in tokens:
            if any(token in h for h in haystacks):
                score += 1
        return score
