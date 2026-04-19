TEMPLATE_TYPE = "Single Hop"

TEMPLATES = [

    # 1. KILLS
    {
        "name": "KILLS",
        "description": "Find who killed whom.\nFill ANY ONE or BOTH.\nExample: Ashraf → victims OR Mamta → killer",
        "query": (
            "MATCH (p)-[:MURDERS|KILLED]->(v)\n"
            "WHERE "
            "('{PERSON_1}' = '' OR toLower(p.id) CONTAINS toLower('{PERSON_1}')) AND "
            "('{PERSON_2}' = '' OR toLower(v.id) CONTAINS toLower('{PERSON_2}'))\n"
            "RETURN p.id AS killer, v.id AS victim\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON_1", "label": "Killer (optional)", "placeholder": "e.g. Mohammad Ashraf", "default": ""},
            {"key": "PERSON_2", "label": "Victim (optional)", "placeholder": "e.g. Mamta Bisht", "default": ""},
            {"key": "LIMIT", "label": "Limit", "placeholder": "e.g. 10", "default": "10"},
        ],
    },

    # 2. USED
    {
        "name": "USED",
        "description": "Find what was used.\nFill ANY ONE or BOTH.\nExample: Ashraf → objects OR Hammer → users",
        "query": (
            "MATCH (p)-[:USED]->(w)\n"
            "WHERE "
            "('{PERSON}' = '' OR toLower(p.id) CONTAINS toLower('{PERSON}')) AND "
            "('{OBJECT}' = '' OR toLower(w.id) CONTAINS toLower('{OBJECT}'))\n"
            "RETURN p.id AS person, w.id AS object\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON", "label": "Person (optional)", "placeholder": "e.g. Mohammad Ashraf", "default": ""},
            {"key": "OBJECT", "label": "Object (optional)", "placeholder": "e.g. Hammer", "default": ""},
            {"key": "LIMIT", "label": "Limit", "default": "10"},
        ],
    },

    # 3. LIVES_IN
    {
        "name": "LIVES_IN",
        "description": "Find residence.\nFill ANY ONE or BOTH.\nExample: Ashraf → location OR Kiccha → residents",
        "query": (
            "MATCH (p)-[:RESIDES_AT]->(l)\n"
            "WHERE "
            "('{PERSON}' = '' OR toLower(p.id) CONTAINS toLower('{PERSON}')) AND "
            "('{LOCATION}' = '' OR toLower(l.id) CONTAINS toLower('{LOCATION}'))\n"
            "RETURN p.id AS person, l.id AS location\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON", "label": "Person (optional)", "placeholder": "e.g. Mohammad Ashraf", "default": ""},
            {"key": "LOCATION", "label": "Location (optional)", "placeholder": "e.g. Kiccha", "default": ""},
            {"key": "LIMIT", "label": "Limit", "default": "10"},
        ],
    },

    # 4. WORKS_AS
    {
        "name": "WORKS_AS",
        "description": "Find profession.\nFill ANY ONE or BOTH.\nExample: Ashraf → profession OR Mason → people",
        "query": (
            "MATCH (p)-[:WORKS_AS]->(prof)\n"
            "WHERE "
            "('{PERSON}' = '' OR toLower(p.id) CONTAINS toLower('{PERSON}')) AND "
            "('{PROFESSION}' = '' OR toLower(prof.id) CONTAINS toLower('{PROFESSION}'))\n"
            "RETURN p.id AS person, prof.id AS profession\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON", "label": "Person (optional)", "default": ""},
            {"key": "PROFESSION", "label": "Profession (optional)", "default": ""},
            {"key": "LIMIT", "label": "Limit", "default": "10"},
        ],
    },

    # 5. ARRESTED_BY
    {
        "name": "ARRESTED_BY",
        "description": "Find arrest info.\nFill ANY ONE or BOTH.\nExample: Ashraf → police OR Police → arrested people",
        "query": (
            "MATCH (p)-[:ARRESTED_BY]->(o)\n"
            "WHERE "
            "('{PERSON}' = '' OR toLower(p.id) CONTAINS toLower('{PERSON}')) AND "
            "('{ORG}' = '' OR toLower(o.id) CONTAINS toLower('{ORG}'))\n"
            "RETURN p.id AS person, o.id AS organization\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON", "label": "Person (optional)", "default": ""},
            {"key": "ORG", "label": "Organization (optional)", "default": ""},
            {"key": "LIMIT", "label": "Limit", "default": "10"},
        ],
    },

    # 6. KNOWS
    {
        "name": "KNOWS",
        "description": "Find relationships.\nFill ANY ONE or BOTH.\nExample: Ashraf → known people OR Mamta → who knows her",
        "query": (
            "MATCH (p)-[:KNOWS]->(p2)\n"
            "WHERE "
            "('{PERSON_1}' = '' OR toLower(p.id) CONTAINS toLower('{PERSON_1}')) AND "
            "('{PERSON_2}' = '' OR toLower(p2.id) CONTAINS toLower('{PERSON_2}'))\n"
            "RETURN p.id AS person1, p2.id AS person2\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON_1", "label": "Person 1 (optional)", "default": ""},
            {"key": "PERSON_2", "label": "Person 2 (optional)", "default": ""},
            {"key": "LIMIT", "label": "Limit", "default": "10"},
        ],
    },

    # 7. HUSBAND_OF
    {
        "name": "HUSBAND_OF",
        "description": "Find husband.\nFill ANY ONE or BOTH.\nExample: Mamta → husband OR Ashraf → wife",
        "query": (
            "MATCH (p)-[:HUSBAND_OF]->(v)\n"
            "WHERE "
            "('{PERSON_1}' = '' OR toLower(p.id) CONTAINS toLower('{PERSON_1}')) AND "
            "('{PERSON_2}' = '' OR toLower(v.id) CONTAINS toLower('{PERSON_2}'))\n"
            "RETURN p.id AS husband, v.id AS wife\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "PERSON_1", "label": "Husband (optional)", "default": ""},
            {"key": "PERSON_2", "label": "Wife (optional)", "default": ""},
            {"key": "LIMIT", "label": "Limit", "default": "10"},
        ],
    },

    # 8. OCCURRED_ON
    {
        "name": "OCCURRED_ON",
        "description": "Find crime date.\nFill ANY ONE or BOTH.\nExample: Crime → date OR Date → crimes",
        "query": (
            "MATCH (c)-[:OCCURRED_ON]->(d)\n"
            "WHERE "
            "('{CRIME}' = '' OR toLower(c.id) CONTAINS toLower('{CRIME}')) AND "
            "('{DATE}' = '' OR toLower(d.id) CONTAINS toLower('{DATE}'))\n"
            "RETURN c.id AS crime, d.id AS date\n"
            "LIMIT {LIMIT}"
        ),
        "params": [
            {"key": "CRIME", "label": "Crime (optional)", "default": ""},
            {"key": "DATE", "label": "Date (optional)", "default": ""},
            {"key": "LIMIT", "label": "Limit", "default": "10"},
        ],
    },
]