import re


FILLER_WORDS = {
    "um": "[UM]",
    "uh": "[UH]",
    "er": "[ER]",
    "hmm": "[HMM]"
}


def detect_fillers(text):

    filler_counts = {}

    for filler, marker in FILLER_WORDS.items():

        matches = re.findall(
            re.escape(marker),
            text,
            re.IGNORECASE
        )

        if matches:
            filler_counts[filler] = len(matches)

    return filler_counts