# app.py
import os, re, asyncio, textwrap
from typing import Literal

import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from agents import Agent, Runner, function_tool, set_default_openai_client
from openai import AsyncOpenAI

# -----------------------------
# Setup (env / secrets)
# -----------------------------
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY is not set. Add it to .streamlit/secrets.toml or your environment.")
    st.stop()

# One-time client wiring (cache so Streamlit reruns don’t recreate)
@st.cache_resource(show_spinner=False)
def _init_openai_client():
    set_default_openai_client(AsyncOpenAI(api_key=OPENAI_API_KEY, timeout=120.0))
    return True

_init_openai_client()

# -----------------------------
# Pydantic Models (your schema)
# -----------------------------
class ClassificationModel(BaseModel):
    domain: Literal["coding","data","business","other"]
    type: Literal["how-to","debug","design","fact","other"]

class ScoresModel(BaseModel):
    clarity: int = Field(ge=0, le=10)
    specificity: int = Field(ge=0, le=10)
    answerability: int = Field(ge=0, le=10)
    safety: int = Field(ge=0, le=10)

class RewritesModel(BaseModel):
    minimal: str = Field(max_length=280, description="Minimal edit")
    ideal:   str = Field(max_length=280, description="Ideal rewrite")

class QuestionReview(BaseModel):
    original_question: str
    missing_info: list[str] = Field(default_factory=list)
    assumptions:  list[str] = Field(default_factory=list)
    followups:    list[str] = Field(default_factory=list)
    flags:        list[str] = Field(default_factory=list, description="['email','phone','card-ish','unsafe','vague']")
    classification: ClassificationModel
    scores: ScoresModel
    rewrites: RewritesModel

# -----------------------------
# Tool(s)
# -----------------------------
@function_tool
def pii_scan(text: str) -> list[str]:
    """Return PII flags if found (email, phone, card-ish)."""
    flags = []
    if re.search(r"\b[\w\.-]+@[\w\.-]+\.\w{2,}\b", text): flags.append("email")
    if re.search(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b", text): flags.append("phone")
    if re.search(r"\b(?:\d[ -]*?){13,16}\b", text): flags.append("card-ish")
    return flags

# -----------------------------
# Agent (cached)
# -----------------------------
@st.cache_resource(show_spinner=False)
def get_agent():
    return Agent(
        name="AskBetter",
        instructions=textwrap.dedent("""
            Evaluate the user's question and return a structured QuestionReview JSON object.
            1. classification: {domain, type}.
            2. scores: integers 0-10 for clarity, specificity, answerability, safety.
            3. missing_info (≤6 essentials), assumptions (≤6), followups (≤5 short).
            4. rewrites: minimal and ideal (each ≤280 chars; no markdown).
            5. Set original_question to the exact user input (verbatim).
            6. Always call pii_scan(text=original_question) and copy the result into flags.
            Return only valid JSON for QuestionReview.
        """).strip(),
        tools=[pii_scan],
        output_type=QuestionReview,
        model="gpt-4o-mini",
    )

ASK_BETTER = get_agent()

# -----------------------------
# Async runner helper
# -----------------------------
def run_async(coro):
    """Run an async coroutine from Streamlit safely."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        # Uncommon in Streamlit, but just in case:
        return asyncio.run(coro)  # type: ignore
    return loop.run_until_complete(coro)

# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="AskBetter – Question Quality Reviewer", page_icon="🧭", layout="wide")

st.title("🧭 AskBetter — Question Quality Reviewer")
st.caption("Judge question quality, surface missing info, and rewrite for quick answers.")

with st.sidebar:
    st.subheader("Settings")
    st.write("Model: `gpt-4o-mini` (from your code)")
    st.info("Tip: Put your `OPENAI_API_KEY` in `.streamlit/secrets.toml`")
    example = st.selectbox(
        "Examples",
        [
            "Fix this SQL?",
            "Can you email me at jane.doe@acme.com to fix my Postgres query?",
            "How to design a pricing experiment for our SaaS?",
        ],
        index=0,
    )
    if st.button("Use example"):
        st.session_state["user_q"] = example

user_q = st.text_area(
    "Paste a question to review",
    value=st.session_state.get("user_q", ""),
    placeholder="e.g., How do I index a JSONB column in Postgres?",
    height=120,
)

col_a, col_b = st.columns([1, 4])
with col_a:
    run_btn = st.button("Analyze", type="primary")
with col_b:
    st.write("")

if run_btn:
    if not user_q.strip():
        st.warning("Please enter a question.")
        st.stop()

    with st.spinner("Scoring and rewriting…"):
        result = run_async(Runner.run(ASK_BETTER, user_q))
        out: QuestionReview = result.final_output

        # Enforce ground truth for original_question (belt & suspenders)
        if out.original_question.strip() != user_q.strip():
            out = out.model_copy(update={"original_question": user_q})

    # -------------------------
    # Summary header
    # -------------------------
    st.subheader("Result")

    c1, c2, c3 = st.columns([1.1, 1.1, 3])
    with c1:
        st.markdown("**Domain**")
        st.code(out.classification.domain)
    with c2:
        st.markdown("**Type**")
        st.code(out.classification.type)
    with c3:
        st.markdown("**Flags**")
        if out.flags:
            st.write(" ".join(f"`{f}`" for f in out.flags))
        else:
            st.write("`none`")

    # -------------------------
    # Scores
    # -------------------------
    st.markdown("### Scores (0–10)")
    s = out.scores
    s_cols = st.columns(4)
    for i, (label, value) in enumerate(
        [("clarity", s.clarity), ("specificity", s.specificity), ("answerability", s.answerability), ("safety", s.safety)]
    ):
        with s_cols[i]:
            st.metric(label.capitalize(), value)

    # -------------------------
    # Missing info / Assumptions / Followups
    # -------------------------
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### Missing info")
        if out.missing_info:
            for item in out.missing_info[:6]:
                st.write(f"- {item}")
        else:
            st.write("_none_")
    with col2:
        st.markdown("#### Assumptions")
        if out.assumptions:
            for item in out.assumptions[:6]:
                st.write(f"- {item}")
        else:
            st.write("_none_")
    with col3:
        st.markdown("#### Follow-ups")
        if out.followups:
            for item in out.followups[:5]:
                st.write(f"- {item}")
        else:
            st.write("_none_")

    # -------------------------
    # Rewrites
    # -------------------------
    st.markdown("### Rewrites (≤280 chars)")
    r1, r2 = st.columns(2)
    with r1:
        st.markdown("**Minimal**")
        st.text_area("",
                     out.rewrites.minimal,
                     height=120,
                     label_visibility="hidden")
        st.caption(f"Length: {len(out.rewrites.minimal)}")
        st.button("Copy minimal", key="copy_min", on_click=lambda: st.session_state.update(_copied_min=True))
        if st.session_state.get("_copied_min"):
            st.toast("Minimal rewrite copied (select + Cmd/Ctrl+C).")

    with r2:
        st.markdown("**Ideal**")
        st.text_area("",
                     out.rewrites.ideal,
                     height=120,
                     label_visibility="hidden")
        st.caption(f"Length: {len(out.rewrites.ideal)}")
        st.button("Copy ideal", key="copy_ideal", on_click=lambda: st.session_state.update(_copied_ideal=True))
        if st.session_state.get("_copied_ideal"):
            st.toast("Ideal rewrite copied (select + Cmd/Ctrl+C).")

    # -------------------------
    # Raw JSON
    # -------------------------
    with st.expander("Raw JSON (QuestionReview)"):
        st.json(out.model_dump())

# Footer
st.markdown("---")
st.caption("AskBetter • Streamlit UI. Powered by OpenAI Agents SDK + Pydantic.")

