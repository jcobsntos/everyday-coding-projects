import os
import random
import numpy as np
import requests
import docx
import PyPDF2
from bs4 import BeautifulSoup
from googlesearch import search   # install with: pip install google
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


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
def sample_random_phrases(text: str, n_phrases=10, min_words=5, max_words=10):
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


# --- Web search ---
def search_web_for_phrase(phrase: str, top_k=5):
    """Uses Google search to find results for a phrase."""
    results = []
    try:
        for url in search(f'"{phrase}"', num_results=top_k):
            results.append({"link": url, "title": url, "snippet": ""})
    except Exception as e:
        print("Search error:", e)
    return results


# --- Fetch and clean webpage ---
def fetch_and_clean_url(url: str, timeout=5):
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts & styles
        for tag in soup(["script", "style"]):
            tag.extract()

        text = soup.get_text(separator=" ")
        return " ".join(text.split())
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
        return ""


# --- Similarity Report ---
def compute_similarity_(user_text, sources):
    """
    user_text: str (uploaded document text)
    sources: list of dicts [{ "title": ..., "url": ..., "content": ..., "query_phrase": ... }]

    returns: dict with overall similarity, mean top 5, and per-source details
    """
    results = []

    # Prepare vectorizer
    documents = [user_text] + [s["content"] for s in sources]
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(documents)

    # Compute cosine similarities (compare doc[0] to others)
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    for i, s in enumerate(sources):
        sim = round(similarities[i] * 100, 2)  # percentage
        results.append({
            "title": s.get("title") or "Untitled",
            "url": s.get("url"),
            "similarity": sim,
            "query_phrase": s.get("query_phrase"),
            "overlaps": s.get("overlaps", [])
        })

    # Sort descending
    results.sort(key=lambda r: r["similarity"], reverse=True)

    overall = np.mean([r["similarity"] for r in results]) if results else 0
    top5 = np.mean([r["similarity"] for r in results[:5]]) if results else 0

    return {
        "overall_similarity": round(overall, 2),
        "mean_top5_similarity": round(top5, 2),
        "num_sources": len(results),
        "by_url": results
    }
