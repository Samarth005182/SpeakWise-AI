# SpeakWise AI — Implementation Plan

Below is a concrete plan that solves all three problems **with one architectural change**: switch to a transcription backend that returns **word-level timestamps**. You cannot reliably detect pace or pauses without per-word timing, and the same switch also fixes filler skipping.

---

## The root cause

`whisper.load_model("base").transcribe(...)` returns only segment-level timestamps (30s chunks) and aggressively smooths disfluencies — that's why "um/uh" vanish. Even the `verbatim_prompt` trick is hit-or-miss on the `base` model. So the "verbatim mode" is fighting the model instead of using a tool built for the job.

---

## Recommended transcription backend

Pick one (in order of recommendation):

| Option | Fillers preserved? | Word timestamps? | Cost | Notes |
|---|---|---|---|---|
| **WhisperX** (local) | Yes (large-v3 + VAD) | Yes (forced alignment via wav2vec2) | Free | Best local option — slower than base, but accurate |
| **Deepgram Nova-3** (already integrated in `audio_text.py`) | Yes (`filler_words=True`) | Yes (`utterances=True`) | Paid | Fastest, cleanest, but needs `DEEPGRAM_API_KEY` |
| Whisper `medium`/`large-v3` with `hallucination_silence_threshold` | Partial | Segment only | Free | Won't give pause detection |

Recommended: **WhisperX** (no API key dependency, all three features work, runs offline). If Deepgram key is already available, that's even less work since `_transcribe_with_deepgram` already exists — just enable `utterances=True` and parse word timestamps instead of only the transcript string.

---

## Proposed new module structure

```
audio_text.py        → returns AnalysisData, not just str
filler_detection.py  → takes timestamped words, not raw text
NEW speech_analysis.py → pace + pauses + overall score
main.py              → orchestrates, prints a unified report
```

---

## Step 1 — Make `transcribe_audio` return word-level data

Replace the return type from `str` with a structured object:

```python
@dataclass
class WordToken:
    text: str
    start: float   # seconds from audio start
    end: float
    confidence: float

@dataclass
class Transcript:
    text: str
    words: list[WordToken]
    duration: float
```

WhisperX snippet:

```python
import whisperx
model = whisperx.load_model("large-v3", device="cpu", compute_type="int8")
result = model.transcribe(audio_file, batch_size=4)
align_model, meta = whisperx.load_align_model("en", device="cpu")
aligned = whisperx.align(result["segments"], align_model, meta,
                         audio_file, device="cpu")
words = [WordToken(w["word"].strip(), w["start"], w["end"], w["score"])
         for w in aligned["word_segments"]]
```

Deepgram snippet (if using cloud path):

```python
options = PrerecordedOptions(model="nova-3", filler_words=True,
                             smart_format=True, utterances=True, language="en")
response = client.listen.rest.v1.transcribe_file(payload, options)
utt = response.results.utterances[0]
words = [WordToken(w.word, w.start, w.end, w.confidence) for w in utt.words]
```

---

## Step 2 — Fix filler detection

Two complementary approaches (use both, then union):

- **Lexical** (keep existing `filler_detection.py` regex): run on the verbatim transcript text — now that WhisperX/Deepgram preserves "um/uh", the existing code will actually work.
- **Channel-based** (Deepgram only): use the native `is_filler` flag — no regex guessing.

Recommendation: drop `right`, `basically`, `actually`, `literally` from `FILLER_WORDS` unless POS tagging is also done — they over-flag in conversational speech. Keep `um/uh/er/ah/hmm/you know/i mean/sort of/kind of`.

---

## Step 3 — Pace analysis (new function in `speech_analysis.py`)

```python
def analyze_pace(transcript: Transcript) -> dict:
    total_words = len(transcript.words)
    speech_duration = sum(w.end - w.start for w in transcript.words)  # active speech only
    wpm = (total_words / speech_duration) * 60 if speech_duration else 0

    # Recommended bands
    if wpm < 100:    label = "Too slow — may sound hesitant"
    elif wpm < 130:  label = "Calm, deliberate"
    elif wpm < 160:  label = "Conversational, ideal"
    elif wpm < 190:  label = "Energetic, slightly fast"
    else:            label = "Too fast — hard to follow"
    return {"wpm": wpm, "label": label, "speech_duration": speech_duration}
```

Why use active speech duration (excluding pauses) instead of the full 60s? Otherwise a speaker with lots of silence gets a falsely low WPM. Optionally also report a "raw WPM" over the full recording length for comparison — a big gap between the two reveals a hesitant speaker.

---

## Step 4 — Pause analysis

Walk consecutive word tokens and measure gaps:

```python
def analyze_pauses(transcript: Transcript) -> dict:
    gaps = []
    for a, b in zip(transcript.words, transcript.words[1:]):
        if b.start > a.end:
            gaps.append((a.end, b.start, b.start - a.end))

    # Classification thresholds (seconds)
    MICRO   = 0.20   # natural junction
    MEDIUM  = 0.50   # clause boundary
    LONG    = 1.00   # hesitation / thought loss
    VLONG   = 2.00   # awkward silence

    total_pause = sum(g for *_, g in gaps)
    total_silence_segments = [g for *_, g in gaps if g >= LONG]
    avg_pause = total_pause / len(gaps) if gaps else 0
    silence_pct = (total_pause / transcript.duration) * 100
    return {...}
```

Useful derived numbers to surface:

- Average mid-sentence pause (sentence-internal vs. inter-sentence — use simple heuristic: pause after a word ending in `.`, `,`, `?`, `!` is inter-clause)
- Number of long pauses (>1s)
- % of recording that was silence
- Longest silence

---

## Step 5 — Unified score

Replace `calculate_filler_score` with a composite that weights all three axes:

```
score = 0.4 * filler_score + 0.3 * pace_score + 0.3 * pause_score
```

where each sub-score is 1–10 based on bands. This is much more representative than the current "filler percentage only" scoring.

---

## Step 6 — Refactor `main.py`

- Move pipeline code under `if __name__ == "__main__":` so the file can be imported for tests.
- Replace the giant top-level script with a `run()` function.
- Print a tabular report: **Fillers | Pace | Pauses | Overall**, each with sub-labels.

---

## Step 7 — Verification

- Install: `pip install whisperx` (heavier than openai-whisper — needs torch + faster-whisper)
- Keep a known test wav with deliberate "um...uh... long pause", run end-to-end, and confirm:
  - Transcript contains "um", "uh"
  - WPM printed matches manual count
  - One reported long pause ~ the deliberate silence

---

## Estimated effort

| Step | Effort |
|---|---|
| 1. Switch transcription backend to word-timestamps | ~1–2h |
| 2. Refactor filler detection on new data shape | ~30m |
| 3. Pace analysis | ~30m |
| 4. Pause analysis | ~1h |
| 5. Composite scoring + report | ~30m |
| 6. `main.py` refactor + `__main__` guard | ~30m |
| 7. Test with sample recording | ~30m |

---

## Risks / decisions to confirm

1. **WhisperX vs Deepgram** — WhisperX requires ~2GB model download on first run and torch; Deepgram is faster but external. Which to implement?
2. **Device support** — WhisperX on CPU is fine but aligns slower; is CUDA available, or CPU-only?
3. **Filler word list trimming** — OK to drop `actually/ basically/ literally/ right` from the filler list to avoid false positives?

---

## Notes

- Start with Step 1 (the transcription-returns-words refactor) because everything else depends on it.
- The existing `transcription.py` is legacy/unused (commented out) and superseded by `audio_text.py`.
- Two `.venv` folders exist (`.venv` and `.venv-1`) — likely redundant; consolidate before adding new deps.
