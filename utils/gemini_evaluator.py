"""
utils/gemini_evaluator.py

Minimal Schema Version:
- Uses ONLY node labels + relationship types
- No properties / embeddings
- Safer Cypher generation
"""

import os
import json
import re
from typing import List, Dict, Tuple

from google import genai
from utils.query_extractor import run_neo4j_query, _get_driver


# ── ENV ────────────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


# ── SCHEMA LOADER (MINIMAL) ────────────────────────────────────────────────────

def load_schema_text() -> str:
    """
    Load ONLY:
    - Node labels
    - Relationship types
    """

    try:
        with open("../schema_cache.json", "r") as f:
            schema = json.load(f)

        labels = set()
        rels = set()

        for label in schema.get("labels", []):
            labels.add(label.get("label"))

        for rel in schema.get("relationships", []):
            rels.add(rel.get("type"))

        lines = ["NODE LABELS:"]
        for l in sorted(labels):
            lines.append(f"- {l}")

        lines.append("\nRELATIONSHIPS:")
        for r in sorted(rels):
            lines.append(f"- {r}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error loading schema: {str(e)}"


# ── TYPES ──────────────────────────────────────────────────────────────────────

class ChangeRecord:
    def __init__(
        self,
        question: str,
        expected_answer: str,
        neo4j_answer: str,
        status: str,
        cypher_executed: str = "",
        error_detail: str = "",
    ):
        self.question        = question
        self.expected_answer = expected_answer
        self.neo4j_answer    = neo4j_answer
        self.status          = status
        self.cypher_executed = cypher_executed
        self.error_detail    = error_detail

    def to_dict(self) -> Dict:
        return self.__dict__


# ── GEMINI CALL ────────────────────────────────────────────────────────────────

def _call_gemini(client, prompt: str) -> str:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text.strip()


# ── MAIN PIPELINE ──────────────────────────────────────────────────────────────

def validate_and_update_graph(text_chunk: str) -> Tuple[bool, List[ChangeRecord]]:
    if not GEMINI_API_KEY:
        return False, "GEMINI_API_KEY not set"

    client = genai.Client(api_key=GEMINI_API_KEY)

    qa_pairs = _generate_qa_pairs(client, text_chunk)
    records: List[ChangeRecord] = []

    for qa in qa_pairs:
        question = qa.get("question", "").strip()
        expected = qa.get("answer", "").strip()

        if not question or not expected:
            continue

        neo4j_answer = _query_neo4j_for_answer(client, question)
        is_correct = _answers_match(client, question, expected, neo4j_answer)

        if is_correct:
            records.append(ChangeRecord(
                question, expected, neo4j_answer, "correct"
            ))
        else:
            record = _fix_graph(client, question, expected, neo4j_answer, text_chunk)
            records.append(record)

    return True, records


# ── STEP 1: GENERATE Q&A ───────────────────────────────────────────────────────

def _generate_qa_pairs(client, chunk: str) -> List[Dict]:
    prompt = f"""
Generate up to 5 factual Q&A pairs from the text.

Return ONLY JSON:
[
  {{"question": "...", "answer": "..."}}
]

TEXT:
\"\"\"
{chunk[:6000]}
\"\"\"
"""
    try:
        raw = _call_gemini(client, prompt)
        raw = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)
    except:
        return []


# ── STEP 2: QUERY NEO4J (MINIMAL SCHEMA) ───────────────────────────────────────

def _query_neo4j_for_answer(client, question: str) -> str:
    schema = load_schema_text()

    prompt = f"""
You are a Neo4j Cypher expert.

GRAPH SCHEMA:
{schema}

IMPORTANT:
- Nodes have property: id

STRICT RULES:
1. ALWAYS use WHERE toLower(n.id) CONTAINS
2. NEVER return full graph
3. Return specific answer only
4. Return ONLY Cypher

EXAMPLES:

Q: Who was killed?
MATCH (p)
WHERE toLower(p.id) CONTAINS toLower("hemanti")
RETURN p.id

Q: Where did event happen?
MATCH (e)-[:OCCURRED_IN]->(l)
RETURN e.id, l.id

Question:
{question}
"""

    try:
        cypher = _call_gemini(client, prompt)

        # 🔧 Clean output
        if "```" in cypher:
            cypher = cypher.split("```")[1]
            if cypher.startswith("cypher"):
                cypher = cypher[len("cypher"):]

        cypher = cypher.strip()

        # 🚨 fallback
        if not cypher:
            cypher = "MATCH (n) RETURN n LIMIT 5"

        success, result = run_neo4j_query(cypher)

        if not success:
            return f"[Error: {result}]"
        if not result:
            return "[No result]"

        return _flatten_result(result)

    except Exception as e:
        return f"[Error: {e}]"


# ── STEP 3: CHECK ANSWERS ──────────────────────────────────────────────────────

def _answers_match(client, question: str, expected: str, actual: str) -> bool:
    prompt = f"""
Question: {question}
Expected: {expected}
Actual: {actual}

Are they same? Answer YES or NO only.
"""
    try:
        return _call_gemini(client, prompt).upper().startswith("YES")
    except:
        return False


# ── STEP 4: FIX GRAPH ──────────────────────────────────────────────────────────

def _fix_graph(client, question, expected, actual, chunk) -> ChangeRecord:
    schema = load_schema_text()

    prompt = f"""
You are a Neo4j repair assistant.

GRAPH SCHEMA:
{schema}

RULES:
- Use MERGE
- Use property 'id'
- Use only given relationships

Question: {question}
Expected: {expected}
Graph: {actual}

TEXT:
{chunk[:2000]}

Return ONLY Cypher
"""

    try:
        cypher = _call_gemini(client, prompt)

        if "```" in cypher:
            cypher = cypher.split("```")[1]
            if cypher.startswith("cypher"):
                cypher = cypher[len("cypher"):]

        cypher = cypher.strip()

        if not cypher:
            return ChangeRecord(question, expected, actual, "error", "", "Empty Cypher")

        success, result = _execute_write_query(cypher)

        return ChangeRecord(
            question,
            expected,
            actual,
            "updated" if success else "error",
            cypher,
            "" if success else result,
        )

    except Exception as e:
        return ChangeRecord(question, expected, actual, "error", "", str(e))


# ── EXECUTE WRITE ──────────────────────────────────────────────────────────────

def _execute_write_query(cypher: str) -> Tuple[bool, str]:
    try:
        driver = _get_driver()
        with driver.session() as session:
            session.run(cypher)
        driver.close()
        return True, "OK"
    except Exception as e:
        return False, str(e)


# ── FORMAT RESULT ──────────────────────────────────────────────────────────────

def _flatten_result(result: List[Dict]) -> str:
    parts = []
    for row in result[:5]:
        for k, v in row.items():
            parts.append(f"{k}: {v}")
    return " | ".join(parts) if parts else "[empty]"