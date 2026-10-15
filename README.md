# Parts Counter

Upload a photo of the things you have and paste the list of what you need. The list can be anything: the electronic parts of a fan, a PC build, a recipe's ingredients, a shopping or school-supplies list. The app counts what's in the photo, checks it against your list and shows what's complete, short or missing, plus anything extra.

It uses Google's Gemini (`gemini-2.5-flash`). The model only reads the image and returns text, which the free API tier covers.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

export GEMINI_API_KEY=your-key-here   # get one at https://aistudio.google.com/apikey
.venv/bin/python app.py
```

Open http://localhost:5000.

To use a different Gemini model, set `GEMINI_MODEL` (default: `gemini-2.5-flash`).

## List format

Anything goes: parts, ingredients, groceries, school supplies, tools. Type the list however you like, one per line, comma-separated or as a sentence. Quantities can be `4x bolts`, `bolts x4`, `four bolts` or `4 bolts`, and no number means 1. Measured amounts like `500 ml milk` or `3 m wire` count as one item, and the notes say whether the amount looks sufficient.

The model splits and reads the list itself, so the "Need" column shows how it understood each line. Check it if a result looks off.

## Tips

- Spread items out on a plain, contrasting surface so nothing overlaps.
- Use good light and shoot from directly above.
- Small look-alike items (resistor values, screw sizes) are the hardest to count. Check the notes column for the model's doubts.
