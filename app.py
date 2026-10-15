import os

from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload

_client = None


def get_client():
    """Create the Gemini client on first use, so the page still loads if the key is missing."""
    global _client
    if _client is None:
        _client = genai.Client()  # reads GEMINI_API_KEY from the environment
    return _client

PROMPT = """You are a careful inventory checker. The photo shows things someone has bought or gathered.
Context: {context}

Required list, exactly as the user typed it (any format, any kind of things):
<<<
{items}
>>>

Step 1: Split the list into separate required items, in the order given. For each, decide `need`:
the number of separate physical units required. "4x bolts", "bolts x4", "four bolts" and "4 bolts" all mean 4.
A measured amount ("500 ml milk", "2 cups sugar", "3 m wire", "16 GB RAM") is NOT a unit count:
use need = 1 (one container/roll/stick) unless the line clearly says more, and put the amount in `name`.
Keep `name` short and recognisable.

Step 2: For every item, set `have` to how many matching physical units are visible in the photo.
- Count individual units (5 resistors = 5), not types. A pack counts as what it holds only if clearly labelled.
- Match by meaning, not exact wording ("10k resistor" matches a brown-black-orange banded resistor).
- If an item is not visible, have = 0. Don't count hidden or ambiguous things; explain doubts in `notes`.
- For measured amounts, note in `notes` whether the visible quantity looks sufficient, if you can tell.
- Never count the same physical object for two different list items.

Step 3: List anything visible that is NOT on the required list as extras, with counts.
Finish with a one or two sentence summary."""


class ItemCount(BaseModel):
    name: str
    need: int
    have: int
    notes: str


class Extra(BaseModel):
    name: str
    count: int


class Tally(BaseModel):
    items: list[ItemCount]
    extras: list[Extra]
    summary: str


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/tally")
def tally():
    photo = request.files.get("photo")
    if not photo or not photo.filename:
        return jsonify(error="Please upload a photo of your items."), 400

    items = request.form.get("items", "").strip()
    if not items:
        return jsonify(error="Please enter the list of required items."), 400

    context = request.form.get("context", "").strip() or "not given"

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        return jsonify(error="Server is missing GEMINI_API_KEY. Set it in the environment and redeploy."), 500

    try:
        response = get_client().models.generate_content(
            model=MODEL,
            contents=[
                PROMPT.format(context=context, items=items),
                types.Part.from_bytes(data=photo.read(), mime_type=photo.mimetype or "image/jpeg"),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=Tally,
                temperature=0,
            ),
        )
    except errors.APIError as e:
        if e.code == 429:
            return jsonify(error="Gemini quota reached for now. Wait a minute and try again."), 429
        return jsonify(error=f"Gemini request failed: {e.message}"), 502

    result = response.parsed
    if result is None:
        return jsonify(error="The model returned no usable answer. Try a clearer photo."), 502

    if not result.items:
        return jsonify(error="Couldn't find any items in your list. Put one thing per line or separate them with commas."), 400

    rows = []
    for c in result.items:
        need, have = max(c.need, 1), max(c.have, 0)
        status = "ok" if have >= need else "missing" if have == 0 else "short"
        rows.append(dict(name=c.name, need=need, have=have, status=status, notes=c.notes))

    extras = [e.model_dump() for e in result.extras if e.count > 0]
    return jsonify(
        rows=rows,
        extras=extras,
        summary=result.summary,
        totals=dict(
            required=sum(r["need"] for r in rows),
            matched=sum(min(r["have"], r["need"]) for r in rows),
            in_photo=sum(r["have"] for r in rows) + sum(e["count"] for e in extras),
            complete=sum(r["status"] == "ok" for r in rows),
            lines=len(rows),
        ),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
