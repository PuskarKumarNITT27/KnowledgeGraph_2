import json

def extract_schema(schema_path: str):
    with open(schema_path, "r") as f:
        schema = json.load(f)

    allowed_nodes = [item["label"] for item in schema.get("labels", [])]
    allowed_rels  = [rel["type"]  for rel in schema.get("relationships", [])]

    return allowed_nodes, allowed_rels

allowed_nodes, allowed_rels = extract_schema("schema_cache.json")

with open("schema.txt", "w") as f:
    f.write("NODE TYPES\n")
    for node in allowed_nodes:
        f.write(f"{node}\n")

    f.write("\nRELATIONSHIPS\n")
    for rel in allowed_rels:
        f.write(f"{rel}\n")

print("Done → schema.txt")