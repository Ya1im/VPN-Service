"""Stateful alerting: emit messages only on state transitions."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class AlertState:
    fail_threshold: int = 2
    _fails: dict[str, int] = field(default_factory=dict)
    _alerted: set[str] = field(default_factory=set)

    def update(self, checks: list[Check]) -> list[str]:
        msgs: list[str] = []
        for c in checks:
            if c.ok:
                self._fails[c.name] = 0
                if c.name in self._alerted:
                    self._alerted.discard(c.name)
                    msgs.append(f"✅ {c.name}: восстановлено ({c.detail})")
                continue
            self._fails[c.name] = self._fails.get(c.name, 0) + 1
            if self._fails[c.name] >= self.fail_threshold and c.name not in self._alerted:
                self._alerted.add(c.name)
                msgs.append(f"🚨 {c.name}: {c.detail}")
        return msgs

    def failing(self) -> set[str]:
        return set(self._alerted)


def format_status(checks: list[Check]) -> str:
    return "\n".join(f"{'✅' if c.ok else '❌'} {c.name}: {c.detail}" for c in checks)
