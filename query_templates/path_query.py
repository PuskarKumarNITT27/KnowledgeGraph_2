"""
query_templates/path_query.py
Schema-aware path queries (label-independent, works with your KG)
"""

TEMPLATE_TYPE = "Path Query"

TEMPLATES = [
    {
        "name": "Shortest path between two Entities",
        "description": "Find the shortest connection between any two entities (people, places, etc.).",
        "query": (
            "MATCH (a), (b)\n"
            "WHERE toLower(coalesce(a.id,'')) CONTAINS toLower('{PERSON_A}')\n"
            "  AND toLower(coalesce(b.id,'')) CONTAINS toLower('{PERSON_B}')\n"
            "  AND a <> b\n"
            "MATCH path = shortestPath((a)-[*..{MAX_DEPTH}]-(b))\n"
            "RETURN path"
        ),
        "params": [
            {"key": "PERSON_A",  "label": "First Entity",  "placeholder": "e.g. Raju",   "default": ""},
            {"key": "PERSON_B",  "label": "Second Entity", "placeholder": "e.g. Suresh", "default": ""},
            {"key": "MAX_DEPTH", "label": "Max Hops",      "placeholder": "5",           "default": "5"},
        ],
    },

    {
        "name": "All paths: Entity to Location",
        "description": "Find all ways an entity is connected to a location.",
        "query": (
            "MATCH (p), (l)\n"
            "WHERE toLower(coalesce(p.id,'')) CONTAINS toLower('{PERSON_NAME}')\n"
            "  AND toLower(coalesce(l.id,'')) CONTAINS toLower('{LOCATION}')\n"
            "MATCH path = (p)-[*1..{MAX_DEPTH}]->(l)\n"
            "RETURN path\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON_NAME", "label": "Entity Name", "placeholder": "e.g. Sanjay Gorle",  "default": "Sanjay Gorle"},
            {"key": "LOCATION",    "label": "Location",    "placeholder": "e.g. Kolhapur",   "default": "Kolhapur"},
            {"key": "MAX_DEPTH",   "label": "Max Hops",    "placeholder": "4",           "default": "4"},
            {"key": "LIMIT",       "label": "Result Limit","placeholder": "5",           "default": "5"},
        ],
    },

    {
        "name": "Crime network around an Entity",
        "description": "Expand all nodes reachable from an entity within N hops.",
        "query": (
            "MATCH (p)\n"
            "WHERE toLower(coalesce(p.id,'')) CONTAINS toLower('{PERSON_NAME}')\n"
            "MATCH path = (p)-[*1..{MAX_DEPTH}]-(x)\n"
            "RETURN path\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON_NAME", "label": "Entity Name", "placeholder": "e.g. Ramesh", "default": ""},
            {"key": "MAX_DEPTH",   "label": "Max Hops",    "placeholder": "2",           "default": "2"},
            {"key": "LIMIT",       "label": "Result Limit","placeholder": "50",          "default": "50"},
        ],
    },
]