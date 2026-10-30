from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from pathlib import Path
import sqlite3, math, re, os
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
INSTANCE_DIR = BASE_DIR / "instance"
DB_PATH = INSTANCE_DIR / "ir_documents.db"
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-key-change-me")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

STOP_WORDS = set("""
a an the and or but if while with to of in on for from by as at is are was were be been
being this that these those it its into about over after before between through during
we you your they them he she his her i me my our their can could should would will just
""".split())

def get_db():
    INSTANCE_DIR.mkdir(exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        count = db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        if count == 0:
            samples = [
                ("Information Retrieval Basics", "information retrieval systems search a collection of documents and return documents relevant to a user query. An IR system includes document processing indexing query processing and ranking."),
                ("Boolean Retrieval Model", "the Boolean retrieval model represents documents using terms and retrieves documents through logical operators AND OR and NOT. A Boolean query matches documents exactly according to its logical expression."),
                ("Vector Space Model and TF-IDF", "the vector space model represents documents and queries as weighted term vectors. TF-IDF gives higher weight to terms that are frequent in a document but rare across the collection. Cosine similarity measures the angle between vectors."),
                ("Precision and Recall", "precision is the fraction of retrieved documents that are relevant. Recall is the fraction of all relevant documents that are retrieved. F1 score is the harmonic mean of precision and recall."),
                ("Text Preprocessing", "text preprocessing includes tokenization stop word removal and stemming. Tokenization splits text into terms. Stop word removal removes common words. Stemming reduces words to a root form."),
                ("Fuzzy Set Retrieval", "fuzzy information retrieval allows partial matching. A document can have a degree of membership between zero and one for a query. Fuzzy union uses maximum and fuzzy intersection uses minimum.")
            ]
            db.executemany("INSERT INTO documents(title, filename, content) VALUES (?, NULL, ?)", samples)

def extract_text(path, ext):
    if ext == "txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == "pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    if ext == "docx":
        from docx import Document
        return "\n".join(p.text for p in Document(str(path)).paragraphs)
    return ""

def tokenize(text):
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [w for w in words if w not in STOP_WORDS]

def stem(word):
    # Small educational suffix stemmer (not a full Porter stemmer).
    for suffix in ("ingly", "edly", "ing", "ed", "ies", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[:-len(suffix)] + ("y" if suffix == "ies" else "")
    return word

def terms(text):
    return [stem(w) for w in tokenize(text)]

def get_documents():
    with get_db() as db:
        return db.execute("SELECT id, title, filename, content, created_at FROM documents ORDER BY id DESC").fetchall()

def boolean_search(query, docs):
    # Supports terms, parentheses, AND, OR, NOT. AND has higher precedence than OR.
    tokens = re.findall(r"\(|\)|\bAND\b|\bOR\b|\bNOT\b|[A-Za-z0-9_]+", query, flags=re.I)
    if not tokens:
        return [], "Enter a Boolean query, e.g. information AND retrieval."
    normalized = [t.upper() if t.upper() in {"AND","OR","NOT"} else t.lower() for t in tokens]
    def evaluate_doc(text):
        present = set(terms(text))
        output, ops = [], []
        precedence = {"OR": 1, "AND": 2, "NOT": 3}
        def apply():
            op = ops.pop()
            if op == "NOT":
                if not output: raise ValueError("NOT needs a term after it.")
                output.append(not output.pop())
            else:
                if len(output) < 2: raise ValueError(f"{op} needs a term on both sides.")
                b, a = output.pop(), output.pop()
                output.append(a and b if op == "AND" else a or b)
        expect_operand = True
        for tok in normalized:
            if tok == "(":
                ops.append(tok); expect_operand = True
            elif tok == ")":
                while ops and ops[-1] != "(": apply()
                if not ops: raise ValueError("Mismatched parentheses.")
                ops.pop(); expect_operand = False
            elif tok in precedence:
                if tok == "NOT":
                    if not expect_operand: raise ValueError("Place NOT before a term.")
                else:
                    if expect_operand: raise ValueError(f"Missing term before {tok}.")
                while ops and ops[-1] in precedence and precedence[ops[-1]] >= precedence[tok] and tok != "NOT":
                    apply()
                ops.append(tok); expect_operand = True
            else:
                if not expect_operand: raise ValueError("Use AND, OR, or NOT between terms.")
                output.append(stem(tok)); expect_operand = False
        while ops:
            if ops[-1] == "(": raise ValueError("Mismatched parentheses.")
            apply()
        if len(output) != 1: raise ValueError("Invalid Boolean expression.")
        return bool(output[0])
    results = []
    try:
        for d in docs:
            if evaluate_doc(d["content"]):
                results.append({"doc": d, "score": 1.0, "score_label": "Exact match"})
    except ValueError as e:
        return [], str(e)
    return results, None

def vector_search(query, docs):
    q_terms = terms(query)
    if not q_terms: return [], "Enter a query containing searchable terms."
    doc_tokens = [terms(d["content"]) for d in docs]
    df = Counter(t for toks in doc_tokens for t in set(toks))
    n = len(docs) or 1
    def vector(tokens):
        counts = Counter(tokens)
        return {t: (1 + math.log(counts[t])) * (math.log((n + 1) / (df[t] + 1)) + 1) for t in counts}
    qv = vector(q_terms)
    qcounts = Counter(q_terms)
    qv = {t: (1 + math.log(qcounts[t])) * (math.log((n + 1) / (df[t] + 1)) + 1) for t in qcounts}
    def cosine(a,b):
        dot = sum(v*b.get(k,0) for k,v in a.items())
        na = math.sqrt(sum(v*v for v in a.values()))
        nb = math.sqrt(sum(v*v for v in b.values()))
        return dot/(na*nb) if na and nb else 0
    results = []
    for d, toks in zip(docs, doc_tokens):
        score = cosine(qv, vector(toks))
        if score > 0:
            results.append({"doc": d, "score": score, "score_label": f"{score:.4f}"})
    return sorted(results, key=lambda x: x["score"], reverse=True), None

def fuzzy_search(query, docs):
    q = set(terms(query))
    if not q: return [], "Enter a query containing searchable terms."
    results = []
    for d in docs:
        dt = set(terms(d["content"]))
        # Fuzzy membership: Jaccard similarity between query and document term sets.
        score = len(q & dt) / len(q | dt) if q | dt else 0
        if score > 0:
            results.append({"doc": d, "score": score, "score_label": f"{score:.4f}"})
    return sorted(results, key=lambda x: x["score"], reverse=True), None

@app.route("/")
def index():
    docs = get_documents()
    return render_template("index.html", documents=docs, count=len(docs))

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("document")
    if not file or not file.filename:
        flash("Choose a document to upload.", "error"); return redirect(url_for("index"))
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        flash("Supported formats: TXT, PDF, DOCX.", "error"); return redirect(url_for("index"))
    UPLOAD_DIR.mkdir(exist_ok=True)
    saved = UPLOAD_DIR / filename
    # Avoid overwriting an existing upload.
    if saved.exists():
        saved = UPLOAD_DIR / f"{saved.stem}_{os.urandom(3).hex()}{saved.suffix}"
    file.save(saved)
    try:
        content = extract_text(saved, ext).strip()
        if not content:
            raise ValueError("No readable text was found in this file.")
        with get_db() as db:
            db.execute("INSERT INTO documents(title, filename, content) VALUES (?, ?, ?)",
                       (Path(filename).stem, saved.name, content))
        flash(f"Uploaded and indexed: {filename}", "success")
    except Exception as exc:
        saved.unlink(missing_ok=True)
        flash(f"Could not read document: {exc}", "error")
    return redirect(url_for("index"))

@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("query", "").strip()
    model = request.form.get("model", "vsm")
    docs = get_documents()
    if model == "boolean":
        results, error = boolean_search(query, docs)
    elif model == "fuzzy":
        results, error = fuzzy_search(query, docs)
    else:
        model = "vsm"
        results, error = vector_search(query, docs)
    return render_template("results.html", query=query, model=model, results=results, error=error)

@app.route("/delete/<int:doc_id>", methods=["POST"])
def delete_document(doc_id):
    with get_db() as db:
        row = db.execute("SELECT filename FROM documents WHERE id=?", (doc_id,)).fetchone()
        db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    if row and row["filename"]:
        (UPLOAD_DIR / row["filename"]).unlink(missing_ok=True)
    flash("Document deleted.", "success")
    return redirect(url_for("index"))

@app.route("/health")
def health():
    return {"status": "ok", "application": "Classic IR Model Demonstrator"}, 200

init_db()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)