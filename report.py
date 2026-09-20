# ============================================================
# SPEAKWISE AI — PERFORMANCE REPORT
# ============================================================

RECORDING_SECONDS = 60


# ============================================================
# INDIVIDUAL SCORING FUNCTIONS
# ============================================================

def score_speech_fluency(total_words, total_fillers):
    """
    Score based on filler word percentage.

    0% fillers     → 10
    1-2% fillers   → 8-9
    3-5% fillers   → 6-7
    6-10% fillers  → 4-5
    >10% fillers   → 1-3
    """

    if total_words == 0:
        return 0.0

    filler_pct = (total_fillers / total_words) * 100.0

    if filler_pct <= 0.5:
        return 10.0
    elif filler_pct <= 1.0:
        return 9.0
    elif filler_pct <= 2.0:
        return 8.0
    elif filler_pct <= 3.0:
        return 7.0
    elif filler_pct <= 5.0:
        return 6.0
    elif filler_pct <= 7.0:
        return 5.0
    elif filler_pct <= 10.0:
        return 4.0
    elif filler_pct <= 15.0:
        return 3.0
    elif filler_pct <= 20.0:
        return 2.0
    else:
        return 1.0


def score_pause_management(pauses, duration):
    """
    Score based on pause count, average length,
    and longest pause relative to speech duration.

    Few short pauses are natural and score well.
    Many long pauses indicate hesitation.
    """

    if duration <= 0:
        return 5.0

    num_pauses = len(pauses)

    if num_pauses == 0:
        return 10.0

    avg_pause = sum(pauses) / num_pauses
    longest = max(pauses)
    pause_rate = num_pauses / (duration / 60.0)

    score = 10.0

    # Penalize for high pause rate (pauses per minute)
    if pause_rate > 12:
        score -= 3.0
    elif pause_rate > 8:
        score -= 2.0
    elif pause_rate > 5:
        score -= 1.0

    # Penalize for long average pause
    if avg_pause > 3.0:
        score -= 3.0
    elif avg_pause > 2.0:
        score -= 2.0
    elif avg_pause > 1.5:
        score -= 1.0

    # Penalize for very long single pause
    if longest > 5.0:
        score -= 2.0
    elif longest > 3.0:
        score -= 1.0

    return max(1.0, min(10.0, score))


def score_eye_contact(video_report):
    """
    Score based on camera eye contact percentage.

    90%+ → 10
    80%+ → 9
    ...
    <20% → 1
    """

    if video_report is None:
        return None

    eye = video_report.get("eye_contact", {})
    pct = eye.get("contact_percentage", 0.0)

    if pct >= 90:
        return 10.0
    elif pct >= 80:
        return 9.0
    elif pct >= 70:
        return 8.0
    elif pct >= 60:
        return 7.0
    elif pct >= 50:
        return 6.0
    elif pct >= 40:
        return 5.0
    elif pct >= 30:
        return 4.0
    elif pct >= 20:
        return 3.0
    elif pct >= 10:
        return 2.0
    else:
        return 1.0


def score_head_stability(video_report):
    """
    Score based on head-forward percentage.
    """

    if video_report is None:
        return None

    head = video_report.get("head_position", {})
    pct = head.get("percentage", 0.0)

    if pct >= 90:
        return 10.0
    elif pct >= 80:
        return 9.0
    elif pct >= 70:
        return 8.0
    elif pct >= 60:
        return 7.0
    elif pct >= 50:
        return 6.0
    elif pct >= 40:
        return 5.0
    elif pct >= 30:
        return 4.0
    elif pct >= 20:
        return 3.0
    elif pct >= 10:
        return 2.0
    else:
        return 1.0


def score_speech_pace(total_words, duration):
    """
    Score based on words per minute.

    Ideal range is 120-160 WPM for presentations.
    Too slow or too fast both lose points.
    """

    if duration <= 0 or total_words == 0:
        return 0.0

    wpm = total_words / (duration / 60.0)

    # Ideal zone: 120–160 WPM
    if 120 <= wpm <= 160:
        return 10.0
    elif 100 <= wpm < 120 or 160 < wpm <= 180:
        return 8.0
    elif 80 <= wpm < 100 or 180 < wpm <= 200:
        return 6.0
    elif 60 <= wpm < 80 or 200 < wpm <= 220:
        return 4.0
    elif 40 <= wpm < 60 or 220 < wpm <= 250:
        return 3.0
    elif wpm < 40:
        return 2.0
    else:
        return 1.0


def score_topic_relevance(relevance_result):
    """
    Extract the relevance score from the AI analysis result.

    Returns None if no result is available.
    """

    if relevance_result is None:
        return None

    score = relevance_result.get("score")
    if score is None:
        return None

    return max(1.0, min(10.0, float(score)))


# ============================================================
# FEEDBACK GENERATION
# ============================================================

def generate_feedback(
    fluency_score,
    pause_score,
    eye_score,
    head_score,
    pace_score,
    relevance_score,
    total_words,
    total_fillers,
    pauses,
    duration,
    video_report,
    relevance_result,
):
    """
    Generate lists of strengths and improvements
    based on the individual scores and raw data.
    """

    strengths = []
    improvements = []

    # --------------------------------------------------------
    # Speech fluency
    # --------------------------------------------------------

    filler_pct = (
        (total_fillers / total_words * 100.0)
        if total_words > 0
        else 0.0
    )

    if fluency_score >= 8:
        strengths.append(
            "Excellent speech fluency — very few "
            "filler words detected."
        )
    elif fluency_score >= 6:
        strengths.append(
            "Decent fluency with moderate filler "
            "word usage."
        )
    else:
        improvements.append(
            f"Reduce filler words (um, uh, er, hmm). "
            f"You used {total_fillers} fillers "
            f"({filler_pct:.1f}% of speech). "
            f"Practice pausing silently instead."
        )

    # --------------------------------------------------------
    # Pause management
    # --------------------------------------------------------

    if pause_score >= 8:
        strengths.append(
            "Great pause management — your speech "
            "flowed naturally without long hesitations."
        )
    elif pause_score >= 6:
        strengths.append(
            "Pause usage was acceptable, with only "
            "occasional longer gaps."
        )
    else:
        avg = (
            sum(pauses) / len(pauses)
            if pauses
            else 0
        )
        improvements.append(
            f"Work on reducing hesitation pauses. "
            f"You had {len(pauses)} pauses averaging "
            f"{avg:.1f}s each. Practice your key points "
            f"to maintain smoother delivery."
        )

    # --------------------------------------------------------
    # Eye contact
    # --------------------------------------------------------

    if eye_score is not None:

        if eye_score >= 8:
            strengths.append(
                "Strong eye contact with the camera — "
                "this builds trust and engagement "
                "with your audience."
            )
        elif eye_score >= 6:
            strengths.append(
                "Moderate eye contact — you looked at "
                "the camera for a good portion of "
                "the time."
            )
        else:
            eye_pct = video_report["eye_contact"].get(
                "contact_percentage", 0
            )
            improvements.append(
                f"Improve camera eye contact (currently "
                f"{eye_pct:.0f}%). Try placing a small "
                f"sticker near your webcam as a visual "
                f"anchor to look at while speaking."
            )

    # --------------------------------------------------------
    # Head stability
    # --------------------------------------------------------

    if head_score is not None:

        if head_score >= 8:
            strengths.append(
                "Excellent head position — you stayed "
                "camera-facing and steady throughout."
            )
        elif head_score >= 6:
            strengths.append(
                "Fairly stable head position with "
                "some turning."
            )
        else:
            head_pct = video_report["head_position"].get(
                "percentage", 0
            )
            improvements.append(
                f"Keep your head facing the camera "
                f"more consistently (currently "
                f"{head_pct:.0f}% forward). Avoid "
                f"looking sideways or down while speaking."
            )

    # --------------------------------------------------------
    # Speech pace
    # --------------------------------------------------------

    wpm = (
        total_words / (duration / 60.0)
        if duration > 0
        else 0
    )

    if pace_score >= 8:
        strengths.append(
            f"Great speaking pace at {wpm:.0f} words "
            f"per minute — clear and easy to follow."
        )
    elif pace_score >= 6:
        if wpm < 120:
            improvements.append(
                f"Your pace ({wpm:.0f} WPM) is a bit "
                f"slow. Try to speak slightly faster "
                f"to keep your audience engaged."
            )
        else:
            improvements.append(
                f"Your pace ({wpm:.0f} WPM) is a bit "
                f"fast. Try slowing down slightly to "
                f"let your points land."
            )
    else:
        if wpm < 80:
            improvements.append(
                f"Speaking pace is very slow ({wpm:.0f} "
                f"WPM). Aim for 120-160 WPM for a "
                f"natural conversational delivery."
            )
        elif wpm > 200:
            improvements.append(
                f"Speaking pace is too fast ({wpm:.0f} "
                f"WPM). Slow down to 120-160 WPM so "
                f"your audience can absorb your message."
            )
        else:
            if wpm < 120:
                improvements.append(
                    f"Your pace ({wpm:.0f} WPM) could "
                    f"use improvement. Aim for 120-160 "
                    f"WPM for the best impact."
                )
            else:
                improvements.append(
                    f"Your pace ({wpm:.0f} WPM) could "
                    f"use improvement. Aim for 120-160 "
                    f"WPM for the best impact."
                )

    # Bonus: word count feedback
    if total_words < 30:
        improvements.append(
            "You spoke very few words. Try to "
            "elaborate more on your points to "
            "fill the time effectively."
        )

    # --------------------------------------------------------
    # Topic relevance
    # --------------------------------------------------------

    if relevance_score is not None:

        if relevance_score >= 8:
            strengths.append(
                "Excellent topic relevance — your speech "
                "stayed focused on the assigned subject."
            )
        elif relevance_score >= 6:
            strengths.append(
                "Good topic relevance — your speech mostly "
                "addressed the assigned subject."
            )
        else:
            improvements.append(
                "Your speech drifted from the assigned "
                "topic. Focus on staying on-subject and "
                "relating your points back to the topic."
            )

        # Flag off-topic sentences
        if relevance_result is not None:
            off_topic = relevance_result.get(
                "off_topic_sentences", []
            )
            if off_topic:
                sentences = "; ".join(
                    f'"{s}"' for s in off_topic[:5]
                )
                improvements.append(
                    f"Off-topic sentences detected: {sentences}"
                )

    return strengths, improvements


# ============================================================
# OVERALL SCORE
# ============================================================

def calculate_overall(scores):
    """
    Weighted average of all available scores.

    Weights:
        Speech fluency:    25%
        Pause management:  15%
        Eye contact:       25%
        Head stability:    15%
        Speech pace:       20%
    """

    weights = {
        "fluency": 0.20,
        "pauses": 0.10,
        "eye_contact": 0.20,
        "head_stability": 0.15,
        "pace": 0.15,
        "relevance": 0.20,
    }

    total_weight = 0.0
    weighted_sum = 0.0

    for key, weight in weights.items():

        value = scores.get(key)

        if value is not None:
            weighted_sum += value * weight
            total_weight += weight

    if total_weight <= 0:
        return 0.0

    return round(weighted_sum / total_weight, 1)


# ============================================================
# PRINT REPORT
# ============================================================

def print_report(
    video_report,
    total_words,
    total_fillers,
    pauses,
    duration,
    transcription="",
    topic="",
    relevance_result=None,
):
    """
    Print the full SpeakWise AI performance report
    with scores out of 10 and actionable feedback.
    """

    # --------------------------------------------------------
    # Calculate all scores
    # --------------------------------------------------------

    fluency = score_speech_fluency(
        total_words,
        total_fillers,
    )

    pause_mgmt = score_pause_management(
        pauses,
        duration,
    )

    eye = score_eye_contact(video_report)

    head = score_head_stability(video_report)

    pace = score_speech_pace(
        total_words,
        duration,
    )

    relevance = score_topic_relevance(relevance_result)

    scores = {
        "fluency": fluency,
        "pauses": pause_mgmt,
        "eye_contact": eye,
        "head_stability": head,
        "pace": pace,
        "relevance": relevance,
    }

    overall = calculate_overall(scores)

    # --------------------------------------------------------
    # Generate feedback
    # --------------------------------------------------------

    strengths, improvements = generate_feedback(
        fluency,
        pause_mgmt,
        eye,
        head,
        pace,
        relevance,
        total_words,
        total_fillers,
        pauses,
        duration,
        video_report,
        relevance_result,
    )

    # --------------------------------------------------------
    # Print header
    # --------------------------------------------------------

    print()
    print("=" * 54)
    print("         SPEAKWISE AI — PERFORMANCE REPORT")
    print("=" * 54)

    # --------------------------------------------------------
    # Transcription
    # --------------------------------------------------------

    if topic:
        print()
        print(f"  Topic: \"{topic}\"")

    if transcription:
        print()
        print("--- What You Said ---")
        print()
        print(f"  {transcription}")

    # --------------------------------------------------------
    # Score breakdown
    # --------------------------------------------------------

    print()
    print("--- Scores (out of 10) ---")
    print()

    bar_width = 20

    score_items = [
        ("Speech Fluency", fluency),
        ("Pause Management", pause_mgmt),
        ("Eye Contact", eye),
        ("Head Stability", head),
        ("Speech Pace", pace),
        ("Topic Relevance", relevance),
    ]

    for label, value in score_items:

        if value is None:
            print(f"  {label:<20} {'N/A':>6}   (video unavailable)")
            continue

        filled = int(round(value / 10.0 * bar_width))
        empty = bar_width - filled
        bar = "█" * filled + "░" * empty

        print(
            f"  {label:<20} {value:>4}/10  "
            f"  {bar}"
        )

    # --------------------------------------------------------
    # Overall
    # --------------------------------------------------------

    print()
    print("-" * 54)

    filled = int(round(overall / 10.0 * bar_width))
    empty = bar_width - filled
    bar = "█" * filled + "░" * empty

    print(
        f"  {'OVERALL RATING':<20} {overall:>4}/10  "
        f"  {bar}"
    )

    print("-" * 54)

    # --------------------------------------------------------
    # Quick stats
    # --------------------------------------------------------

    print()
    print("--- Quick Stats ---")
    print()

    wpm = (
        total_words / (duration / 60.0)
        if duration > 0
        else 0
    )

    filler_pct = (
        (total_fillers / total_words * 100.0)
        if total_words > 0
        else 0.0
    )

    print(f"  Words spoken:        {total_words}")
    print(f"  Speaking pace:       {wpm:.0f} WPM")
    print(f"  Filler words:        {total_fillers} ({filler_pct:.1f}%)")
    print(f"  Pauses (>=0.5s):     {len(pauses)}")

    if pauses:
        print(f"  Longest pause:       {max(pauses):.2f}s")
        print(f"  Average pause:       {sum(pauses) / len(pauses):.2f}s")

    if video_report is not None:
        eye_data = video_report.get("eye_contact", {})
        head_data = video_report.get("head_position", {})
        print(
            f"  Eye contact:         "
            f"{eye_data.get('contact_percentage', 0):.0f}%"
        )
        print(
            f"  Head forward:        "
            f"{head_data.get('percentage', 0):.0f}%"
        )

    # --------------------------------------------------------
    # Strengths
    # --------------------------------------------------------

    if strengths:
        print()
        print("--- What You Did Well ---")
        print()
        for item in strengths:
            print(f"  [+] {item}")

    # --------------------------------------------------------
    # Improvements
    # --------------------------------------------------------

    if improvements:
        print()
        print("--- Areas to Improve ---")
        print()
        for item in improvements:
            print(f"  [-] {item}")

    # --------------------------------------------------------
    # Encouragement
    # --------------------------------------------------------

    print()

    if overall >= 8.0:
        print(
            "  ★ Outstanding performance! "
            "Keep up the excellent work."
        )
    elif overall >= 6.0:
        print(
            "  ★ Solid effort! Focus on the areas above "
            "and you'll improve quickly."
        )
    elif overall >= 4.0:
        print(
            "  ★ Good start! Practice regularly and "
            "you'll see noticeable progress."
        )
    else:
        print(
            "  ★ Every expert was once a beginner. "
            "Keep practicing — you'll get there!"
        )

    print()
    print("=" * 54)
