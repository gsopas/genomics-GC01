import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ CORS: wildcard origins, χωρίς credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # ή βάλε το Bolt URL εδώ για πιο αυστηρό CORS
    allow_credentials=False,  # σημαντικό για να μην μπλοκάρει ο browser
    allow_methods=["*"],
    allow_headers=["*"],
)

class DnaIn(BaseModel):
    sequence: str

def rev_comp(seq: str) -> str:
    comp = str.maketrans("ACGTacgtnN", "TGCAtgcanN")
    return seq.translate(comp)[::-1]

def gc_percent(seq: str) -> float:
    s = seq.upper()
    if len(s) == 0 or any(c not in "ACGTN" for c in s):
        raise ValueError("Sequence must contain only A/C/G/T/N and not be empty.")
    gc = s.count("G") + s.count("C")
    n  = s.count("N")
    denom = len(s) - n
    return 0.0 if denom == 0 else round(100.0 * gc / denom, 2)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/gc")
def gc_endpoint(inp: DnaIn):
    try:
        return {"gc_percent": gc_percent(inp.sequence)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/revcomp")
def revcomp_endpoint(inp: DnaIn):
    try:
        return {"revcomp": rev_comp(inp.sequence)}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid sequence.")

# Optional LLM explain
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

@app.post("/explain")
def explain_endpoint(inp: DnaIn):
    if not client:
        raise HTTPException(status_code=501, detail="LLM not configured.")
    prompt = (
        "Explain briefly what is notable about this DNA snippet. "
        "Include GC%, length, and whether reverse-complement suggests palindromic hints. "
        f"DNA: {inp.sequence}"
    )
    try:
        msg = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return {"explanation": msg.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
