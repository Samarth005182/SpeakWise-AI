# ============================================================
# SPEAKWISE AI — PERFORMANCE REPORT & EVALUATION ENGINE
# ============================================================

RECORDING_SECONDS = 60


# ============================================================
# INDIVIDUAL SCORING FUNCTIONS
# ============================================================

def score_speech_fluency(total_words, total_fillers, duration=60):
    """
    Score based on filler word percentage and spoken volume.
    If no words are spoken, returns 0.0.
    """
    if total_words == 0:
        return 0.0

    # If the user barely spoke (e.g. < 8 words in 30+ seconds), penalize heavily
    if total_words < 8 and duration >= 25:
        return 1.0

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


def score_pause_management(pauses, duration, total_words=None):
    """
    Score based on pause count, average length,
    and longest pause relative to speech duration.

    If total_words is 0 (silence), returns 0.0.
    """
    if total_words is not None and total_words == 0:
        return 0.0

    if duration <= 0:
        return 0.0

    num_pauses = len(pauses)

    if num_pauses == 0:
        # If user spoke healthy amount and had 0 awkward pauses, score 10.0
        return 10.0 if (total_words is None or total_words >= 15) else 3.0

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
    Returns None if video was unavailable or face was not detectable.
    """
    if video_report is None:
        return None

    eye = video_report.get("eye_contact", {})
    if not eye.get("face_detected", True) and eye.get("contact_percentage", 0.0) == 0:
        return 1.0

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
    Returns None if video was unavailable or face was not detectable.
    """
    if video_report is None:
        return None

    head = video_report.get("head_position", {})
    if not head.get("face_detected", True) and head.get("percentage", 0.0) == 0:
        return 1.0

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
    Score based on words per minute (WPM).
    Ideal range is 120-160 WPM for presentations.
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


def score_topic_relevance(relevance_result, total_words=None):
    """
    Extract relevance score from AI analysis result.
    If no words were spoken, returns 0.0.
    """
    if total_words is not None and total_words == 0:
        return 0.0

    if relevance_result is None:
        return None

    score = relevance_result.get("score")
    if score is None:
        return None

    return max(1.0, min(10.0, float(score)))


# ============================================================
# WHAT WENT WRONG — DIAGNOSTIC ANALYSIS
# ============================================================

def generate_what_went_wrong(
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
    video_report=None,
    relevance_result=None,
    filler_breakdown=None,
):
    """
    Diagnose specific mistakes, flaws, and issues that degraded speech performance.
    Returns a list of specific, diagnostic observations explaining what went wrong.
    """
    flaws = []

    # 0. Silence / Zero Words Spoken
    if total_words == 0:
        return [
            "No Speech Detected: We couldn't detect any spoken words in your audio recording. "
            "Please verify that your microphone is selected, not muted, and positioned close to you."
        ]


    # 1. Very Low Content Volume
    wpm = total_words / (duration / 60.0) if duration > 0 else 0
    if total_words < 25 and duration >= 30:
        flaws.append(
            f"Low content volume: Spoke only {total_words} words in {duration}s ({wpm:.0f} WPM). "
            f"Aim for at least 100-140 words per minute to effectively develop your thoughts."
        )

    # 2. Filler Words & Disfluencies
    filler_pct = (total_fillers / total_words * 100.0) if total_words > 0 else 0.0
    if total_fillers > 0 or fluency_score < 8.0:
        breakdown_str = ""
        if filler_breakdown:
            items = [f"'{k}' x{v}" for k, v in filler_breakdown.items() if v > 0]
            if items:
                breakdown_str = f" ({', '.join(items)})"

        if filler_pct > 5.0 or total_fillers >= 4:
            flaws.append(
                f"High filler word usage: Used {total_fillers} filler words{breakdown_str}, "
                f"accounting for {filler_pct:.1f}% of your speech (target: < 2%)."
            )
        elif total_fillers > 0:
            flaws.append(
                f"Disfluencies detected: {total_fillers} filler words{breakdown_str} interrupted vocal delivery."
            )

    # 3. Pacing
    if wpm > 180:
        flaws.append(
            f"Rushed speech pace ({wpm:.0f} WPM): Spoke too rapidly (ideal: 120-160 WPM), making it hard for listeners to follow."
        )
    elif wpm < 90 and total_words >= 25:
        flaws.append(
            f"Sluggish delivery pace ({wpm:.0f} WPM): Delivery was too slow (ideal: 120-160 WPM), which may lower audience engagement."
        )

    # 4. Hesitations & Long Silences
    if pauses:
        avg_pause = sum(pauses) / len(pauses)
        longest_pause = max(pauses)
        if longest_pause >= 3.0:
            flaws.append(
                f"Awkward silence: Longest hesitation pause lasted {longest_pause:.1f}s."
            )
        if len(pauses) > 6 or (len(pauses) > 3 and avg_pause > 1.8):
            flaws.append(
                f"Frequent pauses: Stopped {len(pauses)} times (averaging {avg_pause:.1f}s each), signaling hesitation."
            )

    # 5. Camera Eye Contact & Face Visibility
    if video_report is not None:
        eye_data = video_report.get("eye_contact", {})
        if not eye_data.get("face_detected", True):
            flaws.append(
                "Face not clearly visible: Ensure your webcam is uncovered and well-lit so visual tracking can analyze your eye contact."
            )
        else:
            eye_pct = eye_data.get("contact_percentage", 0.0)
            if eye_pct < 70.0 and eye_score is not None:
                flaws.append(
                    f"Low camera eye contact: Looked directly at the camera only {eye_pct:.0f}% of the time "
                    f"(gaze drifted away {100.0 - eye_pct:.0f}% of the time)."
                )

    # 6. Head Stability & Centering
    if video_report is not None:
        head_data = video_report.get("head_position", {})
        if head_data.get("face_detected", True):
            head_pct = head_data.get("percentage", 0.0)
            if head_pct < 70.0 and head_score is not None:
                flaws.append(
                    f"Excessive head movement: Kept head centered only {head_pct:.0f}% of the time "
                    f"(frequent looking sideways, down, or tilting away)."
                )

    # 7. Topic Relevance & Tangents
    if relevance_result is not None:
        rel_score = relevance_result.get("score")
        off_topic_sentences = relevance_result.get("off_topic_sentences", [])
        if rel_score is not None and rel_score < 7.0:
            flaws.append(
                f"Topic drift: Content relevance scored {rel_score:.1f}/10, drifting away from the core subject."
            )
        if off_topic_sentences:
            examples = "; ".join(f'"{s}"' for s in off_topic_sentences[:3])
            flaws.append(
                f"Off-topic remarks identified by AI: {examples}"
            )

    if not flaws:
        flaws.append("No major flaws detected! Clean speech delivery, steady eye contact, and focused content.")

    return flaws


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
    video_report=None,
    relevance_result=None,
):
    """
    Generate lists of strengths and actionable improvements.
    """
    strengths = []
    improvements = []

    # Case: Silence
    if total_words == 0:
        strengths.append("Camera and microphone initialized properly.")
        improvements.append("Ensure your microphone is enabled and not muted before starting.")
        improvements.append("Speak at a clear, audible volume throughout the full time window.")
        improvements.append("Try practicing with a quick 30-second session first to build momentum.")
        return strengths, improvements

    # 1. Fluency
    filler_pct = (total_fillers / total_words * 100.0) if total_words > 0 else 0.0
    if fluency_score >= 8.0:
        strengths.append("Excellent speech fluency - very few filler words detected.")
    elif fluency_score >= 6.0:
        strengths.append("Decent fluency with moderate filler word usage.")
    else:
        improvements.append(
            f"Reduce filler words (um, uh, like). You used {total_fillers} fillers ({filler_pct:.1f}% of speech). "
            f"Practice pausing silently instead."
        )

    # 2. Pause Management
    if pause_score >= 8.0:
        strengths.append("Great pause management - speech flowed naturally without awkward stops.")
    elif pause_score >= 6.0:
        strengths.append("Acceptable pacing with only occasional hesitation gaps.")
    else:
        avg = sum(pauses) / len(pauses) if pauses else 0
        improvements.append(
            f"Work on reducing hesitation pauses ({len(pauses)} pauses averaging {avg:.1f}s each). "
            f"Structure your talking points before speaking."
        )

    # 3. Eye Contact
    if eye_score is not None:
        if eye_score >= 8.0:
            strengths.append("Strong eye contact with the camera - builds trust and audience connection.")
        elif eye_score >= 6.0:
            strengths.append("Moderate eye contact - looked at the camera for a good portion of time.")
        else:
            eye_pct = video_report["eye_contact"].get("contact_percentage", 0) if video_report else 0
            improvements.append(
                f"Improve camera eye contact (currently {eye_pct:.0f}%). "
                f"Try placing a small visual anchor near your webcam."
            )

    # 4. Head Stability
    if head_score is not None:
        if head_score >= 8.0:
            strengths.append("Excellent head stability - stayed camera-facing and steady.")
        elif head_score >= 6.0:
            strengths.append("Fairly stable posture with minor head movement.")
        else:
            head_pct = video_report["head_position"].get("percentage", 0) if video_report else 0
            improvements.append(
                f"Keep your head facing forward more consistently (currently {head_pct:.0f}% centered)."
            )

    # 5. Speech Pace
    wpm = total_words / (duration / 60.0) if duration > 0 else 0
    if pace_score >= 8.0:
        strengths.append(f"Great speaking pace at {wpm:.0f} WPM - crisp and easy to follow.")
    elif pace_score >= 6.0:
        if wpm < 120:
            improvements.append(f"Pace is slightly slow ({wpm:.0f} WPM). Aim for 120-160 WPM.")
        else:
            improvements.append(f"Pace is slightly fast ({wpm:.0f} WPM). Slow down slightly to let points land.")
    else:
        improvements.append(f"Adjust speaking pace ({wpm:.0f} WPM). Aim for 120-160 WPM for maximum clarity.")

    # 6. Topic Relevance
    if relevance_score is not None:
        if relevance_score >= 8.0:
            strengths.append("Outstanding topic relevance - stayed focused on the assigned subject.")
        elif relevance_score >= 6.0:
            strengths.append("Good topic relevance - mostly addressed the core subject.")
        else:
            improvements.append("Speech drifted from the topic. Tie your points directly back to the core subject.")


    return strengths, improvements


# ============================================================
# OVERALL SCORE CALCULATION
# ============================================================

def calculate_overall(scores, total_words=None):
    """
    Calculate weighted average score (0.0 to 10.0).
    If total_words == 0 (silent recording), overall score is strictly 0.0.
    """
    if total_words is not None and total_words == 0:
        return 0.0

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
# PRINT & COMPILE REPORT
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
    filler_breakdown=None,
):
    """
    Compile and print the complete SpeakWise AI performance report.
    Returns a comprehensive dictionary for persistence and GUI rendering.
    """
    is_silent = (total_words == 0 or not transcription.strip())

    fluency = score_speech_fluency(total_words, total_fillers, duration=duration)
    pause_mgmt = score_pause_management(pauses, duration, total_words=total_words)
    eye = score_eye_contact(video_report)
    head = score_head_stability(video_report)
    pace = score_speech_pace(total_words, duration)
    relevance = score_topic_relevance(relevance_result, total_words=total_words)

    scores = {
        "fluency": fluency,
        "pauses": pause_mgmt,
        "eye_contact": eye,
        "head_stability": head,
        "pace": pace,
        "relevance": relevance,
    }

    overall = calculate_overall(scores, total_words=total_words)
    scores["overall"] = overall

    what_went_wrong = generate_what_went_wrong(
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
        video_report=video_report,
        relevance_result=relevance_result,
        filler_breakdown=filler_breakdown,
    )

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

    wpm = int(round(total_words / (duration / 60.0))) if duration > 0 and total_words > 0 else 0
    filler_pct = (total_fillers / total_words * 100.0) if total_words > 0 else 0.0

    eye_pct = video_report.get("eye_contact", {}).get("contact_percentage", 0.0) if video_report else 0.0
    head_pct = video_report.get("head_position", {}).get("percentage", 0.0) if video_report else 0.0

    # --------------------------------------------------------
    # Console Output
    # --------------------------------------------------------
    print()
    print("=" * 60)
    print("             SPEAKWISE AI -- PERFORMANCE REPORT")
    print("=" * 60)

    if topic:
        print(f"\n  Topic: \"{topic}\"")

    if is_silent:
        print("\n  [!] [NO SPEECH DETECTED] The audio file did not contain audible speech.")
    elif transcription:
        print("\n--- What You Said ---")
        print(f"  {transcription}")


    print("\n--- Scores (out of 10) ---")
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
            print(f"  {label:<20} {'N/A':>6}   (unavailable)")
            continue

        filled = int(round(value / 10.0 * bar_width))
        empty = bar_width - filled
        bar = "[" + "#" * filled + "." * empty + "]"
        print(f"  {label:<20} {value:>4}/10    {bar}")

    print("-" * 60)
    filled = int(round(overall / 10.0 * bar_width))
    empty = bar_width - filled
    bar = "[" + "#" * filled + "." * empty + "]"
    print(f"  {'OVERALL RATING':<20} {overall:>4}/10    {bar}")
    print("-" * 60)

    print("\n--- What Went Wrong (Specific Flaws & Mistakes) ---")
    for item in what_went_wrong:
        if item.startswith("No major"):
            print(f"  [OK] {item}")
        else:
            print(f"  [!] {item}")

    if strengths:
        print("\n--- What You Did Well ---")
        for item in strengths:
            print(f"  [+] {item}")

    if improvements:
        print("\n--- Actionable Advice ---")
        for item in improvements:
            print(f"  [->] {item}")

    print("=" * 60)

    return {
        "fluency": fluency,
        "pauses": pause_mgmt,
        "eye_contact": eye,
        "head_stability": head,
        "pace": pace,
        "relevance": relevance,
        "overall": overall,
        "total_words": total_words,
        "total_fillers": total_fillers,
        "filler_breakdown": filler_breakdown or {},
        "filler_pct": filler_pct,
        "pace_wpm": wpm,
        "eye_contact_pct": eye_pct,
        "head_centering_pct": head_pct,
        "pauses_list": pauses,
        "what_went_wrong": what_went_wrong,
        "strengths": strengths,
        "improvements": improvements,
        "is_silent": is_silent,
        "transcription": transcription,
        "topic": topic,
        "duration": duration,
    }
