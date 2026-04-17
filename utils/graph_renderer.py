"""
utils/graph_renderer.py
Converts node/edge data from Neo4j into an interactive pyvis HTML graph
and returns the HTML string for Streamlit to render.
"""

from typing import Dict
from pathlib import Path
import tempfile

try:
    from pyvis.network import Network
except ImportError:
    Network = None  # Handled gracefully below

# Colour palette — one colour per node group/label
LABEL_COLORS = [
    "#4C9BE8", "#E8834C", "#4CE8A0", "#E84C6B",
    "#A04CE8", "#E8D44C", "#4CE8D4", "#E84CC8",
]


def build_graph_html(graph_data: Dict, height: str = "600px") -> tuple[bool, str]:
    """
    Build an interactive pyvis graph from graph_data and return raw HTML.

    Args:
        graph_data: {"nodes": [...], "edges": [...]} OR {"rows": [...]}
        height:     Height of the rendered graph div.

    Returns:
        (True,  html_string)   on success
        (False, error_message) on failure
    """
    if Network is None:
        return False, "pyvis is not installed. Run: pip install pyvis"

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    # ── ✅ SMART FALLBACK FOR TABLE DATA ───────────────────────────────
    if not nodes and "rows" in graph_data:
        rows = graph_data["rows"]

        node_map = {}
        edge_list = []

        for row in rows:
            keys = list(row.keys())
            values = list(row.values())

            # ---- create nodes ----
            for v in values:
                if v not in node_map:
                    node_map[v] = {
                        "id": str(v),
                        "label": str(v),
                        "group": "Entity",
                    }

            # ---- detect relationship column ----
            rel_idx = None
            for i, k in enumerate(keys):
                if "rel" in k.lower() or "relation" in k.lower():
                    rel_idx = i
                    break

            # ---- smart edge creation ----
            if rel_idx is not None and len(values) >= 3:
                source = str(values[0])
                relation = str(values[rel_idx])

                # ✅ FIX: correct target (next column after relation)
                if rel_idx + 1 < len(values):
                    target = str(values[rel_idx + 1])
                else:
                    target = str(values[-1])

                edge_list.append({
                    "source": source,
                    "target": target,
                    "label": relation,
                })

            # ---- fallback chaining ----
            else:
                for i in range(len(values) - 1):
                    edge_list.append({
                        "source": str(values[i]),
                        "target": str(values[i + 1]),
                        "label": "",
                    })

        nodes = list(node_map.values())
        edges = edge_list
    # ─────────────────────────────────────────────────────────────────

    if not nodes:
        return False, "No nodes found in query result."

    # Assign colors
    groups = list({n.get("group", "Node") for n in nodes})
    color_map = {g: LABEL_COLORS[i % len(LABEL_COLORS)] for i, g in enumerate(groups)}

    # Build graph
    net = Network(
        height=height,
        width="100%",
        bgcolor="#0E1117",
        font_color="#FFFFFF",
        directed=True,
    )

    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=120,
        spring_strength=0.05,
        damping=0.09,
    )

    # ---- nodes ----
    for node in nodes:
        net.add_node(
            node["id"],
            label=node["label"],
            title=node.get("title", ""),
            color=color_map.get(node.get("group", "Node"), "#4C9BE8"),
            size=20,
            font={"size": 14, "color": "#FFFFFF"},
            borderWidth=2,
            borderWidthSelected=4,
        )

    # ---- edges ----
    for edge in edges:
        net.add_edge(
            edge["source"],
            edge["target"],
            title=edge.get("label", ""),
            label=edge.get("label", ""),
            color={"color": "#888888", "highlight": "#FFFFFF"},
            arrows="to",
            font={"size": 11, "color": "#AAAAAA", "align": "middle"},
        )

    # Save HTML
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as tmp:
        tmp_path = tmp.name

    net.save_graph(tmp_path)
    html = Path(tmp_path).read_text(encoding="utf-8")
    Path(tmp_path).unlink(missing_ok=True)

    return True, html