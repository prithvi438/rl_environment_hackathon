"""Adaptive curriculum system for the Customer Support Environment.

Dynamically adjusts difficulty based on recent agent performance,
implementing a sliding-window approach to enable curriculum learning.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Optional

from cs_env.models import Difficulty
from cs_env.tasks.task_registry import TaskDefinition, get_task_by_difficulty

_DIFFICULTY_ORDER = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD, Difficulty.EXPERT]


class CurriculumManager:
    """Manages adaptive difficulty progression."""

    def __init__(
        self,
        window_size: int = 3,
        promote_threshold: float = 0.75,
        demote_threshold: float = 0.30,
        initial_difficulty: Difficulty = Difficulty.EASY,
        seed: Optional[int] = None,
    ) -> None:
        self._window_size = window_size
        self._promote = promote_threshold
        self._demote = demote_threshold
        self._current = initial_difficulty
        self._history: deque[float] = deque(maxlen=window_size)
        self._episodes = 0
        self._promotions = 0
        self._demotions = 0
        self._rng = random.Random(seed)
        self._used: set[str] = set()

    @property
    def current_difficulty(self) -> Difficulty:
        return self._current

    @property
    def episode_count(self) -> int:
        return self._episodes

    @property
    def average_recent_reward(self) -> float:
        return sum(self._history) / len(self._history) if self._history else 0.0

    @property
    def stats(self) -> dict:
        return {
            "current_difficulty": self._current.value,
            "episode_count": self._episodes,
            "avg_reward": round(self.average_recent_reward, 3),
            "history": list(self._history),
            "promotions": self._promotions,
            "demotions": self._demotions,
        }

    def select_task(self, force_difficulty: Optional[Difficulty] = None) -> TaskDefinition:
        diff = force_difficulty or self._current
        candidates = get_task_by_difficulty(diff)
        if not candidates:
            idx = _DIFFICULTY_ORDER.index(diff)
            for off in [1, -1, 2, -2]:
                fi = idx + off
                if 0 <= fi < len(_DIFFICULTY_ORDER):
                    candidates = get_task_by_difficulty(_DIFFICULTY_ORDER[fi])
                    if candidates:
                        break
        if not candidates:
            raise RuntimeError(f"No tasks for {diff}")
        unused = [t for t in candidates if t.task_id not in self._used]
        if unused:
            task = self._rng.choice(unused)
        else:
            self._used -= {t.task_id for t in candidates}
            task = self._rng.choice(candidates)
        self._used.add(task.task_id)
        return task.copy()

    def record_episode_reward(self, reward: float) -> None:
        self._history.append(reward)
        self._episodes += 1
        self._adjust()

    def _adjust(self) -> None:
        if len(self._history) < self._window_size:
            return
        avg = self.average_recent_reward
        idx = _DIFFICULTY_ORDER.index(self._current)
        if avg >= self._promote and idx < len(_DIFFICULTY_ORDER) - 1:
            self._current = _DIFFICULTY_ORDER[idx + 1]
            self._promotions += 1
            self._history.clear()
        elif avg <= self._demote and idx > 0:
            self._current = _DIFFICULTY_ORDER[idx - 1]
            self._demotions += 1
            self._history.clear()

    def reset(self) -> None:
        self._current = Difficulty.EASY
        self._history.clear()
        self._episodes = 0
        self._promotions = 0
        self._demotions = 0
        self._used.clear()
