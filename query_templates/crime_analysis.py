"""
query_templates/crime_analysis.py
Crime-specific analytical queries for the news knowledge graph.
"""

TEMPLATE_TYPE = "Crime Analysis"

TEMPLATES = [
    {
        "name": "Top most connected People",
        "description": "Find people with the most relationships — key figures in the graph.",
        "query": (
            "MATCH (p:Person)-[r]-()\n"
            "RETURN p.id AS person, count(r) AS connections\n"
            "ORDER BY connections DESC\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "15", "default": "15"},
        ],
    },
    {
        "name": "All crimes in a City",
        "description": "List all crime events linked to a specific city.",
        "query": (
            "MATCH (c:Crime)-[r]-(l)\n"
            "WHERE (l:City OR l:Location)\n"
            "  AND toLower(l.id) CONTAINS toLower('{CITY}')\n"
            "RETURN c.id AS crime, type(r) AS relation, l.id AS location\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "CITY",  "label": "City Name",    "placeholder": "e.g. Thane, Pune", "default": ""},
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "20",               "default": "20"},
        ],
    },
    {
        "name": "Accused persons not yet arrested",
        "description": "Find people with HAS_NOT_ARRESTED relationships — still at large.",
        "query": (
            "MATCH (a)-[r:HAS_NOT_ARRESTED]->(p:Person)\n"
            "RETURN a.id AS authority, p.id AS accused_still_at_large\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "20", "default": "20"},
        ],
    },
    {
        "name": "Killed / Murder relationships",
        "description": "Find all kill or murder relationships in the graph.",
        "query": (
            "MATCH (a)-[r:KILLED|MURDERED|HACKED_TO_DEATH|BEATEN_TO_DEATH|"
            "TRIED_TO_MURDER|ATTEMPTED_TO_KILL|PLANNED_TO_KILL|KILLS]->(b)\n"
            "RETURN a.id AS perpetrator, type(r) AS action,\n"
            "       b.id AS victim, labels(a)[0] AS perp_type\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "20", "default": "20"},
        ],
    },
    {
        "name": "Financial fraud connections",
        "description": "Map money transfers, cheating and fraud relationships.",
        "query": (
            "MATCH (a)-[r:TRANSFERRED_MONEY_TO|TRANSFERRED_AMOUNT_TO|TRANSFERRED_FUNDS|"
            "CHEATED|DUPED_BY|LOST_MONEY_TO|DEMANDED_MONEY|DEMANDED_MONEY_FROM|"
            "DEMANDED_TRANSFER|TOOK_MONEY_FROM]->(b)\n"
            "RETURN a.id AS from, type(r) AS action, b.id AS to,\n"
            "       labels(a)[0] AS from_type, labels(b)[0] AS to_type\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "20", "default": "20"},
        ],
    },
    {
        "name": "All entities in a raw Chunk",
        "description": "Inspect which entities were extracted from a specific text chunk.",
        "query": (
            "MATCH (ch:Chunk)-[:HAS_ENTITY]->(e)\n"
            "RETURN ch.id AS chunk_id,\n"
            "       collect(e.id) AS entities,\n"
            "       collect(labels(e)[0]) AS entity_types\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Number of Chunks", "placeholder": "10", "default": "10"},
        ],
    },
    {
        "name": "Substance / drug seizures",
        "description": "Find substance-related seizures and who was involved.",
        "query": (
            "MATCH (a)-[r:SEIZED|RECOVERED|SEIZED_FROM|RECOVERED_FROM|CAUGHT_WITH]->(s:Substance)\n"
            "RETURN a.id AS seized_by, type(r) AS action, s.id AS substance\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "15", "default": "15"},
        ],
    },
]