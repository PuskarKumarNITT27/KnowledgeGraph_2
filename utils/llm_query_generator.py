import os
import json
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def load_schema_from_cache() -> str:
    """Convert your schema_cache.json into clean LLM-readable schema"""
    try:
        with open("../schema_cache.json", "r") as f:
            schema = json.load(f)

        formatted = []

        # ✅ NODES
        formatted.append("NODE LABELS:")
        for label in schema.get("labels", []):
            name = label.get("label", "")

            # extract useful properties (ignore embedding)
            props = [
                p["key"]
                for p in label.get("properties", [])
                if p["key"] != "embedding"
            ]

            if props:
                formatted.append(f"- {name} ({', '.join(props)})")
            else:
                formatted.append(f"- {name}")

        # ✅ RELATIONSHIPS
        formatted.append("\nRELATIONSHIP TYPES:")
        for rel in schema.get("relationships", []):
            rel_type = rel.get("type", "")
            formatted.append(f"- {rel_type}")

        return "\n".join(formatted)

    except Exception as e:
        return f"Error loading schema: {str(e)}"


def generate_cypher_from_nl(question: str) -> str:
    schema = load_schema_from_cache()

    prompt = f"""
You are a Neo4j Cypher expert.

STRICT GRAPH SCHEMA:
{schema}

IMPORTANT RULES:
1. Use ONLY given node labels and relationship types
2. NEVER invent new relationships or labels
3. Prefer specific relationships (avoid HAS_ENTITY unless absolutely needed)
4. Use node property: id for filtering
5. Use toLower(n.id) CONTAINS toLower("value") for search
6. Always use proper Cypher syntax
7. Return ONLY Cypher query
8. NO explanation, NO markdown

If unsure → return:
MATCH (n) RETURN n LIMIT 5

USER QUESTION:
{question}
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    text = response.text.strip()

    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("cypher"):
            text = text[len("cypher"):]

    return text.strip()



def _question_evaluator(question: str, generated_query: str) -> dict:
    """
    Fake evaluator function.
    Does NOT actually evaluate correctness.
    Just simulates evaluation pipeline.
    """

    print("🔍 Running dummy evaluator...")

    # fake scoring logic
    score = 0

    if "MATCH" in generated_query:
        score += 1

    if "RETURN" in generated_query:
        score += 1

    if len(question) > 5:
        score += 1

    # fake verdict
    if score >= 2:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    # fake explanation
    explanation = "This is a dummy evaluation. No real validation performed."

    # fake metadata
    result = {
        "question": question,
        "query": generated_query,
        "score": score,
        "verdict": verdict,
        "confidence": round(score / 3, 2),
        "note": explanation
    }

    return result


# ==========================================
# 🚀 Example Usage
# ==========================================
if __name__ == "__main__":
    q = "Who used hammer?"
    
    cypher_query = generate_cypher_from_nl(q)
    print("Generated Query:\n", cypher_query)

    evaluation = _question_evaluator(q, cypher_query)
    print("\nEvaluation Result:\n", evaluation)