import os
import random
import requests
import docx
import PyPDF2
from bs4 import BeautifulSoup
from urllib.parse import quote
from rapidfuzz import fuzz
import numpy as np
from dotenv import load_dotenv

# Load .env
load_dotenv()

# --- Google CSE Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CX = os.getenv("GOOGLE_CSE_ID")


# --- File extractors ---
def extract_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == ".pdf":
        text = ""
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    elif ext == ".docx":
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError("Unsupported file type.")


# --- Phrase sampler ---
def sample_random_phrases(text: str, n_phrases=5, min_words=10, max_words=30):
    words = text.split()
    if len(words) < min_words:
        return [text]

    phrases = []
    for _ in range(n_phrases):
        start = random.randint(0, max(0, len(words) - max_words))
        length = random.randint(min_words, max_words)
        phrase = " ".join(words[start:start + length])
        phrases.append(phrase)
    return phrases


# --- Google CSE search ---
def search_web_for_phrase(phrase: str, top_k=5):
    results = []
    phrase = phrase.strip()
    if len(phrase) > 200:
        phrase = phrase[:200] + "..."
    query = quote(f'"{phrase}"')

    url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={CX}&q={query}&num={top_k}"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        for item in items:
            results.append({
                "url": item.get("link"),
                "title": item.get("title"),
                "snippet": item.get("snippet"),
            })
    except Exception as e:
        print(f"CSE search error: {e}")
    return results


# --- Fetch and clean webpage ---
def fetch_and_clean_url(url: str, timeout=5):
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.extract()
        text = soup.get_text(separator=" ")
        return " ".join(text.split())
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
        return ""


# --- Similarity Report using RapidFuzz ---
def compute_similarity_report(user_text: str, sources: list):
    """
    Computes similarity using sentence-level fuzzy matching (RapidFuzz)
    Returns overall similarity, mean top 5, and per-source overlaps
    """
    results = []

    for s in sources:
        content = s.get("content", "")
        overlaps = []

        # Split into sentences
        user_sentences = [sent.strip() for sent in user_text.split(".") if sent.strip()]
        source_sentences = [sent.strip() for sent in content.split(".") if sent.strip()]

        for us in user_sentences:
            # Find best matching sentence in source
            best_match = max(
                [(ss, fuzz.token_set_ratio(us, ss)) for ss in source_sentences],
                key=lambda x: x[1],
                default=("", 0)
            )
            if best_match[1] >= 70:  # threshold for similarity
                overlaps.append({
                    "source_excerpt": best_match[0][:200],
                    "score": best_match[1]
                })

        similarity = np.mean([o["score"] for o in overlaps]) if overlaps else 0

        results.append({
            "title": s.get("title") or "Untitled",
            "url": s.get("url"),
            "similarity": round(similarity, 2),
            "query_phrase": s.get("query_phrase"),
            "overlaps": overlaps
        })

    results.sort(key=lambda r: r["similarity"], reverse=True)
    overall = np.mean([r["similarity"] for r in results]) if results else 0
    top5 = np.mean([r["similarity"] for r in results[:5]]) if results else 0

    return {
        "overall_similarity": round(overall, 2),
        "mean_top5_similarity": round(top5, 2),
        "num_sources": len(results),
        "by_url": results
    }
