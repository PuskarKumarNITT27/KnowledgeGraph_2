"""
query_templates/conjunctive.py
Conjunctive (AND-logic) queries for the crime/news knowledge graph.
"""

TEMPLATE_TYPE = "Conjunctive Query"

TEMPLATES = [
    {
        "name": "Person involved in Crime AND Location",
        "description": "Find a person linked to both a specific crime and location.",
        "query": (
            "MATCH (p:Person)-[r1]->(c:Crime)\n"
            "MATCH (p)-[r2]->(l:Location)\n"
            "WHERE toLower(c.id) CONTAINS toLower('{CRIME_TYPE}')\n"
            "  AND toLower(l.id) CONTAINS toLower('{LOCATION}')\n"
            "RETURN p.id AS person, c.id AS crime, l.id AS location\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "CRIME_TYPE", "label": "Crime Type",    "placeholder": "e.g. robbery", "default": ""},
            {"key": "LOCATION",   "label": "Location",      "placeholder": "e.g. Pune",    "default": ""},
            {"key": "LIMIT",      "label": "Result Limit",  "placeholder": "10",           "default": "10"},
        ],
    },
    {
        "name": "Arrested AND charged under a Law",
        "description": "Find people who were both arrested and charged under a specific law.",
        "query": (
            "MATCH (a)-[r1:ARRESTED|ARRESTED_FOR|ARRESTED_UNDER]->(p:Person)\n"
            "MATCH (p)-[r2:ARRESTED_UNDER|BOOKED_FOR|ACCUSED_UNDER|REGISTERED_UNDER]->(l:Law)\n"
            "WHERE toLower(l.id) CONTAINS toLower('{LAW_NAME}')\n"
            "RETURN p.id AS person, a.id AS arrested_by,\n"
            "       l.id AS law\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LAW_NAME", "label": "Law / Act Name", "placeholder": "e.g. IPC, NDPS, POCSO", "default": ""},
            {"key": "LIMIT",    "label": "Result Limit",   "placeholder": "10", "default": "10"},
        ],
    },
    {
        "name": "Event in a City AND involving an Organization",
        "description": "Find events in a city that also involve a specific organization.",
        "query": (
            "MATCH (e:Event)-[r1]->(c:City)\n"
            "MATCH (e)-[r2]-(o:Organization)\n"
            "WHERE toLower(c.id) CONTAINS toLower('{CITY}')\n"
            "  AND toLower(o.id) CONTAINS toLower('{ORG_NAME}')\n"
            "RETURN e.id AS event, c.id AS city, o.id AS organization\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "CITY",     "label": "City",              "placeholder": "e.g. Mumbai",  "default": ""},
            {"key": "ORG_NAME", "label": "Organization Name", "placeholder": "e.g. Police",  "default": ""},
            {"key": "LIMIT",    "label": "Result Limit",      "placeholder": "10",           "default": "10"},
        ],
    },
    {
        "name": "Victim AND Accused in same chunk",
        "description": "Find chunks mentioning both a victim and an accused person.",
        "query": (
            "MATCH (ch:Chunk)-[:HAS_ENTITY]->(victim:Person)\n"
            "MATCH (ch)-[:HAS_ENTITY]->(accused:Person)\n"
            "WHERE toLower(victim.id) CONTAINS toLower('{VICTIM_NAME}')\n"
            "  AND toLower(accused.id) CONTAINS toLower('{ACCUSED_NAME}')\n"
            "  AND victim <> accused\n"
            "RETURN ch.id AS chunk, victim.id AS victim, accused.id AS accused\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "VICTIM_NAME",  "label": "Victim Name",  "placeholder": "e.g. Priya",  "default": ""},
            {"key": "ACCUSED_NAME", "label": "Accused Name", "placeholder": "e.g. Raju",   "default": ""},
            {"key": "LIMIT",        "label": "Result Limit", "placeholder": "10",           "default": "10"},
        ],
    },

    {
        "name": "Person who KILLED someone AND was ARRESTED",
        "description": "Find accused persons who both killed a victim and were subsequently arrested.",
        "query": (
            "MATCH (accused)-[:KILLED]->(victim)\n"
            "WITH accused, collect(victim.id)[0] AS killed_person\n"
            "MATCH (org)-[:ARRESTED]->(accused)\n"
            "WHERE accused.id IS NOT NULL\n"
            "RETURN accused.id AS accused, killed_person AS victim,\n"
            "       org.id AS arrested_by\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "15", "default": "15"},
        ],
    },

    {
        "name": "Person worked at victim's place AND committed crime there",
        "description": "Find accused who previously worked at the crime location (prior access motive).",
        "query": (
            "MATCH (accused)-[:WORKS_AT|WORKS_FOR|WORKED_AT]->(place)\n"
            "WITH accused, place\n"
            "MATCH (accused)-[:KILLED|COMMITTED|ATTACKED|COMMITTED_OFFENSE_AGAINST]->(victim)\n"
            "WHERE accused.id IS NOT NULL AND place.id IS NOT NULL\n"
            "RETURN accused.id AS accused, place.id AS prior_workplace,\n"
            "       victim.id AS crime_victim\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "10", "default": "10"},
        ],
    },

    {
        "name": "Accused with weapon recovered AND confession",
        "description": "Find accused from whom evidence was recovered AND who also confessed.",
        "query": (
            "MATCH (org)-[:RECOVERED|SEIZED]->(item)\n"
            "WITH org, collect(item.id) AS recovered_items\n"
            "MATCH (org)-[:ARRESTED]->(accused)-[:CONFESSED_TO]->(crime)\n"
            "WHERE accused.id IS NOT NULL\n"
            "RETURN accused.id AS accused, crime.id AS confession,\n"
            "       recovered_items[0..3] AS evidence_recovered\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "LIMIT", "label": "Result Limit", "placeholder": "10", "default": "10"},
        ],
    },
]