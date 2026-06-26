# SmartResearch Engine 🔬
**AI-Powered Academic Paper Analysis**
*By Malak Naimi (202210733) & Riham Halaika (202211632)*

---

## Project Structure

```
SmartResearch/
├── app.py                  # Flask web server & API routes
├── research_engine.py      # All AI/analysis logic
├── config.py               # API keys configuration
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html          # Main UI
├── static/
│   ├── css/style.css       # Styling (dark theme)
│   └── js/app.js           # Frontend logic
└── uploads/                # Temporary PDF storage (auto-created)
```

---

## Quick Start

### 1. Navigate into the project folder
```bash
cd SmartResearch
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API keys in `config.py`

| API               | Cost   | Key Required | Get It                                         |
|-------------------|--------|-------------|------------------------------------------------|
| Semantic Scholar  | FREE   | No          | Automatic                                      |
| arXiv             | FREE   | No          | Automatic                                      |
| OpenAlex          | FREE   | No (add email) | Just add your email in config.py            |
| HuggingFace       | FREE   | Yes (optional) | https://huggingface.co/settings/tokens      |

Open `config.py` and fill in:
```python
HUGGINGFACE_API_KEY = "hf_your_key_here"
OPENALEX_EMAIL      = "your@email.com"
```
> HuggingFace is optional — the app uses a basic extractive summarizer if no key is set.

### 4. Run
```bash
python app.py
```
Open your browser at: **http://127.0.0.1:5000**

---

## Features

### 01 — Search Topic
Enter any research topic and the engine will:
- Query **Semantic Scholar** and **arXiv** simultaneously
- Extract the **top 10 key research themes**
- Plot a **publication timeline**
- Detect **research gaps** by comparing your results to a broader arXiv sample
- Generate a full downloadable **Markdown report**

### 02 — Analyse Your Paper (Upload PDF)
Upload any academic PDF and get:
- A **clear, full, ordered abstraction** — section by section, in the order the paper is written:
  1. Overview & Purpose
  2. Problem Statement & Motivation
  3. Background & Context
  4. Literature Review / Related Work
  5. Methodology / Proposed Approach
  6. Experiments & Evaluation
  7. Results & Findings
  8. Discussion
  9. Conclusions
  10. Limitations / Future Directions
- **Key findings** sentences extracted from the text
- **Topics cloud** from the paper's own keywords
- **Gap / future-work sentences** detected from the text

---

## APIs Used

| API               | Endpoint                                      | Limit                        |
|-------------------|-----------------------------------------------|------------------------------|
| Semantic Scholar  | https://api.semanticscholar.org/graph/v1/     | 100 req / 5 min              |
| arXiv             | http://export.arxiv.org/api/                  | No strict limit              |
| OpenAlex          | https://api.openalex.org/                     | 100 000 req / day (with email) |
| HuggingFace BART  | https://api-inference.huggingface.co/         | ~30 000 tokens / month (free) |

---

## Troubleshooting

**No papers found?**
- Try broader search terms (e.g. "machine learning" instead of a very specific phrase)
- Check your internet connection

**PDF upload fails?**
- Make sure the PDF is text-based, not a scanned image
- File must be under 16 MB
- Password-protected PDFs are not supported

**Summarization not working?**
- Add a HuggingFace API key to `config.py`
- Without it the app falls back to extractive summarization (still works fine)
