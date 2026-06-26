"""
SmartResearch Engine — Configuration
=====================================
FREE APIs used by this project:

1. Semantic Scholar  — No key needed.  100 req / 5 min.
2. arXiv             — No key needed.  Completely open.
3. OpenAlex          — No key needed.  Add email for higher limits.
4. HuggingFace       — Free-tier key.  Get one at huggingface.co/settings/tokens
"""


import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # — HuggingFace (for AI su  mmarization) ——————
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

    # — OpenAlex ——————
    OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "memesamer146@gmail.com")