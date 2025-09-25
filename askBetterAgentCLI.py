import asyncio
from dotenv import load_dotenv
import os, re, sys
from datetime import date
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from typing import Literal
# Agents SDK + OpenAI client
from agents import Agent, Runner, tool,function_tool, set_default_openai_client
from openai import AsyncOpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set")

# Wire the client once for all agents
set_default_openai_client(AsyncOpenAI(api_key=api_key, timeout=120.0))

# ---------- Models ----------
class ClassificationModel(BaseModel):
    domain: Literal["coding","data","business","other"]
    type: Literal["how-to","debug","design","fact","other"]

class ScoresModel(BaseModel):
    clarity: int = Field(..., ge=0, le=10)
    specificity: int = Field(..., ge=0, le=10)
    answerability: int = Field(..., ge=0, le=10)
    safety: int = Field(..., ge=0, le=10)

class RewritesModel(BaseModel):
    minimal: str = Field(max_length=280, description="Minimal edit")
    ideal: str = Field(max_length=280, description="Ideal rewrite")

class QuestionReview(BaseModel):
    original_question: str
    missing_info: list[str]
    assumptions: list[str]
    followups: list[str]
    flags: list[str] = Field(default_factory=list, description="['email','phone','card-ish','unsafe','vague']")
    classification: ClassificationModel
    scores: ScoresModel
    rewrites: RewritesModel


# ---------- Tool(s) ----------
@function_tool
def pii_scan(text: str) -> list[str]:
    """Return PII flags if found (email, phone, card-ish)."""
    flags = []
    if re.search(r"\b[\w\.-]+@[\w\.-]+\.\w{2,}\b", text): flags.append("email")
    if re.search(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b", text): flags.append("phone")
    if re.search(r"\b(?:\d[ -]*?){13,16}\b", text): flags.append("card-ish")
    return flags

# ---------- Agent ----------
AskBetter_agent = Agent(
    name="AskBetter",
    instructions=(
        "Evaluate the user's question and return a structured QuestionReview JSON object.\n"
        "1. Fill the 'classification' object with a 'domain' and 'type'.\n"
        "2. Fill the 'scores' object with 0-10 scores for 'clarity', 'specificity', 'answerability', and 'safety'.\n"
        "3. Fill the 'missing_info' list with essentials needed to answer (max 6).\n"
        "4. Fill the 'assumptions' list with reasonable defaults you'd make (max 6).\n"
        "5. Fill the 'followups' list with short, targeted questions (max 5).\n"
        "6. Fill the 'rewrites' object with a 'minimal' and an 'ideal' rewrite (max 280 chars each).\n"
        "7. Call pii_scan(text=original_question) and copy the result into flags."
    ),
    tools=[pii_scan],
    output_type=QuestionReview,
    model="gpt-4o-mini", # Using a slightly more powerful model can also improve reliability.
)

# ---------- Runner ----------
async def main(user_question: str):
    result = await Runner.run(AskBetter_agent, user_question)
    out = result.final_output

    # enforce ground truth
    if out.original_question.strip() != user_question.strip():
        out = out.model_copy(update={"original_question": user_question})

    print(out.model_dump_json(indent=2))

if __name__ == "__main__":
    user_q = " ".join(sys.argv[1:]).strip()
    if not user_q:
        # fall back to interactive prompt
        user_q = input("Enter your question: ").strip()
    if not user_q:
        print("No question provided. Exiting.")
        raise SystemExit(1)
    asyncio.run(main(user_q))
