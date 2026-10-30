# Classic IR Model Demonstrator

A Flask educational application demonstrating three classic Information Retrieval approaches:
- **Boolean Model** — AND, OR, NOT with parentheses and AND-before-OR precedence.
- **Vector Space Model** — TF-IDF term weighting and cosine similarity ranking.
- **Fuzzy Set Model** — partial matching using Jaccard similarity as a 0–1 membership score.

## Features
- Six sample documents are inserted automatically on first run.
- Upload and index TXT, PDF, and DOCX documents.
- Search the stored collection using any of the three models.
- View ranked results and relevance scores.
- SQLite persistence and a health-check endpoint.
- Basic text normalization: tokenization, stop-word removal, and a small educational suffix stemmer.

## Setup (Windows PowerShell)
```powershell
cd classic_ir_model_demonstrator
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.

## Setup (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Run tests
```bash
pytest -q
```

## Docker
```bash
docker build -t classic-ir-demo .
docker run --rm -p 5000:5000 -v ir_data:/app/instance -v ir_uploads:/app/uploads classic-ir-demo
```
Open http://127.0.0.1:5000

## Jenkins
A sample `Jenkinsfile` is included. Configure a Pipeline job pointing to this Git repository. The Jenkins agent must have Python 3 and pip available. The pipeline installs dependencies and runs pytest.

## Project structure
```text
classic_ir_model_demonstrator/
├── app.py
├── requirements.txt
├── README.md
├── Dockerfile
├── Jenkinsfile
├── .gitignore
├── templates/
│   ├── base.html
│   ├── index.html
│   └── results.html
├── static/style.css
├── tests/test_app.py
├── uploads/
└── instance/
```

## Notes / academic scope
- The stemmer is intentionally a small educational suffix stemmer, not a full Porter implementation.
- The Fuzzy Set model uses Jaccard similarity over unique preprocessed query/document terms as an illustrative membership function.
- Boolean retrieval returns exact matches and does not rank matching documents.
- PDF uploads require selectable/extractable text; scanned image-only PDFs need OCR, which is not included.
- This is a classroom demonstrator, not a production search service.
