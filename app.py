"""
app.py — Main entry point for the Knowledge Graph Streamlit app.
"""

import streamlit as st
from pathlib import Path

from utils.schema_inspector import fetch_full_schema, load_schema_from_cache
from utils.llm_query_generator import generate_cypher_from_nl
from input_files.ocr_extractor import process_ocr_file
from input_files.pdf_extractor import process_pdf_file
from input_files.csv_extractor import process_csv_file
from utils.query_extractor import run_neo4j_query, run_neo4j_graph_query
from utils.graph_renderer import build_graph_html
from utils.gemini_evaluator import validate_and_update_graph
from utils.schema_inspector import fetch_full_schema
from query_templates.loader import load_all_templates

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Knowledge Graph System",
    page_icon="🕸️",
    layout="wide",
)

Path("extracted_data").mkdir(exist_ok=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    st.sidebar.title("📂 File Upload")
    st.sidebar.markdown("Upload OCR images, PDFs, or CSVs to extract and chunk text.")

    uploaded_file = st.sidebar.file_uploader(
        label="Choose a file",
        type=["png", "jpg", "jpeg", "tiff", "bmp", "pdf", "csv"],
        help="Supported: Images (OCR), PDF, CSV",
    )

    submit_clicked = st.sidebar.button("🚀 Submit File", use_container_width=True)
    if submit_clicked:
        handle_file_submission(uploaded_file)

    # ── Mode switcher in sidebar ──────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧭 Mode")

    if "active_mode" not in st.session_state:
        st.session_state.active_mode = "query"

    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        if st.button(
            "🔍 Query",
            use_container_width=True,
            type="primary" if st.session_state.active_mode == "query" else "secondary",
            key="btn_query_mode",
        ):
            st.session_state.active_mode = "query"
            st.rerun()
    with col2:
        if st.button(
            "🧪 Tune",
            use_container_width=True,
            type="primary" if st.session_state.active_mode == "finetune" else "secondary",
            key="btn_finetune_mode",
        ):
            st.session_state.active_mode = "finetune"
            st.rerun()
    with col3:
        if st.button(
            "🗺 Schema",
            use_container_width=True,
            type="primary" if st.session_state.active_mode == "schema" else "secondary",
            key="btn_schema_mode",
        ):
            st.session_state.active_mode = "schema"
            st.rerun()

    mode_hints = {
        "query":    "🔍 **Query mode** — Explore your graph.",
        "finetune": "🧪 **Fine-tune mode** — Validate & repair with Gemini.",
        "schema":   "🗺 **Schema mode** — Inspect labels, properties & relationships.",
    }
    st.sidebar.info(mode_hints.get(st.session_state.active_mode, ""))


def handle_file_submission(uploaded_file):
    if uploaded_file is None:
        st.sidebar.error("⚠️ Please upload a file before submitting.")
        return

    extension = Path(uploaded_file.name).suffix.lower()
    OCR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

    if extension in OCR_EXTENSIONS:
        with st.sidebar.status("Processing OCR file…", expanded=True) as status:
            success, message = process_ocr_file(uploaded_file)
            status.update(label=message, state="complete" if success else "error")
        if success:
            st.sidebar.success(message)

    elif extension == ".pdf":
        with st.sidebar.status("Processing PDF file…", expanded=True) as status:
            success, message = process_pdf_file(uploaded_file)
            status.update(label=message, state="complete" if success else "error")
        if success:
            st.sidebar.success(message)

    elif extension == ".csv":
        with st.sidebar.status("Scraping & chunking CSV…", expanded=True) as status:
            success, message = process_csv_file(uploaded_file)
            status.update(label=message, state="complete" if success else "error")
        if success:
            st.sidebar.success(message)
        else:
            st.sidebar.error(message)
    else:
        st.sidebar.error(f"❌ Unsupported file type: `{extension}`")


# ── Query Section ─────────────────────────────────────────────────────────────
def render_query_section():
    st.title("🔍 Query the Knowledge Graph")
    st.markdown("Run Cypher queries against your Neo4j Aura database.")

    # ── Template Picker ───────────────────────────────────────────────────────
    _render_template_picker()

    # ── Manual query form ─────────────────────────────────────────────────────
    with st.expander("💡 Query tips"):
        st.markdown("""
        For **Graph View** — return nodes and relationships:
        ```cypher
        MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 50
        ```
        For **Table View** — any Cypher works:
        ```cypher
        MATCH (n:Article) RETURN n.title LIMIT 20
        ```
        """)

    # Pre-fill query box if a template was applied
    prefill = st.session_state.get("prefill_query", "")

    with st.form(key="query_form"):
        query_input = st.text_area(
            label="Enter your Cypher query",
            value=prefill,
            placeholder="MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 50",
            height=130,
        )
        submitted = st.form_submit_button("🔍 Run Query", use_container_width=True)

    if submitted:
        handle_query_submission(query_input)


# ── Template picker UI ────────────────────────────────────────────────────────

def _render_template_picker():
    """
    Renders:
      1. A dropdown to choose the template TYPE (Single Hop, Multi Hop, …)
      2. Cards for every template in that type
      3. A @st.dialog popup with dynamic param inputs when a card is clicked
      4. On OK → injects the formatted query into the query text area
    """
    all_templates = load_all_templates()
    if not all_templates:
        return

    with st.expander("📋 Template Queries", expanded=False):
        type_options = list(all_templates.keys())

        selected_type = st.selectbox(
            "Query Type",
            options=type_options,
            key="template_type_selector",
            help="Choose a category, then click any template card below.",
        )

        templates = all_templates.get(selected_type, [])
        if not templates:
            st.info("No templates found for this type.")
            return

        st.markdown(f"**{len(templates)} template(s) available — click one to fill placeholders:**")

        # Render template cards in a responsive grid (3 per row)
        cols = st.columns(min(3, len(templates)))
        for idx, tmpl in enumerate(templates):
            with cols[idx % 3]:
                if st.button(
                    label=f"🗂 {tmpl['name']}",
                    key=f"tmpl_card_{selected_type}_{idx}",
                    use_container_width=True,
                    help=tmpl["description"],
                ):
                    st.session_state["_dialog_template"] = tmpl
                    st.session_state["_dialog_open"] = True
                st.caption(tmpl["description"])

    # Open dialog if a card was clicked
    if st.session_state.get("_dialog_open"):
        _open_template_dialog()


@st.dialog("Fill Template Parameters")
def _open_template_dialog():
    tmpl = st.session_state.get("_dialog_template")
    if not tmpl:
        st.warning("No template selected.")
        return

    st.markdown(f"### 🗂 {tmpl['name']}")
    st.caption(tmpl["description"])
    st.markdown("---")

    # ── Preview ─────────────────────────────
    with st.expander("👁 Preview raw template"):
        st.code(tmpl["query"], language="cypher")

    st.markdown("**Fill in the placeholders:**")

    param_values = {}

    # ── Input fields ────────────────────────
    for param in tmpl.get("params", []):
        key = param["key"]

        val = st.text_input(
            label=param.get("label", key),
            value=st.session_state.get(f"_dialog_param_{key}", param.get("default", "")),
            placeholder=param.get("placeholder", ""),
            key=f"_dialog_param_{key}",
        )

        param_values[key] = val

    st.markdown("---")
    col_ok, col_cancel = st.columns(2)

    # ── APPLY BUTTON ────────────────────────
    with col_ok:
        if st.button("✅ Apply to Query Box", use_container_width=True, type="primary"):

            # ✅ CLEAN VALUES (fix spaces + None)
            clean_values = {
                k: (v.strip() if isinstance(v, str) else "")
                for k, v in param_values.items()
            }

            # ✅ VALIDATION (ONLY required fields)
            missing = []
            for p in tmpl.get("params", []):
                key = p["key"]
                if p.get("required", False) and not clean_values.get(key, ""):
                    missing.append(p.get("label", key))

            if missing:
                st.warning(f"⚠️ Please fill in: {', '.join(missing)}")
                return

            # ✅ INFO: no filters applied
            non_limit_keys = [k for k in clean_values if k != "LIMIT"]
            if not any(clean_values[k] for k in non_limit_keys):
                st.info("ℹ️ No filters applied — showing ALL results")

            # ✅ FORMAT QUERY
            formatted = tmpl["query"]
            for key, val in clean_values.items():
                formatted = formatted.replace(f"{{{key}}}", val)

            # ✅ Inject query
            st.session_state["prefill_query"] = formatted

            # 🔥 CLEAR OLD INPUT STATE (CRITICAL FIX)
            for k in list(st.session_state.keys()):
                if k.startswith("_dialog_param_"):
                    del st.session_state[k]

            # Close dialog
            st.session_state["_dialog_open"] = False
            st.session_state.pop("_dialog_template", None)

            st.rerun()

    # ── CANCEL BUTTON ───────────────────────
    with col_cancel:
        if st.button("❌ Cancel", use_container_width=True):
            for k in list(st.session_state.keys()):
                if k.startswith("_dialog_param_"):
                    del st.session_state[k]

            st.session_state["_dialog_open"] = False
            st.session_state.pop("_dialog_template", None)
            st.rerun()
# ── Cypher detection ──────────────────────────────────────────────────────────

def is_cypher(q: str) -> bool:
    return any(q.strip().lower().startswith(k) for k in [
        "match", "create", "merge", "call", "with", "return"
    ])


# ── Query Submission handler ──────────────────────────────────────────────────
def handle_query_submission(query: str):
    if not query.strip():
        st.warning("⚠️ Query cannot be empty.")
        return

    # Convert Natural Language → Cypher if needed
    if not is_cypher(query):
        with st.spinner("🤖 Converting to Cypher using Gemini..."):
            try:
                generated_query = generate_cypher_from_nl(query)
                st.info("🔁 Generated Cypher:")
                st.code(generated_query, language="cypher")
                query = generated_query
            except Exception as e:
                st.error(f"LLM conversion failed: {e}")
                return

    tab_table, tab_graph = st.tabs(["📋 Table View", "🕸️ Graph View"])

    # ── TABLE VIEW ─────────────────────────────────────────
    with tab_table:
        with st.spinner("Fetching results…"):
            success, result = run_neo4j_query(query)

        if success:
            st.success(f"✅ Returned **{len(result)}** record(s).")
            if result:
                st.dataframe(result, use_container_width=True)
            else:
                st.info("Query executed successfully but returned no records.")
        else:
            st.error(f"❌ {result}")

    # ── GRAPH VIEW ─────────────────────────────────────────
    with tab_graph:
        with st.spinner("Building graph…"):
            g_success, g_result = run_neo4j_graph_query(query)

        # ✅ CASE 1: Proper graph data exists
        if g_success and g_result.get("nodes"):
            node_count = len(g_result["nodes"])
            edge_count = len(g_result["edges"])

            st.success(f"✅ Graph: **{node_count}** nodes · **{edge_count}** edges")

            html_ok, html_or_err = build_graph_html(g_result)

        # ✅ CASE 2: Fallback → build graph from table data
        else:
            if success and result:
                st.info("⚠️ No graph objects found → building graph from table data")

                fallback_data = {"rows": result}
                html_ok, html_or_err = build_graph_html(fallback_data)

            else:
                st.error("❌ Unable to render graph.")
                return

        # ✅ Render graph
        if html_ok:
            st.components.v1.html(html_or_err, height=620, scrolling=False)
        else:
            st.error(html_or_err)
            
            
# ── Fine-tune / Validate Section ──────────────────────────────────────────────
def render_validate_section():
    st.title("🧪 Validate & Fine-tune Graph")
    st.markdown(
        "Paste text or upload a file. Gemini will generate questions, "
        "check your Neo4j graph for correct answers, and **automatically fix** "
        "any gaps or errors it finds."
    )

    input_mode = st.radio(
        "Input mode",
        ["✏️ Paste text", "📄 Upload file (PDF / TXT)"],
        horizontal=True,
    )

    text_chunk = ""

    if input_mode == "✏️ Paste text":
        text_chunk = st.text_area(
            label="Text chunk to validate",
            placeholder="Paste a paragraph or article excerpt here…",
            height=200,
            key="validate_text",
        )
    else:
        val_file = st.file_uploader(
            "Upload PDF or TXT file",
            type=["pdf", "txt"],
            key="validate_file",
        )
        if val_file:
            text_chunk = _read_uploaded_text(val_file)
            if text_chunk:
                with st.expander("📄 Preview extracted text"):
                    st.text(text_chunk[:1500] + ("…" if len(text_chunk) > 1500 else ""))

    validate_clicked = st.button(
        "✅ Validate",
        use_container_width=True,
        type="primary",
    )

    if validate_clicked:
        handle_validation(text_chunk)


def handle_validation(text_chunk: str):
    if not text_chunk.strip():
        st.warning("⚠️ Please provide some text before validating.")
        return

    word_count = len(text_chunk.split())
    st.info(f"📊 Processing **{word_count}** words against your Neo4j graph…")

    progress = st.progress(0, text="Sending to Gemini…")

    with st.spinner("Gemini is generating questions and validating answers…"):
        success, result = validate_and_update_graph(text_chunk)

    progress.progress(100, text="Done!")

    if not success:
        st.error(f"❌ Validation failed: {result}")
        return

    if not result:
        st.warning("⚠️ Gemini could not generate any questions from this text.")
        return

    total   = len(result)
    correct = sum(1 for r in result if r.status == "correct")
    created = sum(1 for r in result if r.status == "created")
    updated = sum(1 for r in result if r.status == "updated")
    errors  = sum(1 for r in result if r.status == "error")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("✅ Correct", correct)
    col2.metric("🆕 Created", created)
    col3.metric("✏️ Updated", updated)
    col4.metric("❌ Errors",  errors)

    st.subheader("📋 Detailed Change Log")

    STATUS_ICONS  = {"correct": "✅", "created": "🆕", "updated": "✏️", "error": "❌"}
    STATUS_COLORS = {"correct": "green", "created": "blue", "updated": "orange", "error": "red"}

    for i, record in enumerate(result, 1):
        icon  = STATUS_ICONS.get(record.status, "•")
        color = STATUS_COLORS.get(record.status, "grey")

        with st.expander(f"{icon} Q{i}: {record.question}"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**📖 Expected (from text)**")
                st.info(record.expected_answer)
            with col_b:
                st.markdown("**🗄️ Graph returned**")
                if record.neo4j_answer != record.expected_answer:
                    st.warning(record.neo4j_answer)
                else:
                    st.success(record.neo4j_answer)

            st.markdown(f"**Status:** :{color}[{record.status.upper()}]")

            if record.cypher_executed:
                st.markdown("**Cypher executed on Neo4j:**")
                st.code(record.cypher_executed, language="cypher")

            if record.error_detail:
                st.error(record.error_detail)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _read_uploaded_text(uploaded_file) -> str:
    extension = Path(uploaded_file.name).suffix.lower()

    if extension == ".txt":
        return uploaded_file.read().decode("utf-8", errors="ignore")

    elif extension == ".pdf":
        try:
            import fitz
            pdf_bytes = uploaded_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages = [page.get_text() for page in doc]
            doc.close()
            return "\n".join(pages)
        except ImportError:
            st.error("PyMuPDF not installed. Run: pip install pymupdf")
            return ""
        except Exception as e:
            st.error(f"Could not read PDF: {e}")
            return ""
    else:
        st.error(f"Unsupported file type: {extension}")
        return ""


# ── Schema Inspector Section ──────────────────────────────────────────────────
def render_schema_section():
    st.title("🗺 Graph Schema Inspector")
    st.markdown(
        "Inspect exactly what LLM Graph Builder created in your Neo4j Aura database — "
        "labels, property keys, sample values, and relationship pairs. "
        "Use this to write correct Cypher queries."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📦 Load Cached Schema", use_container_width=True):
            success, schema = load_schema_from_cache()
            if not success:
                st.error("❌ No cached schema found. Please fetch live schema first.")
                return
            _render_schema(schema)

    with col2:
        if st.button("🔄 Fetch Live Schema", type="primary", use_container_width=True):
            with st.spinner("Connecting to Neo4j Aura and reading schema…"):
                success, schema = fetch_full_schema()
            if not success:
                st.error(f"❌ {schema}")
                return
            _render_schema(schema)


def _render_schema(schema: dict):
    import pandas as pd

    totals = schema.get("totals", {})
    labels = schema.get("labels", [])
    rels   = schema.get("relationships", [])

    # ── Summary metrics ───────────────────────────────────────────────────────
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔵 Total Nodes",        totals.get("nodes", 0))
    col2.metric("🔗 Total Relationships", totals.get("relationships", 0))
    col3.metric("🏷 Unique Labels",       len(labels))
    col4.metric("🔀 Relationship Types",  len(rels))

    # ── Node Labels ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔵 Node Labels & Properties")
    st.caption("Exact label names to use in Cypher — copy them precisely.")

    if not labels:
        st.warning("No node labels found in the database.")
    else:
        # Status legend
        st.markdown(
            "🟢 **Populated** (>0 nodes) &nbsp;|&nbsp; "
            "🔴 **Empty** (0 nodes) &nbsp;|&nbsp; "
            "🔑 `id` = primary property used by LLM Graph Builder"
        )
        st.markdown("")

        for lbl in labels:
            count = lbl["count"]
            # Status badge
            if count == "?" or count is None:
                badge = "⬜"
            elif int(count) == 0:
                badge = "🔴"
            elif int(count) >= 100:
                badge = "🟢 **Large**"
            elif int(count) >= 10:
                badge = "🟢"
            else:
                badge = "🟡 Small"

            with st.expander(
                f"{badge}  **:{lbl['label']}**  ·  {count} node(s)",
                expanded=False,
            ):
                props = lbl.get("properties", [])
                if not props:
                    st.info("No properties found — node may only have an `id` field.")
                else:
                    df = pd.DataFrame(props, columns=["key", "sample"])
                    df.columns = ["Property Key", "Sample Value"]
                    st.dataframe(df, use_container_width=True, hide_index=True)

                prop_keys = [p["key"] for p in props] if props else ["id"]
                st.markdown("**📋 Ready-to-use Cypher snippet:**")
                st.code(
                    f"MATCH (n:{lbl['label']}) RETURN {', '.join('n.' + k for k in prop_keys[:5])} LIMIT 10",
                    language="cypher",
                )

    # ── Relationships ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔗 Relationship Types")
    st.caption("Exact relationship names to use in Cypher.")

    if not rels:
        st.warning("No relationships found in the database.")
    else:
        # Summary table with real counts
        rel_rows = []
        for r in rels:
            pairs_str = ", ".join(f"(:{f})->(:{t})" for f, t in r["pairs"]) or "—"
            count = r["count"]
            if count != "?" and count is not None and int(count) == 0:
                status = "🔴 Empty"
            elif count == "?":
                status = "⬜ Unknown"
            else:
                status = "🟢 Active"
            rel_rows.append({
                "Status":            status,
                "Relationship Type": r["type"],
                "Count":             count,
                "Connects":          pairs_str,
            })
        st.dataframe(pd.DataFrame(rel_rows), use_container_width=True, hide_index=True)

        st.markdown("**📋 Query snippets per relationship:**")
        for r in rels:
            count_label = f"{r['count']} occurrence(s)" if r["count"] != "?" else "? occurrences"
            if r["pairs"]:
                from_lbl, to_lbl = r["pairs"][0]
                snippet = f"MATCH (a:{from_lbl})-[r:{r['type']}]->(b:{to_lbl})\nRETURN a, r, b LIMIT 10"
            else:
                snippet = f"MATCH (a)-[r:{r['type']}]->(b) RETURN a, r, b LIMIT 10"
            with st.expander(f"**:{r['type']}**  ·  {count_label}"):
                st.code(snippet, language="cypher")

    # ── What to do next ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("💡 What to do with this data")
    st.markdown("""
    **Your graph is a crime/news knowledge graph.** Here's how to use it:

    | Goal | What to do |
    |---|---|
    | Find crimes by a person | Use **Single Hop → "All relations of a Person"** template |
    | Map a crime network | Use **Path Query → "Crime network around a Person"** |
    | Find financial fraud | Use **Crime Analysis → "Financial fraud connections"** |
    | See kills/murders | Use **Crime Analysis → "Killed / Murder relationships"** |
    | Check who's not arrested | Use **Crime Analysis → "Accused persons not yet arrested"** |
    | Explore raw chunks | Use **Multi Hop → "Chunk → Entities extracted"** |

    **Key tip:** Your graph uses `n.id` as the main property (not `n.name` or `n.title`).
    Always query with: `WHERE toLower(n.id) CONTAINS toLower('your search term')`
    """)

    with st.expander("🛠 Raw schema introspection queries"):
        st.code("""// All labels
CALL db.labels()

// All relationship types
CALL db.relationshipTypes()

// Count nodes per label — most useful
MATCH (n)
RETURN labels(n)[0] AS label, count(*) AS count
ORDER BY count DESC

// Sample any node to see its properties
MATCH (n) RETURN labels(n), keys(n), n LIMIT 5

// See all Entity subtypes
MATCH (n:Entity)
RETURN labels(n) AS all_labels, count(*) AS count
ORDER BY count DESC""", language="cypher")


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    render_sidebar()

    # Route to the correct section based on active mode
    mode = st.session_state.get("active_mode", "query")
    if mode == "query":
        render_query_section()
    elif mode == "finetune":
        render_validate_section()
    else:
        render_schema_section()


if __name__ == "__main__":
    main()