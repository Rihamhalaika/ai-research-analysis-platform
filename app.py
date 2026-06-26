"""
SmartResearch Engine - Main Flask Application
By Malak Naimi (202210733) & Riham Halaika (202211632)
"""

from flask import Flask, render_template, request, jsonify
import os
from research_engine import ResearchEngine

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024   # 16 MB max upload
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs('uploads', exist_ok=True)

engine = ResearchEngine()


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/search', methods=['POST'])
def search_topic():
    """Search academic databases and analyse a topic."""
    data = request.get_json()
    topic = data.get('topic', '').strip()
    max_papers = int(data.get('max_papers', 10))

    if not topic:
        return jsonify({'error': 'Topic is required'}), 400

    try:
        result = engine.search_and_analyze(topic, max_papers=max_papers)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_paper():
    """
    Accept a PDF upload and return a clear, full, ordered abstraction
    of what the paper covers — section by section.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are supported'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    try:
        result = engine.analyze_uploaded_paper(filepath)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/report', methods=['POST'])
def generate_report():
    """Generate a full markdown report from search results."""
    data = request.get_json()
    try:
        report = engine.generate_full_report(data)
        return jsonify({'report': report})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  SmartResearch Engine — Starting...")
    print("  Open your browser at: http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5000)
