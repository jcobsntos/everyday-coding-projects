# Plagiarism Checker – Flask App

## Quick Start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit .env and set SERPAPI_API_KEY
flask --app app run
```

Upload a `.docx`, `.pdf`, or `.txt`. The app samples random 5–10 word phrases, searches Google (via SerpAPI), scrapes the top results, cleans text with Trafilatura, computes TF‑IDF cosine similarity and fuzzy overlaps, then displays an overall score and per‑URL matches. You can download a PDF report.
