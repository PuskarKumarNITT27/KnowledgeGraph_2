"""
evaluation/evaluator.py

Core KG evaluation engine.

Two modes:
  A) EXTRACTION mode  — run all templates, dump every triple the graph contains.
                        Useful when you have NO ground truth yet.

  B) SCORING mode     — compare graph answers against a ground truth CSV.
                        Computes Precision, Recall, F1, Hits@K, MRR.

Usage (from UI):
    from evaluation.evaluator import run_extraction, run_scoring
"""

import os
import io
import math
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from utils.query_extractor import _get_driver
from evaluation.eval_templates import EVAL_TEMPLATES


# ── Public API ────────────────────────────────────────────────────────────────

def run_extraction(
    template_ids: Optional[List[str]] = None,
) -> Tuple[bool, Dict]:
    """
    Mode A — fetch all triples from the graph for the given templates.

    Args:
        template_ids: list of template_id strings to run.
                      Pass None to run ALL templates.

    Returns:
        (True, {
            "results": [
                {
                  "template_id": ...,
                  "pattern": ...,
                  "hop_type": ...,
                  "triples": [(subject, predicate, object), ...]
                },
                ...
            ],
            "total_triples": int
        })
        (False, error_string)
    """
    templates = _select_templates(template_ids)
    if not templates:
        return False, "No matching templates found."

    try:
        driver = _get_driver()
        output = []
        total = 0

        with driver.session() as session:
            for tmpl in templates:
                triples = _run_template_query(session, tmpl)
                output.append({
                    "template_id": tmpl["template_id"],
                    "pattern":     tmpl["pattern"],
                    "hop_type":    tmpl["hop_type"],
                    "triples":     triples,
                })
                total += len(triples)

        driver.close()
        return True, {"results": output, "total_triples": total}

    except Exception as e:
        return False, f"Extraction failed: {e}"


def run_scoring(
    ground_truth: List[Dict],
    template_ids: Optional[List[str]] = None,
    hits_k: int = 10,
) -> Tuple[bool, Dict]:
    """
    Mode B — score the graph against ground truth triples.

    Args:
        ground_truth: list of dicts with keys:
                        template_id, subject, object
                      (predicate is optional — matched by template_id)
        template_ids: which templates to score (None = all)
        hits_k:       K value for Hits@K metric

    Returns:
        (True, {
            "per_template": [...],   per-template metrics
            "overall":      {...},   macro-averaged across templates
        })
        (False, error_string)
    """
    if not ground_truth:
        return False, "Ground truth list is empty."

    templates = _select_templates(template_ids)
    if not templates:
        return False, "No matching templates found."

    try:
        driver = _get_driver()
        per_template = []
        all_precisions, all_recalls, all_f1s = [], [], []
        all_mrr, all_hits = [], []

        with driver.session() as session:
            for tmpl in templates:
                tid = tmpl["template_id"]

                # Graph predictions for this template
                triples = _run_template_query(session, tmpl)
                predicted = set(
                    _normalise(t["object"]) for t in triples
                )
                predicted_ranked = [
                    _normalise(t["object"]) for t in triples
                ]

                # Ground truth for this template
                gt_for_tmpl = [
                    g for g in ground_truth
                    if g.get("template_id") == tid
                ]
                if not gt_for_tmpl:
                    continue

                expected = set(
                    _normalise(g["object"]) for g in gt_for_tmpl
                )

                # Core metrics
                tp = len(predicted & expected)
                precision = tp / len(predicted) if predicted else 0.0
                recall    = tp / len(expected)  if expected  else 0.0
                f1 = (2 * precision * recall / (precision + recall)
                      if (precision + recall) > 0 else 0.0)

                # Hits@K
                top_k = set(predicted_ranked[:hits_k])
                hits_at_k = len(top_k & expected) / len(expected) if expected else 0.0

                # MRR (mean reciprocal rank)
                mrr = _compute_mrr(predicted_ranked, expected)

                result = {
                    "template_id":   tid,
                    "pattern":       tmpl["pattern"],
                    "hop_type":      tmpl["hop_type"],
                    "ground_truth_count":  len(expected),
                    "predicted_count":     len(predicted),
                    "true_positives":      tp,
                    "precision":           round(precision, 4),
                    "recall":              round(recall,    4),
                    "f1":                  round(f1,        4),
                    f"hits@{hits_k}":      round(hits_at_k, 4),
                    "mrr":                 round(mrr,       4),
                    "correct_answers":     sorted(predicted & expected),
                    "missing_answers":     sorted(expected - predicted),
                    "extra_answers":       sorted(predicted - expected),
                }
                per_template.append(result)
                all_precisions.append(precision)
                all_recalls.append(recall)
                all_f1s.append(f1)
                all_mrr.append(mrr)
                all_hits.append(hits_at_k)

        driver.close()

        if not per_template:
            return False, "No templates matched any ground truth entries."

        overall = {
            "templates_evaluated":    len(per_template),
            "macro_precision":        round(_mean(all_precisions), 4),
            "macro_recall":           round(_mean(all_recalls),    4),
            "macro_f1":               round(_mean(all_f1s),        4),
            f"macro_hits@{hits_k}":   round(_mean(all_hits),       4),
            "macro_mrr":              round(_mean(all_mrr),        4),
        }

        return True, {"per_template": per_template, "overall": overall}

    except Exception as e:
        return False, f"Scoring failed: {e}"


def ground_truth_from_csv(csv_bytes: bytes) -> Tuple[bool, List[Dict]]:
    """
    Parse a ground truth CSV file.

    Expected columns (flexible — any order, case-insensitive):
      template_id | subject | object

    Returns (True, list_of_dicts) or (False, error_msg).
    """
    try:
        import pandas as pd
        df = pd.read_csv(io.BytesIO(csv_bytes))
        df.columns = [c.strip().lower() for c in df.columns]

        required = {"template_id", "subject", "object"}
        missing_cols = required - set(df.columns)
        if missing_cols:
            return False, (
                f"CSV is missing columns: {missing_cols}. "
                f"Found: {list(df.columns)}"
            )

        df = df.dropna(subset=["template_id", "object"])
        records = df[["template_id", "subject", "object"]].to_dict("records")
        return True, records

    except Exception as e:
        return False, f"Could not parse CSV: {e}"


def export_triples_csv(results: List[Dict]) -> bytes:
    """Convert extraction results to a downloadable CSV bytes."""
    try:
        import pandas as pd
        rows = []
        for r in results:
            for (s, p, o) in r["triples"]:
                rows.append({
                    "template_id": r["template_id"],
                    "hop_type":    r["hop_type"],
                    "pattern":     r["pattern"],
                    "subject":     s,
                    "predicate":   p,
                    "object":      o,
                })
        df = pd.DataFrame(rows)
        return df.to_csv(index=False).encode()
    except Exception:
        return b""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _select_templates(template_ids):
    if template_ids is None:
        return EVAL_TEMPLATES
    return [t for t in EVAL_TEMPLATES if t["template_id"] in template_ids]


def _run_template_query(session, tmpl: Dict) -> List[Dict]:
    """Execute the template Cypher and return list of {subject, predicate, object}."""
    try:
        result = session.run(tmpl["cypher"])
        rows = []
        for rec in result:
            rows.append({
                "subject":   str(rec.get("subject", "") or ""),
                "predicate": str(rec.get("predicate", "") or ""),
                "object":    str(rec.get("object", "") or ""),
            })
        return rows
    except Exception as e:
        return []


def _normalise(text: str) -> str:
    """Lowercase + strip for fuzzy matching."""
    return str(text).lower().strip()


def _compute_mrr(ranked: List[str], expected: set) -> float:
    """Mean Reciprocal Rank — first hit position in the ranked list."""
    for i, item in enumerate(ranked, start=1):
        if _normalise(item) in expected:
            return 1.0 / i
    return 0.0


def _mean(lst: List[float]) -> float:
    return sum(lst) / len(lst) if lst else 0.0