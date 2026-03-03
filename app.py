# app_streamlit.py

import sys
import os
import tempfile
import json
from pathlib import Path
from datetime import datetime
from collections import Counter
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

# Ensure local modules are importable
sys.path.insert(0, ".")



# --------- SAFE MODULE LOADING ---------
@st.cache_resource
def load_modules():
    modules = {}

    # Core analyzer (required)
    try:
        from code_quality_analyzer import CodeQualityAnalyzer
        modules["analyzer"] = CodeQualityAnalyzer()
    except Exception as e:
        st.error(f"❌ code_quality_analyzer.py required, import failed: {e}")
        st.stop()

    # Config (optional)
    try:
        from config_loader import load_config
        modules["config"] = load_config()
    except Exception:
        modules["config"] = {}

    # Engines (optional)
    try:
        from autofix_engine import AutoFixEngine
        modules["autofix"] = AutoFixEngine()
    except Exception:
        modules["autofix"] = None

    try:
        from ollama_engine import OllamaReviewEngine
        modules["ollama"] = OllamaReviewEngine()
    except Exception:
        modules["ollama"] = None

    try:
        from openrouter_engine import OpenRouterReviewEngine
        modules["openrouter"] = OpenRouterReviewEngine()
    except Exception:
        modules["openrouter"] = None

    try:
        from rule_based_engine import RuleBasedEngine
        modules["rulebased"] = RuleBasedEngine()
    except Exception:
        modules["rulebased"] = None

    modules["status"] = "✅ Modules loaded"
    return modules



modules = load_modules()
analyzer = modules["analyzer"]
config = modules.get("config", {})

analysis_ran = False
project_metrics = None
smells = [] 

# ---------- PAGE CONFIG & THEME ----------
st.set_page_config(
    page_title="AI Code Reviewer Pro",
    page_icon="🚀",
    layout="wide",
)

st.markdown(
    """
    <style>
    .big-title {
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    .sub-title {
        font-size: 16px;
        opacity: 0.8;
        margin-bottom: 1rem;
    }
    .metric-green {
        color: #1DB954;
        font-weight: 600;
    }
    .metric-red {
        color: #FF4B4B;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="big-title">🚀 AI Code Reviewer Pro</div>
    <div class="sub-title">
        Static analysis + AI review + auto-fix, powered by your local engines and OpenRouter/Ollama.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("ℹ️ Runtime status", expanded=False):
    st.write(modules["status"])
    st.write(
        {
            "AutoFixEngine": modules["autofix"] is not None,
            "OllamaReviewEngine": modules["ollama"] is not None,
            "OpenRouterReviewEngine": modules["openrouter"] is not None,
            "RuleBasedEngine": modules["rulebased"] is not None,
        }
    )

# ---------- SIDEBAR CONTROLS ----------
 

st.sidebar.header("Project input")

input_mode = st.sidebar.radio(
    "Source",
    ["Single file", "Upload .zip / folder snapshot"],
    index=0,
)

uploaded_file = None
project_root: Path | None = None

if input_mode == "Single file":
    code_file = st.sidebar.file_uploader("Upload a Python file", type=["py"])
    if code_file:
        tmp_dir = Path(tempfile.mkdtemp())
        project_root = tmp_dir
        target_path = tmp_dir / code_file.name
        target_path.write_bytes(code_file.read())
        uploaded_file = target_path
else:
    zip_file = st.sidebar.file_uploader("Upload a zipped project", type=["zip"])
    if zip_file:
        import zipfile

        tmp_dir = Path(tempfile.mkdtemp())
        project_root = tmp_dir
        zip_path = tmp_dir / "project.zip"
        zip_path.write_bytes(zip_file.read())
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

run_button = st.sidebar.button("🔍 Run analysis", type="primary")

st.sidebar.markdown("---")
st.sidebar.header("AI settings")

use_openrouter = st.sidebar.checkbox("Use OpenRouter AI (cloud)", value=True)
use_ollama = st.sidebar.checkbox("Use Ollama AI (local)", value=False)
use_rulebased = st.sidebar.checkbox("Include rule-based explanations", value=True)

enable_ai_autofix = st.sidebar.checkbox("Enable AI auto-fix", value=False)
only_safe_autofix = st.sidebar.checkbox("Only safe (unused imports) fixes", value=True)
selected_smells = st.sidebar.multiselect(
    "Smell types for AI auto-fix",
    ["long_method", "long_parameter_list", "missing_type_hints", "unused_imports"],
    default=["unused_imports"],
)

st.sidebar.markdown("---")
st.sidebar.header("Quality gate preview")
min_quality = st.sidebar.slider("Min average quality", 0.0, 10.0, 6.0, 0.5)


# ---------- HELPERS ----------
def _project_metrics_to_df(project_metrics: dict) -> pd.DataFrame:
    """Build per-file metrics table from the analyzer project_metrics structure."""
    rows = []
    for file_path, metrics in project_metrics.get("files", {}).items():
        smells = metrics.get("smells", [])  # ✅ Raw list from analyzer
        sev_counts = Counter(s["severity"] for s in smells)  # ✅ Compute from list
        rows.append(
            {
                "file": Path(file_path).name,
                "path": file_path,
                "smells": len(smells),  # ✅ len() of smells list
                "critical": sev_counts.get("critical", 0),
                "high": sev_counts.get("high", 0),
                "medium": sev_counts.get("medium", 0),
                "low": sev_counts.get("low", 0),
                "quality_score": metrics.get("quality_score", 0.0),
            }
        )
    return pd.DataFrame(rows)



def _render_smell_table(smells) -> pd.DataFrame:
    rows = []
    for s in smells:
        rows.append(
            {
                "file": Path(s.file).name,
                "path": s.file,
                "line": s.line,
                "type": s.type,
                "node": getattr(s, "node_name", getattr(s, "nodename", "")),
                "description": s.description,
                "severity": getattr(s, "severity", "low"),
            }
        )
    return pd.DataFrame(rows)


# ---------- MAIN LAYOUT ----------
tab_overview, tab_smells, tab_ai, tab_autofix, tab_reports = st.tabs(
    [
        "📊 Overview",
        "🐛 Smells",
        "🤖 AI Review",
        "🛠 Auto-fix",
        "📂 Reports & Export",
    ]
)

# analysis_ran = False
# project_metrics = None
# smells = []

if run_button:
    if project_root is None:
        st.error("Please upload a file or project first.")
    else:
        analysis_ran = True

        # Reset analyzer state for repeated runs
        analyzer.reset() if hasattr(analyzer, "reset") else None

        # Run static analysis on file or project
        if uploaded_file is not None and uploaded_file.is_file():
            analyzer.analyze_file(str(uploaded_file))
            project_metrics = analyzer.compute_project_metrics()
        else:
            _ = analyzer.analyze_project(str(project_root))
            project_metrics = analyzer.compute_project_metrics()

        smells = analyzer.smells


# -------------- OVERVIEW TAB --------------
with tab_overview:
    if not analysis_ran or project_metrics is None:
        st.info("Run an analysis to see project overview.")
    else:
        left, mid, right = st.columns(3)

        avg_quality = project_metrics.get("avg_quality_score", 0.0)
        total_smells = project_metrics.get("total_smells", 0)
        sev = project_metrics.get("severity_distribution", {})

        with left:
            st.metric(
                "Average quality score",
                f"{avg_quality:.1f} / 10",
                delta=None,
            )
        with mid:
            st.metric("Total code smells", int(total_smells))
        with right:
            crit = sev.get("critical", 0)
            high = sev.get("high", 0)
            med = sev.get("medium", 0)
            low = sev.get("low", 0)
            st.metric("Critical / High / Medium / Low", f"{crit} / {high} / {med} / {low}")

        st.markdown("---")

        df_files = _project_metrics_to_df(project_metrics)
        if not df_files.empty:
            c1, c2 = st.columns([2, 3])

            with c1:
                st.subheader("Per-file quality")
                st.dataframe(
                    df_files[["file", "smells", "critical", "high", "medium", "low", "quality_score"]],
                    use_container_width=True,
                )

            with c2:
                st.subheader("Severity distribution")
                sev_df = (
                    pd.DataFrame(
                        [
                            {"severity": k.capitalize(), "count": v}
                            for k, v in sev.items()
                        ]
                    )
                    if sev
                    else pd.DataFrame(columns=["severity", "count"])
                )

                if not sev_df.empty:
                    fig = px.bar(
                        sev_df,
                        x="severity",
                        y="count",
                        color="severity",
                        title="Smells by severity",
                    )
                    st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Quality gate status")

        gate_pass = (avg_quality >= min_quality) and (
            sev.get("medium", 0) == 0
            and sev.get("high", 0) == 0
            and sev.get("critical", 0) == 0
        )

        if gate_pass:
            st.success(
                f"✅ Gate PASSED: quality {avg_quality:.1f} ≥ {min_quality:.1f}, no medium/high/critical smells."
            )
        else:
            st.error(
                f"🚫 Gate FAILED: quality {avg_quality:.1f} < {min_quality:.1f} "
                f"or non-low severity smells present."
            )


# -------------- SMELLS TAB --------------
with tab_smells:
    if not analysis_ran or not smells:
        st.info("No smells to display yet. Run analysis first.")
    else:
        st.subheader("Detected code smells")

        df_smells = _render_smell_table(smells)

        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            selected_severity = st.multiselect(
                "Filter by severity",
                sorted(df_smells["severity"].unique()),
                default=list(sorted(df_smells["severity"].unique())),
            )
        with filter_col2:
            selected_type = st.multiselect(
                "Filter by smell type",
                sorted(df_smells["type"].unique()),
                default=list(sorted(df_smells["type"].unique())),
            )

        mask = df_smells["severity"].isin(selected_severity) & df_smells["type"].isin(
            selected_type
        )
        st.dataframe(df_smells[mask], use_container_width=True)


# -------------- AI REVIEW TAB --------------
# -------------- AI REVIEW TAB (FIXED) --------------
with tab_ai:
    st.subheader("🤖 Ollama Debug")
    st.write(f"Smells: {len(smells)}")  # >0?
    st.write(f"Ollama engine: {modules.get('ollama')}")
    
    if smells and modules.get("ollama"):
        test_smell = smells[0]
        st.json({"file": test_smell.file, "type": test_smell.type, "line": test_smell.line})
        
        if st.button("Test Ollama on first smell"):
            try:
                review = modules["ollama"].get_review(test_smell)
                st.success(f"✅ Review: {review}")
            except Exception as e:
                st.error(f"❌ {type(e).__name__}: {e}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.error("No smells or Ollama not loaded")


# -------------- AUTO-FIX TAB --------------
with tab_autofix:
    if not analysis_ran or not smells:
        st.info("Run analysis to enable auto-fix.")
    elif modules["autofix"] is None:
        st.warning("AutoFixEngine not available. Check imports or installation.")
    else:
        st.subheader("Auto-fix engine")

        autofix_engine = modules["autofix"]

        mode = st.radio(
            "Fix mode",
            ["Safe only (unused imports)", "AI-powered (selected smells)"],
            index=0 if only_safe_autofix else 1,
        )

        if mode.startswith("AI") and not (use_openrouter or use_ollama):
            st.warning("Enable at least one AI engine in the sidebar for AI auto-fix.")
        else:
            fix_button = st.button("Apply fixes now")

            if fix_button:
                with st.spinner("Running auto-fix..."):
                    if mode.startswith("Safe"):
                        fixes = autofix_engine.apply_fixes(smells)
                    else:
                        # Rebuild engine with explicit engine choice if you want:
                        # from autofix_engine import AutoFixEngine
                        # autofix_engine = AutoFixEngine(use_openrouter=use_openrouter)
                        fixes = autofix_engine.apply_ai_fixes(
                            smells, allowed_smells=selected_smells
                        )

                from dataclasses import asdict

                fixes_dict = [asdict(fx) for fx in fixes]
                applied_count = sum(1 for fx in fixes if fx.applied)

                st.success(f"Applied {applied_count} fixes. See table below.")
                df_fixes = pd.DataFrame(fixes_dict)
                st.dataframe(df_fixes, use_container_width=True)

                # Save a local log
                log_name = f"applied_fixes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                if st.download_button(
                    "Download fixes log as JSON",
                    data=json.dumps(fixes_dict, indent=2, default=str),
                    file_name=log_name,
                    mime="application/json",
                ):
                    st.toast("Auto-fix log downloaded.")


# -------------- REPORTS TAB --------------
with tab_reports:
    st.subheader("Quality reports & exports")

    if not analysis_ran or project_metrics is None:
        st.info("Run analysis to generate reports.")
    else:
        col1, col2 = st.columns(2)

        # Export project metrics JSON
        with col1:
            st.write("Project metrics JSON")
            metrics_json = json.dumps(project_metrics, indent=2, default=str)
            st.code(metrics_json[:2000] + ("..." if len(metrics_json) > 2000 else ""))
            st.download_button(
                "Download project_quality_report.json",
                data=metrics_json,
                file_name="project_quality_report.json",
                mime="application/json",
            )

        # Export smells CSV
        with col2:
            st.write("Smells CSV")
            if smells:
                df_smells = _render_smell_table(smells)
                csv_bytes = df_smells.to_csv(index=False).encode("utf-8")
                st.dataframe(df_smells.head(50), use_container_width=True)
                st.download_button(
                    "Download smells.csv",
                    data=csv_bytes,
                    file_name="smells.csv",
                    mime="text/csv",
                )

        st.markdown("---")
        st.write(
            "You can also run the CLI for CI/Pre-commit gates, docstring coverage, "
            "and batch quality checks (see cli.py commands: scan, review, apply, docstrings, gate)."
        )
