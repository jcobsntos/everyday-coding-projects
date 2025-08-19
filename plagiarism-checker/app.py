import os
import io
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from utils import (
    extract_text_from_file,
    sample_random_phrases,
    search_web_for_phrase,
    fetch_and_clean_url,
    compute_similarity_report,
)
from pdf_report import render_results_pdf

ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def allowed_file(filename: str):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/analyze")
def analyze():
    if "file" not in request.files:
        flash("No file part in the request.", "danger")
        return redirect(url_for("index"))

    f = request.files["file"]
    if f.filename == "":
        flash("No selected file.", "warning")
        return redirect(url_for("index"))

    if not allowed_file(f.filename):
        flash("Unsupported file type. Upload TXT, PDF, or DOCX.", "danger")
        return redirect(url_for("index"))

    filename = secure_filename(f.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], f"{int(time.time())}_{filename}")
    f.save(path)

    try:
        source_text = extract_text_from_file(path)

        # Sample longer phrases for better search
        phrases = sample_random_phrases(source_text, n_phrases=5, min_words=10, max_words=30)

        scraped_docs = []
        for phrase in phrases:
            results = search_web_for_phrase(phrase, top_k=5)
            for r in results:
                cleaned = fetch_and_clean_url(r["url"], timeout=5)
                if cleaned and len(cleaned.split()) > 50:
                    scraped_docs.append({
                        "url": r["url"],
                        "title": r.get("title"),
                        "snippet": r.get("snippet"),
                        "content": cleaned,  # important for RapidFuzz
                        "query_phrase": phrase,
                    })

        report = compute_similarity_report(source_text, scraped_docs)

        return render_template(
            "results.html",
            report=report,
            phrases=phrases,
            uploaded_filename=filename,
            analyzed_at=datetime.utcnow(),
        )

    except Exception as exc:
        flash(f"Error during analysis: {exc}", "danger")
        return redirect(url_for("index"))


@app.post("/export-pdf")
def export_pdf():
    html = request.form.get("html_payload")
    if not html:
        flash("No data to export.", "warning")
        return redirect(url_for("index"))

    pdf_bytes = render_results_pdf(html)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="plagiarism_report.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)
