import io
import re
from pypdf import PdfReader

# Map our internal topic keys to keywords to search for in PDF text
TOPIC_KEYWORDS = {
    # Literacy
    "pronouns":               ["pronoun", "personal pronoun", "possessive pronoun",
                                "subject pronoun", "object pronoun", "reflexive pronoun"],
    "contractions":           ["contraction", "apostrophe"],
    "homophones":             ["homophone"],
    "interjections":          ["interjection"],
    "suffix_prefix":          ["suffix", "prefix"],
    "vocabulary":             ["vocabulary", "cious", "tious", "tion word", "sion word",
                                "que word", "silent gh", "spelling pattern"],
    "research_writing":       ["research writing", "reading comprehension", "comprehension",
                                "main idea", "story element", "inference", "writing format",
                                "reading", "passage"],
    # Numeracy
    "division_equal_groups":  ["equal group", "equal sharing", "division", "sharing equally",
                                "divid"],
    "division_repeated_subtraction": ["repeated subtraction"],
    "division_number_line":   ["number line", "division"],
    "division_fact_families": ["fact famil", "multiplication and division", "fact triangle"],
    "division_word_problems": ["word problem", "story problem", "division"],
    "measurement_length":     ["length", "centimetre", "centimeter", "metre", "meter",
                                "measuring length", "ruler", "measuring"],
    "measurement_mass":       ["mass", "weight", "kilogram", "gram", "kg", "gm"],
    "measurement_capacity":   ["capacity", "litre", "liter", "millilitre", "milliliter"],
}

# Minimum keyword hits to consider a topic detected
MIN_HITS = 1


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF given its raw bytes."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts).lower()
    except Exception:
        return ""


def detect_topics(pdf_bytes: bytes) -> dict:
    """
    Returns a dict of {topic_key: True/False} based on keyword presence in PDF.
    Also returns the raw extracted text for display/debugging.
    """
    text = extract_text_from_pdf(pdf_bytes)
    detected = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in text)
        detected[topic] = hits >= MIN_HITS

    return detected, text[:2000] if text else ""


def summarise_detected(detected: dict, topic_labels: dict) -> list:
    """Return list of (topic_key, label, detected_bool) sorted by subject then name."""
    from utils.worksheet_utils import LITERACY_TOPICS, NUMERACY_TOPICS
    result = []
    for t in LITERACY_TOPICS + NUMERACY_TOPICS:
        result.append((t, topic_labels.get(t, t), detected.get(t, False)))
    return result
