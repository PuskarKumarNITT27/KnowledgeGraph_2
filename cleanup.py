"""
cleanup.py — Deduplicate nodes and normalise relationship types in Neo4j Aura.

Run with:
    python cleanup.py

Steps:
  1. Find & report duplicate entity nodes (same id, case-insensitive)
  2. Merge duplicate nodes via APOC (keeps all properties + re-routes all edges)
  3. Normalise semantically-similar relationship types into canonical ones
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI      = os.getenv("NEO4J_URI")
USER     = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


# ── helpers ────────────────────────────────────────────────────────────────────

def run(cypher, params=None):
    with driver.session() as s:
        result = s.run(cypher, params or {})
        return [dict(r) for r in result]


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── Step 1 : Report duplicates ──────────────────────────────────────────────

section("STEP 1 — Duplicate node check (excluding Chunks)")

dups = run("""
MATCH (n)
WHERE n.id IS NOT NULL
  AND NOT 'Chunk' IN labels(n)
WITH toLower(trim(n.id)) AS norm_id, collect(n) AS nodes
WHERE size(nodes) > 1
RETURN norm_id            AS duplicate_id,
       size(nodes)        AS count,
       [x IN nodes | labels(x)[0]][0..3] AS sample_labels
ORDER BY count DESC
LIMIT 30
""")

if not dups:
    print("  ✅  No duplicate nodes found.")
else:
    print(f"  ⚠️  Found {len(dups)} duplicate id groups:\n")
    for d in dups:
        print(f"  [{d['count']}x]  \"{d['duplicate_id']}\"  labels={d['sample_labels']}")


# ── Step 2 : Merge duplicate nodes (APOC) ──────────────────────────────────

section("STEP 2 — Merging duplicate nodes via APOC")

try:
    result = run("""
    MATCH (n)
    WHERE n.id IS NOT NULL
      AND NOT 'Chunk' IN labels(n)
    WITH toLower(trim(n.id)) AS norm_id, collect(n) AS nodes
    WHERE size(nodes) > 1
    CALL apoc.refactor.mergeNodes(nodes, {
        properties : 'overwrite',
        mergeRels  : true
    })
    YIELD node
    RETURN count(node) AS merged_count
    """)
    merged = result[0]["merged_count"] if result else 0
    print(f"  ✅  Merged {merged} duplicate node group(s).")
except Exception as e:
    print(f"  ❌  APOC merge failed: {e}")
    print("     Make sure APOC is enabled on your Neo4j Aura instance.")


# ── Step 3 : Normalise relationship types ──────────────────────────────────

section("STEP 3 — Normalising similar relationship types")

# Map of (old types to rename → canonical type)
REL_NORMALISATION = {
    # Murder / Violence
    "KILLS":                  "KILLED",
    "MURDERED":               "KILLED",
    "HACKED_TO_DEATH":        "KILLED",
    "BEATEN_TO_DEATH":        "KILLED",
    "STRANGLED":              "KILLED",

    # Arrest variants
    "ARRESTED_BY":            "ARRESTED",
    "ARRESTED_FOR":           "ARRESTED",
    "ARRESTED_FROM":          "ARRESTED",
    "ARRESTED_IN":            "ARRESTED",
    "ARRESTED_UNDER":         "ARRESTED",
    "TOOK_INTO_CUSTODY":      "ARRESTED",
    "APPREHENDED":            "ARRESTED",
    "NABBED":                 "ARRESTED",
    "DETAINED":               "ARRESTED",

    # Location variants
    "LOCATED_AT":             "LOCATED_IN",
    "LOCATED_ON":             "LOCATED_IN",
    "LOCATED_UNDER":          "LOCATED_IN",
    "AT_LOCATION":            "LOCATED_IN",

    # Residence variants
    "RESIDED_IN":             "RESIDES_IN",
    "RESIDES_ON":             "RESIDES_IN",
    "RESIDED_NEAR":           "RESIDES_IN",
    "USUALLY_RESIDES_AT":     "RESIDES_IN",
    "LIVES_IN":               "RESIDES_IN",

    # Work / employment variants
    "WORKED_AT":              "WORKS_AT",
    "WORKED_FOR":             "WORKS_FOR",
    "WORKS_IN":               "WORKS_FOR",
    "EMPLOYED_BY":            "WORKS_FOR",
    "FORMER_EMPLOYEE_OF":     "WORKS_FOR",

    # FIR / complaint variants
    "FILED_COMPLAINT_AGAINST":"FILED_COMPLAINT",
    "FILED_COMPLAINT_AT":     "FILED_COMPLAINT",
    "FILED_COMPLAINT_FOR":    "FILED_COMPLAINT",
    "FILED_COMPLAINT_TO":     "FILED_COMPLAINT",
    "FILED_COMPLAINT_WITH":   "FILED_COMPLAINT",
    "LODGED_COMPLAINT_AGAINST":"FILED_COMPLAINT",
    "LODGED_COMPLAINT_FOR":   "FILED_COMPLAINT",
    "LODGED_COMPLAINT_UNDER": "FILED_COMPLAINT",
    "LODGED_COMPLAINT_WITH":  "FILED_COMPLAINT",

    # Occurrence / location of event
    "OCCURRED_AT":            "OCCURRED_IN",
    "TOOK_PLACE_AT":          "OCCURRED_IN",

    # Recovery / seizure
    "SEIZED_FROM":            "SEIZED",
    "RECOVERED_FROM":         "RECOVERED",

    # Flee
    "FLED_WITH":              "FLED_TO",
    "FLED_FROM":              "FLED_TO",

    # Relationship
    "HAS_RELATIONSHIP_WITH":  "HAS_RELATIONSHIP",
    "IN_RELATIONSHIP_WITH":   "HAS_RELATIONSHIP",

    # Family
    "IS_BROTHER_OF":          "BROTHER_OF",
    "IS_HUSBAND_OF":          "HUSBAND_OF",
    "IS_SISTER_OF":           "SISTER_OF",

    # Victim
    "IS_VICTIM_OF":           "VICTIM_OF",

    # Member
    "IS_MEMBER_OF":           "MEMBER_OF",
    "IS_A_MEMBER_OF":         "MEMBER_OF",
    "IS_PART_OF":             "PART_OF",
}

total_renamed = 0
for old_type, new_type in REL_NORMALISATION.items():
    try:
        # Pure Cypher: create a new rel with canonical type, delete the old one
        result = run(f"""
        MATCH (a)-[r:{old_type}]->(b)
        CREATE (a)-[:{new_type}]->(b)
        WITH r
        DELETE r
        RETURN count(*) AS renamed
        """)
        count = result[0]["renamed"] if result else 0
        if count:
            print(f"  ✅  {old_type:35s} → {new_type}   ({count} relationships)")
            total_renamed += count
    except Exception as e:
        print(f"  ⚠️  Could not rename {old_type}: {e}")

print(f"\n  Total relationships renamed: {total_renamed}")


# ── Done ───────────────────────────────────────────────────────────────────────

section("DONE")
print("  Graph cleanup complete.")
print("  Run 'Fetch Live Schema' in the app to refresh your schema cache.\n")

driver.close()
