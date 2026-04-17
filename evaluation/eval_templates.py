"""
evaluation/eval_templates.py

Evaluation query templates in triple format: SUBJECT _REL_ OBJECT
Each template maps to a Cypher query that fetches all matching triples
from the graph. These are used for KG evaluation — not for UI display.

Template format:
  - template_id   : unique string key
  - pattern       : human-readable  e.g.  "___ KILLS ___"
  - hop_type      : "single_hop" | "multi_hop"
  - subject_label : Neo4j label for the subject node
  - object_label  : Neo4j label for the object node
  - relationship  : relationship type (or list of types)
  - cypher        : full Cypher that returns (subject, predicate, object) rows
  - answer_key    : which RETURN alias holds the answer (usually "object")
"""

EVAL_TEMPLATES = [

    # ═══════════════════════════════════════════════════════
    # SINGLE HOP — direct relationship between two nodes
    # ═══════════════════════════════════════════════════════

    {
        "template_id":    "kills",
        "pattern":        "___ KILLS ___",
        "hop_type":       "single_hop",
        "subject_label":  "Person",
        "object_label":   "Person",
        "relationship":   ["KILLED", "MURDERS", "HACKED_TO_DEATH",
                           "BEATEN_TO_DEATH", "KILLS", "STRANGLED"],
        "cypher": """
            MATCH (s:Person)-[r]->(o:Person)
            WHERE type(r) IN ['KILLED','MURDERS','HACKED_TO_DEATH',
                              'BEATEN_TO_DEATH','KILLS','STRANGLED']
            RETURN s.id AS subject,
                   type(r) AS predicate,
                   o.id AS object
            ORDER BY subject
        """,
        "answer_key": "object",
    },

    {
        "template_id":    "arrested_by",
        "pattern":        "___ ARRESTED BY ___",
        "hop_type":       "single_hop",
        "subject_label":  "Person",
        "object_label":   "Organization",
        "relationship":   ["ARRESTED_BY", "ARRESTED"],
        "cypher": """
            MATCH (s:Person)-[r:ARRESTED_BY|ARRESTED]->(o)
            RETURN s.id AS subject,
                   type(r) AS predicate,
                   o.id AS object
            ORDER BY subject
        """,
        "answer_key": "object",
    },

    {
        "template_id":    "works_for",
        "pattern":        "___ WORKS FOR ___",
        "hop_type":       "single_hop",
        "subject_label":  "Person",
        "object_label":   "Organization",
        "relationship":   ["WORKS_FOR", "WORKS_AT", "WORKS_IN",
                           "EMPLOYED_BY", "OFFICIAL_OF"],
        "cypher": """
            MATCH (s:Person)-[r]->(o:Organization)
            WHERE type(r) IN ['WORKS_FOR','WORKS_AT','WORKS_IN',
                              'EMPLOYED_BY','OFFICIAL_OF']
            RETURN s.id AS subject,
                   type(r) AS predicate,
                   o.id AS object
            ORDER BY subject
        """,
        "answer_key": "object",
    },

    {
        "template_id":    "located_in",
        "pattern":        "___ LOCATED IN ___",
        "hop_type":       "single_hop",
        "subject_label":  "Person",
        "object_label":   "Location",
        "relationship":   ["LOCATED_IN", "RESIDES_IN", "LIVES_IN",
                           "RESIDED_IN", "IS_FROM", "NATIVE_OF"],
        "cypher": """
            MATCH (s)-[r]->(o:Location)
            WHERE type(r) IN ['LOCATED_IN','RESIDES_IN','LIVES_IN',
                              'RESIDED_IN','IS_FROM','NATIVE_OF']
            RETURN s.id AS subject,
                   type(r) AS predicate,
                   o.id AS object
            ORDER BY subject
        """,
        "answer_key": "object",
    },

    {
        "template_id":    "accused_of",
        "pattern":        "___ ACCUSED OF ___",
        "hop_type":       "single_hop",
        "subject_label":  "Person",
        "object_label":   "Crime",
        "relationship":   ["ACCUSED_OF", "ACCUSED_UNDER",
                           "BOOKED_FOR", "ARRESTED_FOR"],
        "cypher": """
            MATCH (s:Person)-[r]->(o)
            WHERE type(r) IN ['ACCUSED_OF','ACCUSED_UNDER',
                              'BOOKED_FOR','ARRESTED_FOR']
            RETURN s.id AS subject,
                   type(r) AS predicate,
                   o.id AS object
            ORDER BY subject
        """,
        "answer_key": "object",
    },

    {
        "template_id":    "married_to",
        "pattern":        "___ MARRIED TO ___",
        "hop_type":       "single_hop",
        "subject_label":  "Person",
        "object_label":   "Person",
        "relationship":   ["MARRIED_TO", "SPOUSE_OF", "WIFE_OF",
                           "HUSBAND_OF", "IS_HUSBAND_OF"],
        "cypher": """
            MATCH (s:Person)-[r]->(o:Person)
            WHERE type(r) IN ['MARRIED_TO','SPOUSE_OF','WIFE_OF',
                              'HUSBAND_OF','IS_HUSBAND_OF']
            RETURN s.id AS subject,
                   type(r) AS predicate,
                   o.id AS object
            ORDER BY subject
        """,
        "answer_key": "object",
    },

    {
        "template_id":    "stole_from",
        "pattern":        "___ STOLE FROM ___",
        "hop_type":       "single_hop",
        "subject_label":  "Person",
        "object_label":   "Person",
        "relationship":   ["STOLE_FROM", "STOLE", "ROBBED",
                           "ROBBED_OF", "THEFT_FROM"],
        "cypher": """
            MATCH (s:Person)-[r]->(o)
            WHERE type(r) IN ['STOLE_FROM','STOLE','ROBBED',
                              'ROBBED_OF','THEFT_FROM']
            RETURN s.id AS subject,
                   type(r) AS predicate,
                   o.id AS object
            ORDER BY subject
        """,
        "answer_key": "object",
    },

    {
        "template_id":    "filed_complaint",
        "pattern":        "___ FILED COMPLAINT AGAINST ___",
        "hop_type":       "single_hop",
        "subject_label":  "Person",
        "object_label":   "Person",
        "relationship":   ["FILED_COMPLAINT_AGAINST",
                           "FILED_COMPLAINT_TO",
                           "LODGED_COMPLAINT_AGAINST",
                           "REGISTERED_COMPLAINT_FOR"],
        "cypher": """
            MATCH (s)-[r]->(o)
            WHERE type(r) IN ['FILED_COMPLAINT_AGAINST',
                              'FILED_COMPLAINT_TO',
                              'LODGED_COMPLAINT_AGAINST',
                              'REGISTERED_COMPLAINT_FOR']
            RETURN s.id AS subject,
                   type(r) AS predicate,
                   o.id AS object
            ORDER BY subject
        """,
        "answer_key": "object",
    },

    # ═══════════════════════════════════════════════════════
    # MULTI HOP — chain of 2 relationships
    # ═══════════════════════════════════════════════════════

    {
        "template_id":    "person_crime_location",
        "pattern":        "___ COMMITTED CRIME AT ___  (via Crime node)",
        "hop_type":       "multi_hop",
        "subject_label":  "Person",
        "object_label":   "Location",
        "relationship":   ["any → Crime → Location"],
        "cypher": """
            MATCH (s:Person)-[r1]->(c:Crime)-[r2]->(o:Location)
            RETURN s.id AS subject,
                   type(r1) + ' → ' + c.id + ' → ' + type(r2) AS predicate,
                   o.id AS object
            ORDER BY subject
        """,
        "answer_key": "object",
    },

    {
        "template_id":    "person_org_location",
        "pattern":        "___ WORKS AT ORG IN ___  (via Organization)",
        "hop_type":       "multi_hop",
        "subject_label":  "Person",
        "object_label":   "Location",
        "relationship":   ["WORKS_FOR/AT → LOCATED_IN"],
        "cypher": """
            MATCH (s:Person)-[r1]->(org:Organization)-[r2:LOCATED_IN]->(o:Location)
            WHERE type(r1) IN ['WORKS_FOR','WORKS_AT','WORKS_IN','EMPLOYED_BY']
            RETURN s.id AS subject,
                   s.id + ' → ' + org.id AS predicate,
                   o.id AS object
            ORDER BY subject
        """,
        "answer_key": "object",
    },

    {
        "template_id":    "co_accused",
        "pattern":        "___ CO-ACCUSED WITH ___  (via shared Event)",
        "hop_type":       "multi_hop",
        "subject_label":  "Person",
        "object_label":   "Person",
        "relationship":   ["Person → Event ← Person"],
        "cypher": """
            MATCH (s:Person)-[r1]->(e:Event)<-[r2]-(o:Person)
            WHERE s <> o
            RETURN s.id AS subject,
                   'co-accused via ' + e.id AS predicate,
                   o.id AS object
            ORDER BY subject
            LIMIT 200
        """,
        "answer_key": "object",
    },
]