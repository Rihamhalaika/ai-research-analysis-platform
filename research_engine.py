"""
SmartResearch Engine — Core AI Engine
========================================
Free APIs used:
  • Semantic Scholar  — 200M+ papers, no key
  • arXiv             — 2M+ preprints, no key
  • OpenAlex          — 250M+ works, no key
  • HuggingFace BART  — AI summarisation, free-tier key
"""

import re
import os
import time
import requests
import xml.etree.ElementTree as ET
import urllib.parse
from collections import Counter
from datetime import datetime

import PyPDF2
from config import Config


# ════════════════════════════════════════════════════════════════════════════
#  ResearchEngine
# ════════════════════════════════════════════════════════════════════════════

class ResearchEngine:

    def __init__(self):
        self.config = Config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SmartResearch-Engine/2.0 (Academic Research Tool)'
        })

    # ────────────────────────────────────────────────────────────────────────
    #  1. PAPER RETRIEVAL
    # ────────────────────────────────────────────────────────────────────────

    def fetch_semantic_scholar(self, topic: str, limit: int = 10) -> list:
        """Query Semantic Scholar Graph API."""
        papers = []
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                'query': topic,
                'limit': limit,
                'fields': 'title,abstract,authors,year,citationCount,externalIds,venue,referenceCount'
            }
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                for p in resp.json().get('data', []):
                    papers.append({
                        'title':     p.get('title', 'Unknown'),
                        'abstract':  p.get('abstract', ''),
                        'authors':   [a.get('name', '') for a in p.get('authors', [])],
                        'year':      p.get('year'),
                        'citations': p.get('citationCount', 0),
                        'venue':     p.get('venue', ''),
                        'source':    'Semantic Scholar',
                        'doi':       p.get('externalIds', {}).get('DOI', ''),
                    })
        except Exception as e:
            print(f"[Semantic Scholar] {e}")
        return papers

    def fetch_arxiv(self, topic: str, limit: int = 10) -> list:
        """Query arXiv Atom API."""
        papers = []
        try:
            query = urllib.parse.quote(topic)
            url = (f"http://export.arxiv.org/api/query"
                   f"?search_query=all:{query}&start=0&max_results={limit}&sortBy=relevance")
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('atom:entry', ns):
                    title_el     = entry.find('atom:title', ns)
                    abstract_el  = entry.find('atom:summary', ns)
                    published_el = entry.find('atom:published', ns)
                    authors = [
                        a.find('atom:name', ns).text
                        for a in entry.findall('atom:author', ns)
                        if a.find('atom:name', ns) is not None
                    ]
                    papers.append({
                        'title':     title_el.text.strip().replace('\n', ' ') if title_el is not None else 'Unknown',
                        'abstract':  abstract_el.text.strip() if abstract_el is not None else '',
                        'authors':   authors,
                        'year':      int(published_el.text[:4]) if published_el is not None else None,
                        'citations': 0,
                        'venue':     'arXiv',
                        'source':    'arXiv',
                        'doi':       '',
                    })
        except Exception as e:
            print(f"[arXiv] {e}")
        return papers

    def fetch_openalex(self, topic: str, limit: int = 10) -> list:
        """Query OpenAlex works endpoint."""
        papers = []
        try:
            params = {
                'search':    topic,
                'per-page':  limit,
                'sort':      'relevance_score:desc',
                'filter':    'has_abstract:true',
                'mailto':    self.config.OPENALEX_EMAIL,
            }
            resp = self.session.get("https://api.openalex.org/works", params=params, timeout=15)
            if resp.status_code == 200:
                for p in resp.json().get('results', []):
                    abstract = ''
                    if p.get('abstract_inverted_index'):
                        abstract = self._reconstruct_abstract(p['abstract_inverted_index'])
                    authors = [
                        a.get('author', {}).get('display_name', '')
                        for a in p.get('authorships', [])
                        if a.get('author', {}).get('display_name')
                    ]
                    host = p.get('host_venue') or {}
                    papers.append({
                        'title':     p.get('display_name', 'Unknown'),
                        'abstract':  abstract,
                        'authors':   authors,
                        'year':      p.get('publication_year'),
                        'citations': p.get('cited_by_count', 0),
                        'venue':     host.get('display_name', ''),
                        'source':    'OpenAlex',
                        'doi':       p.get('doi', ''),
                    })
        except Exception as e:
            print(f"[OpenAlex] {e}")
        return papers

    def _reconstruct_abstract(self, inverted_index: dict) -> str:
        """Convert OpenAlex inverted-index abstract back to plain text."""
        words = {}
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        return ' '.join(words[k] for k in sorted(words))

    # ────────────────────────────────────────────────────────────────────────
    #  2. SUMMARISATION
    # ────────────────────────────────────────────────────────────────────────

    def summarize_text(self, text: str, max_length: int = 130, min_length: int = 30) -> str:
        """Summarise with HuggingFace BART or fall back to extractive summary."""
        if not text or len(text.strip()) < 50:
            return text
        hf_key = self.config.HUGGINGFACE_API_KEY
        if not hf_key or hf_key == "YOUR_HUGGINGFACE_API_KEY":
            return self._basic_summarize(text, max_length)
        try:
            url  = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {hf_key}"},
                json={"inputs": text[:1024],
                      "parameters": {"max_length": max_length, "min_length": min_length}},
                timeout=30
            )
            if resp.status_code == 200:
                result = resp.json()
                if isinstance(result, list) and result:
                    return result[0].get('summary_text', self._basic_summarize(text, max_length))
        except Exception as e:
            print(f"[HuggingFace] {e}")
        return self._basic_summarize(text, max_length)

    def _basic_summarize(self, text: str, max_chars: int = 500) -> str:
        """Extractive fallback: return the first few sentences up to max_chars."""
        sentences = re.split(r'(?<=[.!?]) +', text.strip())
        summary = ''
        for s in sentences:
            if len(summary) + len(s) > max_chars:
                break
            summary += s + ' '
        return summary.strip() or text[:max_chars] + '...'

    # ────────────────────────────────────────────────────────────────────────
    #  3. KEYWORD / TOPIC EXTRACTION
    # ────────────────────────────────────────────────────────────────────────

    _STOP_WORDS = {
        'the','a','an','and','or','but','in','on','at','to','for','of','with',
        'by','from','is','are','was','were','be','been','have','has','had','do',
        'does','did','will','would','could','should','may','might','this','that',
        'these','those','we','our','their','its','it','also','can','paper','study',
        'research','approach','method','using','based','results','show','proposed',
        'use','used','present','provide','including','such','two','three','however',
        'which','than','more','most','into','about','through','between','across',
        'each','both','well','not','new','work','first','second','shows','shown',
        'find','found','high','large','small','data','model','models','system',
        'systems','task','tasks','problem','problems','set','sets','given',
        'different','several','many','number','type','types','form','forms',
        'general','specific','single','multiple','various','existing','recent',
        'current','state','level','case','cases','ways','terms','order',
        'information','performance','evaluation','analysis','framework','learning',
        'training','testing','methods','network','networks','dataset','datasets',
        'feature','features','input','output','function','functions','value',
        'values','process','processing','time','real','make','made','other','only',
        'same','while','when','where','effect','effects','over','class','classes',
        'object','objects','knowledge','ability','human',
    }

    def extract_keywords(self, text: str) -> list:
        """
        Extract meaningful research phrases (bigrams + trigrams) from text.
        Single words are kept only when clearly domain-specific (>=7 chars).
        """
        if not text:
            return []
        words = re.findall(r'\b[a-z][a-z]{2,}\b', text.lower())
        sw = self._STOP_WORDS

        bigrams = [
            f"{words[i]} {words[i+1]}"
            for i in range(len(words) - 1)
            if words[i] not in sw and words[i+1] not in sw
            and len(words[i]) > 3 and len(words[i+1]) > 3
        ]
        trigrams = [
            f"{words[i]} {words[i+1]} {words[i+2]}"
            for i in range(len(words) - 2)
            if words[i] not in sw and words[i+2] not in sw
            and len(words[i]) > 3 and len(words[i+2]) > 3
        ]
        singles = [w for w in words if w not in sw and len(w) >= 7]

        return bigrams + trigrams + singles

    def extract_topics(self, papers: list) -> list:
        """
        Return the top-10 research topics across the papers, ranked by
        how many papers mention them.
        """
        if not papers:
            return []

        paper_counts = Counter()
        raw_counts   = Counter()

        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            kws_unique = set(self.extract_keywords(text))
            kws_all    = self.extract_keywords(text)
            for kw in kws_unique:
                paper_counts[kw] += 1
            for kw in kws_all:
                raw_counts[kw] += 1

        total_papers = len(papers)
        topics = []
        for kw, paper_cnt in paper_counts.most_common(80):
            min_papers = 2 if ' ' in kw else 3
            if paper_cnt < min_papers:
                continue
            topics.append({
                'keyword':     kw,
                'count':       raw_counts[kw],
                'paper_count': paper_cnt,
                'percentage':  round(paper_cnt / total_papers * 100, 1),
            })

        topics.sort(key=lambda x: x['paper_count'], reverse=True)
        return topics[:10]

    # ────────────────────────────────────────────────────────────────────────
    #  4. RESEARCH GAP DETECTION
    # ────────────────────────────────────────────────────────────────────────

    def identify_research_gaps(self, papers: list, topic: str) -> dict:
        """
        Identify research gaps by comparing what IS covered in the retrieved
        papers against the broader field (fetched from arXiv).

        Returns:
          gap_topics    — underexplored keywords (present in field, absent in results)
          extracted_gaps — sentences from abstracts that self-report limitations/gaps
        """
        # Step 1: what the retrieved papers cover
        paper_counts_specific = Counter()
        for p in papers:
            text = f"{p.get('title', '')} {p.get('abstract', '')}"
            for kw in set(self.extract_keywords(text)):
                paper_counts_specific[kw] += 1

        well_studied_threshold = max(2, len(papers) * 0.25)
        well_studied = {
            kw for kw, cnt in paper_counts_specific.items()
            if cnt >= well_studied_threshold
        }

        # Step 2: broader field via arXiv (50 papers)
        broader_papers = []
        try:
            broader_papers = self.fetch_arxiv(topic, limit=50)
            time.sleep(0.3)
        except Exception:
            pass

        paper_counts_broad = Counter()
        for p in broader_papers:
            text = f"{p.get('title', '')} {p.get('abstract', '')}"
            for kw in set(self.extract_keywords(text)):
                paper_counts_broad[kw] += 1

        total_broad    = len(broader_papers) or 1
        total_specific = len(papers) or 1

        # Step 3: score each gap candidate
        gap_candidates = []
        for kw, broad_cnt in paper_counts_broad.most_common(200):
            if len(kw) < 5 or kw in well_studied or broad_cnt < 3:
                continue
            broad_pct    = broad_cnt / total_broad
            specific_cnt = paper_counts_specific.get(kw, 0)
            specific_pct = specific_cnt / total_specific
            gap_score    = broad_pct - specific_pct
            if gap_score > 0:
                gap_candidates.append({
                    'keyword':        kw,
                    'gap_score':      round(gap_score * 1000, 1),
                    'broad_count':    broad_cnt,
                    'specific_count': specific_cnt,
                    'broad_pct':      round(broad_pct * 100, 1),
                    'specific_pct':   round(specific_pct * 100, 1),
                })

        gap_candidates.sort(key=lambda x: x['gap_score'], reverse=True)

        # Step 4: self-reported gap sentences from abstracts
        gap_phrases = [
            "limited", "lack", "gap", "future work", "unexplored", "remain",
            "unclear", "challenge", "open problem", "yet to", "need further",
            "little attention", "not yet", "scarce", "underexplored",
            "insufficient", "missing", "no study", "few studies",
        ]
        extracted_gaps = []
        seen = set()
        for paper in papers:
            abstract = paper.get('abstract', '')
            for phrase in gap_phrases:
                if phrase in abstract.lower():
                    for sentence in re.split(r'(?<=[.!?]) +', abstract):
                        if phrase in sentence.lower() and len(sentence) > 40:
                            key = sentence.strip()[:80]
                            if key not in seen:
                                seen.add(key)
                                extracted_gaps.append({
                                    'gap':          sentence.strip(),
                                    'source_paper': paper.get('title', 'Unknown'),
                                    'phrase':       phrase,
                                })
                            break

        return {
            'gap_topics':     gap_candidates[:15],
            'extracted_gaps': extracted_gaps,
        }

    # ────────────────────────────────────────────────────────────────────────
    #  5. PDF ANALYSIS  ← redesigned: full ordered abstraction only
    # ────────────────────────────────────────────────────────────────────────

    def analyze_uploaded_paper(self, filepath: str) -> dict:
        """
        Read an uploaded PDF and return a clear, full, ordered abstraction
        of what the paper covers — section by section.

        The abstraction is the primary output. No external API calls are made;
        everything is derived from the paper's own text.
        """
        text = self._extract_pdf_text(filepath)
        if not text:
            return {'error': 'Could not extract text from PDF. '
                             'Make sure the file is not a scanned image or password-protected.'}

        filename  = os.path.basename(filepath)
        word_count = len(text.split())

        # ── Infer title (longest meaningful first line) ──────────────────
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 15]
        title = lines[0][:200] if lines else filename

        # ── Extract all named sections ───────────────────────────────────
        section_data = self._extract_all_sections(text)

        # ── Build the ordered abstraction ───────────────────────────────
        abstraction = self._build_ordered_abstraction(text, section_data)

        # ── Key findings (result/contribution sentences) ─────────────────
        findings = self._extract_findings(text)

        # ── Top keywords for the topics tab ──────────────────────────────
        kw_counter = Counter(self.extract_keywords(text))
        paper_topics = [
            {'keyword': kw, 'count': cnt}
            for kw, cnt in kw_counter.most_common(60)
            if cnt >= 2
        ][:15]

        # ── Gap / future-work sentences ───────────────────────────────────
        gap_phrases = [
            "future work", "future research", "limitation", "limitations",
            "not yet", "remains unclear", "underexplored", "open question",
            "need further", "further investigation", "lack of", "no study",
        ]
        paper_gaps, seen_gaps = [], set()
        for sentence in re.split(r'(?<=[.!?]) +', text):
            for phrase in gap_phrases:
                if phrase in sentence.lower() and len(sentence) > 40:
                    key = sentence.strip()[:80]
                    if key not in seen_gaps:
                        seen_gaps.add(key)
                        paper_gaps.append(sentence.strip()[:300])
                    break
        paper_gaps = paper_gaps[:8]

        # ── List of detected section names (for display pills) ────────────
        sections_found = [
            s.replace('_', ' ').title()
            for s in section_data if section_data[s]
        ]

        return {
            'title':        title,
            'filename':     filename,
            'word_count':   word_count,
            'sections':     sections_found,
            'abstraction':  abstraction,   # ← primary output: ordered blocks
            'section_data': section_data,
            'findings':     findings,
            'topics':       paper_topics,
            'gaps':         paper_gaps,
        }

    # ── PDF helpers ──────────────────────────────────────────────────────────

    def _extract_pdf_text(self, filepath: str) -> str:
        """Extract plain text from every page of a PDF."""
        try:
            text = ''
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
            return text.strip()
        except Exception as e:
            print(f"[PDF] {e}")
            return ''

    def _extract_all_sections(self, text: str) -> dict:
        """
        Scan the text for well-known section headings and return a dict
        mapping heading → full section text (up to 4 000 chars each).
        """
        SECTIONS = [
            'abstract', 'introduction', 'related work', 'background',
            'literature review', 'methodology', 'methods', 'approach',
            'proposed method', 'experimental setup', 'experiments',
            'evaluation', 'results', 'discussion', 'analysis',
            'conclusion', 'conclusions', 'concluding remarks',
            'future work', 'limitations',
            'references',
        ]
        text_lower = text.lower()

        positions = []
        for sec in SECTIONS:
            idx = text_lower.find('\n' + sec)
            if idx != -1:
                positions.append((idx, sec, True))   # True = found with \n prefix
            else:
                idx = text_lower.find(sec)
                if idx != -1:
                    positions.append((idx, sec, False))

        positions.sort(key=lambda x: x[0])

        section_data = {}
        for i, (start, sec, has_newline) in enumerate(positions):
            # +1 to skip the \n when found with newline prefix
            prefix_len = 1 + len(sec) if has_newline else len(sec)
            content_start = start + prefix_len
            content_end   = positions[i + 1][0] if i + 1 < len(positions) else len(text)
            raw = text[content_start:content_end].strip()
            raw = re.sub(r'^[\s\d\.\:\-–]+', '', raw).strip()
            # Remove stray single character left over from section heading overlap in PDF
            # e.g. "abstractt Deep..." → the trailing 't' of 'abstract' bleeds into content
            raw = re.sub(r'^[a-zA-Z]\s', '', raw).strip()
            if len(raw) > 60:
                section_data[sec] = raw[:4000]

        return section_data

    def _build_ordered_abstraction(self, full_text: str, section_data: dict) -> list:
        """
        Build a numbered, ordered list of abstraction blocks.
        Each block has:
          'number'  — display index (1-based)
          'label'   — human-readable section name
          'text'    — 2–5 sentence summary of that section
        """
        # Ordered priority: most papers follow this structure
        PRIORITY = [
            ('abstract',          'Overview & Purpose'),
            ('introduction',      'Problem Statement & Motivation'),
            ('background',        'Background & Context'),
            ('literature review', 'Literature Review'),
            ('related work',      'Related Work'),
            ('methodology',       'Methodology'),
            ('methods',           'Methods'),
            ('approach',          'Proposed Approach'),
            ('proposed method',   'Proposed Method'),
            ('experimental setup','Experimental Setup'),
            ('experiments',       'Experiments'),
            ('evaluation',        'Evaluation'),
            ('results',           'Results & Findings'),
            ('discussion',        'Discussion'),
            ('analysis',          'Analysis'),
            ('conclusion',        'Conclusions'),
            ('conclusions',       'Conclusions'),
            ('future work',       'Future Directions'),
            ('limitations',       'Limitations'),
        ]

        blocks = []
        seen_labels = set()
        counter = 1

        for sec_key, label in PRIORITY:
            content = section_data.get(sec_key, '')
            if not content or label in seen_labels:
                continue
            seen_labels.add(label)
            summary = self._basic_summarize(content, max_chars=600)
            if summary:
                blocks.append({
                    'number': counter,
                    'label':  label,
                    'text':   summary,
                })
                counter += 1

        # Fallback when no sections were detected
        if not blocks:
            blocks.append({
                'number': 1,
                'label':  'Full Paper Content',
                'text':   self._basic_summarize(full_text, max_chars=800),
            })

        return blocks

    def _extract_findings(self, text: str) -> list:
        """Extract sentences that describe key results or contributions."""
        indicators = [
            'we found', 'results show', 'results indicate', 'we demonstrate',
            'we show', 'our results', 'our approach achieves', 'outperforms',
            'significant', 'accuracy of', 'improvement of', 'we propose',
            'we present', 'we introduce', 'we achieve', 'our method',
        ]
        findings, seen = [], set()
        for sentence in re.split(r'(?<=[.!?]) +', text):
            sentence = sentence.strip()
            if len(sentence) < 40 or len(sentence) > 300:
                continue
            for ind in indicators:
                if ind in sentence.lower():
                    key = sentence[:80]
                    if key not in seen:
                        seen.add(key)
                        findings.append(sentence)
                    break
        return findings[:6]

    # ────────────────────────────────────────────────────────────────────────
    #  6. MAIN SEARCH PIPELINE
    # ────────────────────────────────────────────────────────────────────────

    def search_and_analyze(self, topic: str, max_papers: int = 10) -> dict:
        """
        Full pipeline:
          1. Retrieve papers from Semantic Scholar + arXiv
          2. Deduplicate and cap at max_papers
          3. Summarise each abstract
          4. Extract topics
          5. Identify research gaps
          6. Compute statistics
        """
        print(f"\n[Engine] Searching: {topic}")

        papers = []
        papers.extend(self.fetch_semantic_scholar(topic, limit=max_papers))
        time.sleep(0.5)
        papers.extend(self.fetch_arxiv(topic, limit=max_papers))

        papers = self._deduplicate_papers(papers)[:max_papers]
        print(f"[Engine] {len(papers)} papers found")

        for paper in papers:
            abstract = paper.get('abstract', '')
            paper['summary'] = (
                self._basic_summarize(abstract, max_chars=400)
                if len(abstract) > 100 else abstract[:300]
            )

        topics  = self.extract_topics(papers)
        gaps    = self.identify_research_gaps(papers, topic)
        year_dist      = self._year_distribution(papers)
        citation_stats = self._citation_stats(papers)

        return {
            'topic':             topic,
            'papers':            papers,
            'topics':            topics,
            'gaps':              gaps,
            'year_distribution': year_dist,
            'citation_stats':    citation_stats,
            'total_papers':      len(papers),
            'timestamp':         datetime.now().isoformat(),
        }

    # ────────────────────────────────────────────────────────────────────────
    #  7. REPORT GENERATION
    # ────────────────────────────────────────────────────────────────────────

    def generate_full_report(self, data: dict) -> str:
        """Generate a full Markdown research report from search results."""
        topic          = data.get('topic', 'Unknown Topic')
        papers         = data.get('papers', [])
        topics         = data.get('topics', [])
        gaps           = data.get('gaps', {})
        year_dist      = data.get('year_distribution', {})
        citation_stats = data.get('citation_stats', {})
        gap_topics     = gaps.get('gap_topics', [])
        extracted_gaps = gaps.get('extracted_gaps', [])

        nl = '\n'

        report = f"""# SmartResearch Report: {topic}

**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}
**Papers Analysed:** {len(papers)}

---

## Most Covered Topics in This Field

{nl.join(f"- **{t['keyword'].title()}** — {t['paper_count']} of {len(papers)} papers ({t['percentage']}%)" for t in topics) or "- No topics extracted."}

---

## Research Gaps — Underexplored Areas

Topics present in the broader field but absent from the retrieved papers:

{nl.join(f"- **{g['keyword'].title()}** — {g['broad_count']} broader papers, only {g['specific_count']} in results (gap score: {g['gap_score']})" for g in gap_topics[:10]) or "- No gaps detected."}

### Gaps Self-Reported in Abstracts

{nl.join(f"- {g['gap'][:200]}  *(from: {g['source_paper'][:60]})*" for g in extracted_gaps[:6]) or "- None found."}

---

## Papers Summary

{nl.join(
    f"### {i+1}. {p.get('title','Unknown')}{nl}"
    f"**Authors:** {', '.join(p.get('authors',[])[:3]) or 'Unknown'} | "
    f"**Year:** {p.get('year','N/A')} | **Citations:** {p.get('citations',0):,}{nl}"
    f"> {p.get('summary', p.get('abstract',''))[:350]}...{nl}"
    for i, p in enumerate(papers[:10])
)}

---

## Publication Trends

{nl.join(f"- **{y}**: {c} paper(s)" for y, c in sorted(year_dist.items(), reverse=True)[:8]) or "- No data."}

**Citation stats:** avg {citation_stats.get('avg', 0)} · max {citation_stats.get('max', 0):,} · total {citation_stats.get('total', 0):,}

---

*Report generated by SmartResearch Engine · Malak Naimi & Riham Halaika*
"""
        return report

    # ────────────────────────────────────────────────────────────────────────
    #  8. UTILITIES
    # ────────────────────────────────────────────────────────────────────────

    def _deduplicate_papers(self, papers: list) -> list:
        seen, unique = set(), []
        for p in papers:
            key = re.sub(r'[^a-z0-9]', '', p.get('title', '').lower())[:50]
            if key and key not in seen:
                seen.add(key)
                unique.append(p)
        return unique

    def _year_distribution(self, papers: list) -> dict:
        years = [p.get('year') for p in papers if p.get('year')]
        if not years:
            return {}
        c = Counter(years)
        return {str(y): c[y] for y in sorted(c)}

    def _citation_stats(self, papers: list) -> dict:
        cits = [p.get('citations', 0) for p in papers if p.get('citations', 0) > 0]
        if not cits:
            return {'avg': 0, 'max': 0, 'total': 0}
        return {
            'avg':   round(sum(cits) / len(cits), 1),
            'max':   max(cits),
            'total': sum(cits),
        }
