import re


MARKER_FILLERS = {
    "um": r"\[UM\]",
    "uh": r"\[UH\]",
    "er": r"\[ER\]",
    "hmm": r"\[HMM\]",
    "ah": r"\[AH\]",
}

SPOKEN_FILLERS = {
    "um": r"\bum+\b",
    "uh": r"\buh+\b",
    "er": r"\ber+\b",
    "hmm": r"\bhmm+\b",
    "ah": r"\bah+\b",
    "like": r"\blike\b",
    "you know": r"\byou\s+know\b",
    "basically": r"\bbasically\b",
    "actually": r"\bactually\b",
    "literally": r"\bliterally\b",
    "i mean": r"\bi\s+mean\b",
}


def detect_fillers(text):
    if not text or not text.strip():
        return {}

    filler_counts = {}

    clean_text = text
    for filler_name, marker_pattern in MARKER_FILLERS.items():
        matches = re.findall(marker_pattern, text, re.IGNORECASE)
        if matches:
            filler_counts[filler_name] = filler_counts.get(filler_name, 0) + len(matches)
            clean_text = re.sub(marker_pattern, " ", clean_text, flags=re.IGNORECASE)

    for filler_name, pattern in SPOKEN_FILLERS.items():
        matches = re.findall(pattern, clean_text, re.IGNORECASE)
        if matches:
            filler_counts[filler_name] = filler_counts.get(filler_name, 0) + len(matches)

    return {k: v for k, v in filler_counts.items() if v > 0}
