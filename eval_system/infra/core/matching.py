"""Matching engine and pair-rule interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import EvalExtraction, MatchResult, PairMatch


class PairRule(Protocol):
  """Defines legal pairs and pair weights for one metric."""

  def is_legal(self, pred: EvalExtraction, gold: EvalExtraction) -> bool:
    """Return whether the pair is legal under this metric."""

  def weight(self, pred: EvalExtraction, gold: EvalExtraction) -> float:
    """Return the pair weight used by the matcher."""


@dataclass
class MaxWeightBipartiteMatcher:
  """Solves one-to-one maximum weight matching with the Hungarian algorithm."""

  def match(
      self,
      preds: list[EvalExtraction],
      golds: list[EvalExtraction],
      pair_rule: PairRule,
      *,
      metric_name: str,
      doc_id: str,
  ) -> MatchResult:
    """Build a weighted bipartite graph and return the optimal match result."""
    if not preds and not golds:
      return MatchResult(metric_name, doc_id, (), (), (), 0, 0, 0)

    edges: dict[tuple[int, int], float] = {}
    for pred_index, pred in enumerate(preds):
      for gold_index, gold in enumerate(golds):
        if pair_rule.is_legal(pred, gold):
          edges[(pred_index, gold_index)] = pair_rule.weight(pred, gold)

    assignment = self._hungarian_maximize(len(preds), len(golds), edges)
    matches = tuple(
        PairMatch(pred_index, gold_index, weight)
        for pred_index, gold_index, weight in assignment
        if weight > 0
    )
    matched_pred_indices = {match.pred_index for match in matches}
    matched_gold_indices = {match.gold_index for match in matches}

    return MatchResult(
        metric_name=metric_name,
        doc_id=doc_id,
        matches=matches,
        unmatched_pred_indices=tuple(
            index for index in range(len(preds)) if index not in matched_pred_indices
        ),
        unmatched_gold_indices=tuple(
            index for index in range(len(golds)) if index not in matched_gold_indices
        ),
        tp=len(matches),
        fp=len(preds) - len(matches),
        fn=len(golds) - len(matches),
    )

  def _hungarian_maximize(
      self,
      pred_count: int,
      gold_count: int,
      edges: dict[tuple[int, int], float],
  ) -> list[tuple[int, int, float]]:
    """Run a max-weight assignment on a rectangular matrix."""
    size = max(pred_count, gold_count)
    if size == 0:
      return []

    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    for (pred_index, gold_index), weight in edges.items():
      matrix[pred_index][gold_index] = weight

    max_weight = max((weight for row in matrix for weight in row), default=0.0)
    cost = [[max_weight - value for value in row] for row in matrix]
    assignment = self._hungarian_minimize(cost)

    result: list[tuple[int, int, float]] = []
    for pred_index, gold_index in assignment:
      if pred_index >= pred_count or gold_index >= gold_count:
        continue
      if (pred_index, gold_index) not in edges:
        continue
      result.append((pred_index, gold_index, edges[(pred_index, gold_index)]))
    return result

  def _hungarian_minimize(self, cost: list[list[float]]) -> list[tuple[int, int]]:
    """Compute the minimum-cost assignment for a square cost matrix."""
    size = len(cost)
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)

    for row in range(1, size + 1):
      p[0] = row
      minv = [float("inf")] * (size + 1)
      used = [False] * (size + 1)
      col0 = 0
      while True:
        used[col0] = True
        row0 = p[col0]
        delta = float("inf")
        col1 = 0
        for col in range(1, size + 1):
          if used[col]:
            continue
          cur = cost[row0 - 1][col - 1] - u[row0] - v[col]
          if cur < minv[col]:
            minv[col] = cur
            way[col] = col0
          if minv[col] < delta:
            delta = minv[col]
            col1 = col
        for col in range(size + 1):
          if used[col]:
            u[p[col]] += delta
            v[col] -= delta
          else:
            minv[col] -= delta
        col0 = col1
        if p[col0] == 0:
          break
      while True:
        col1 = way[col0]
        p[col0] = p[col1]
        col0 = col1
        if col0 == 0:
          break

    assignment: list[tuple[int, int]] = []
    for col in range(1, size + 1):
      if p[col] != 0:
        assignment.append((p[col] - 1, col - 1))
    return assignment
