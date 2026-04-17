"""
query_templates/single_hop.py
Schema-aware + safe queries (minimal modification)
"""

TEMPLATE_TYPE = "Single Hop"

TEMPLATES = [
   {
        "name": "People involved in a Crime",
        "description": "Find entities involved in a specific crime type (theft, murder, rape, etc.).",
        "query": (
            "MATCH (p)-[r]->(c)\n"
            "WHERE toLower(type(r)) CONTAINS toLower('{CRIME_TYPE}')\n"
            "OR toLower(coalesce(c.id,'')) CONTAINS toLower('{CRIME_TYPE}')\n"
            "RETURN p.id AS entity, type(r) AS relation, c.id AS crime\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {
                "key": "CRIME_TYPE",
                "label": "Crime Type",
                "placeholder": "e.g. theft, murder, rape",
                "default": ""
            },
            {
                "key": "LIMIT",
                "label": "Result Limit",
                "placeholder": "10",
                "default": "10"
            },
        ],
    },

    {
        "name": "All relations of a Person",
        "description": "See every relationship a named person has in the graph.",
        "query": (
            "MATCH (p:Person)-[r]->(x)\n"
            "WHERE toLower(coalesce(p.id,'')) CONTAINS toLower('{PERSON_NAME}')\n"
            "AND x.id IS NOT NULL\n"
            "RETURN p.id AS person, type(r) AS relationship, "
            "x.id AS connected_to, labels(x)[0] AS type\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON_NAME", "label": "Person Name", "placeholder": "e.g. Rahul, Sharma", "default": ""},
            {"key": "LIMIT",       "label": "Result Limit", "placeholder": "20", "default": "20"},
        ],
    },

    {
        "name": "Events at a Location",
        "description": "Find all events or incidents that occurred at a place.",
        "query": (
            "MATCH (e)-[r:OCCURRED_IN|OCCURRED_AT|LOCATED_IN|LOCATED_AT]->(l)\n"
            "WHERE toLower(l.id) = toLower('{LOCATION}')\n"
            "RETURN e.id AS event, type(r) AS relation, l.id AS location\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {
                "key": "LOCATION",
                "label": "Location Name",
                "placeholder": "e.g. Delhi, Pune,Mumbai",
                "default": ""
            },
            {
                "key": "LIMIT",
                "label": "Result Limit",
                "placeholder": "10",
                "default": "10"
            },
        ],
    },

    {
        "name": "Organizations a Person works for",
        "description": "Find which organizations a person is linked to.",
        "query": (
            "MATCH (p:Person)-[r:WORKS_FOR|WORKS_AT|WORKS_IN|EMPLOYED_BY|OFFICIAL_OF]->(o:Organization)\n"
            "WHERE toLower(coalesce(p.id,'')) CONTAINS toLower('{PERSON_NAME}')\n"
            "RETURN p.id AS person, type(r) AS relation, o.id AS organization\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON_NAME", "label": "Person Name", "placeholder": "e.g. Inspector Singh", "default": ""},
            {"key": "LIMIT",       "label": "Result Limit", "placeholder": "10", "default": "10"},
        ],
    },

    {
        "name": "Vehicles involved in incidents",
        "description": "Find vehicles linked to crimes or events.",
        "query": (
            "MATCH (v:Vehicle)-[r]-(x)\n"
            "WHERE v.id IS NOT NULL AND x.id IS NOT NULL\n"
            "RETURN v.id AS vehicle, type(r) AS relation, "
            "x.id AS connected_to, labels(x)[0] AS type\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "15", "default": "15"},
        ],
    },

    {
        "name": "Arrests — who arrested whom",
        "description": "Find all arrest relationships in the graph.",
        "query": (
            "MATCH (a)-[r:ARRESTED|ARRESTED_BY|ARRESTED_FOR|ARRESTED_IN|ARRESTED_FROM|ARRESTED_UNDER]->(b)\n"
            "WHERE a.id IS NOT NULL AND b.id IS NOT NULL\n"
            "RETURN a.id AS subject, type(r) AS action, b.id AS object,\n"
            "       labels(a)[0] AS subject_type, labels(b)[0] AS object_type\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "20", "default": "20"},
        ],
    },

    {
        "name": "Objects recovered from a location",
        "description": "See what objects were seized or recovered and from where.",
        "query": (
            "MATCH (a)-[r:RECOVERED|SEIZED|SEIZED_FROM|RECOVERED_FROM]->(b)\n"
            "WHERE a.id IS NOT NULL AND b.id IS NOT NULL\n"
            "RETURN a.id AS who, type(r) AS action, b.id AS what_or_where,\n"
            "       labels(b)[0] AS type\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "15", "default": "15"},
        ],
    },
]