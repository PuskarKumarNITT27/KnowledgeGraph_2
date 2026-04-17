"""
query_templates/multi_hop.py
Schema-aware multi-hop queries (label-independent, robust for your KG)
"""

TEMPLATE_TYPE = "Multi Hop"

TEMPLATES = [
    {
        "name": "Entity → Crime → Location chain",
        "description": "Trace an entity through a crime/event to where it happened.",
        "query": (
            "MATCH (p)-[r1]->(c)-[r2:OCCURRED_IN|OCCURRED_AT]->(l)\n"
            "WHERE toLower(coalesce(p.id,'')) CONTAINS toLower('{PERSON_NAME}')\n"
            "RETURN p.id AS entity, type(r1) AS action,\n"
            "       c.id AS crime, type(r2) AS crime_relation, l.id AS location\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON_NAME", "label": "Entity Name", "placeholder": "e.g. Raju, Theft", "default": ""},
            {"key": "LIMIT",       "label": "Result Limit", "placeholder": "10", "default": "10"},
        ],
    },

    {
        "name": "Co-entities in same events",
        "description": "Find entities involved in the same events.",
        "query": (
            "MATCH (p1)-[r1]->(e)<-[r2]-(p2)\n"
            "WHERE toLower(coalesce(p1.id,'')) CONTAINS toLower('{PERSON_NAME}')\n"
            "  AND p1 <> p2\n"
            "RETURN p1.id AS entity, p2.id AS related_entity,\n"
            "       e.id AS shared_event, count(e) AS shared_events\n"
            "ORDER BY shared_events DESC\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON_NAME", "label": "Entity Name", "placeholder": "e.g. Theft, Ramesh", "default": ""},
            {"key": "LIMIT",       "label": "Result Limit", "placeholder": "10", "default": "10"},
        ],
    },

    {
        "name": "Organization → Entity → Crime",
        "description": "Find crimes linked to entities from an organization.",
        "query": (
            "MATCH (o)<-[r1]-(p)-[r2]->(c)\n"
            "WHERE toLower(coalesce(o.id,'')) CONTAINS toLower('{ORG_NAME}')\n"
            "RETURN o.id AS organization, p.id AS entity,\n"
            "       type(r2) AS relation, c.id AS crime\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "ORG_NAME", "label": "Organization Name", "placeholder": "e.g. Police, Bank", "default": ""},
            {"key": "LIMIT",    "label": "Result Limit",       "placeholder": "10", "default": "10"},
        ],
    },

    {
        "name": "Chunk → Entities extracted",
        "description": "See all entities extracted from a chunk.",
        "query": (
            "MATCH (ch)-[:HAS_ENTITY]->(e)\n"
            "WHERE toLower(coalesce(ch.id,'')) CONTAINS toLower('{KEYWORD}')\n"
            "RETURN ch.id AS chunk, e.id AS entity, labels(e) AS entity_types\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "KEYWORD", "label": "Keyword", "placeholder": "e.g. murder, theft", "default": ""},
            {"key": "LIMIT",   "label": "Result Limit", "placeholder": "20", "default": "20"},
        ],
    },

    {
        "name": "Relationship network of an Entity",
        "description": "Map relationships like family, friends, associates.",
        "query": (
            "MATCH (p)-[r]->(p2)\n"
            "WHERE toLower(coalesce(p.id,'')) CONTAINS toLower('{PERSON_NAME}')\n"
            "  AND type(r) IN [\n"
            "    'MARRIED_TO','SPOUSE_OF','WIFE_OF','HUSBAND_OF',\n"
            "    'HAS_CHILD','CHILD_OF','BROTHER_OF','SISTER_OF',\n"
            "    'FRIEND_OF','PARTNER_OF'\n"
            "  ]\n"
            "RETURN p.id AS entity, type(r) AS relation, p2.id AS related_entity\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON_NAME", "label": "Entity Name", "placeholder": "e.g. Priya", "default": ""},
            {"key": "LIMIT",       "label": "Result Limit", "placeholder": "15", "default": "15"},
        ],
    },
]