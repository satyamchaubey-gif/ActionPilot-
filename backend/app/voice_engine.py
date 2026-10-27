import re, json
from typing import List, Dict, Any, Tuple

COMMON_NAMES = [
    "Priya", "Alex", "Rahul", "Rohan", "Sarah", "Daniel", "Ananya", "Sameer",
    "Vikram", "Amit", "Pooja", "Arjun", "Sneha", "David", "Michael", "Emma"
]

HINGLISH_FIXES = [
    (r"\bkardo\b", "kar do"),
    (r"\bkarlena\b", "kar lena"),
    (r"\bkardenge\b", "kar denge"),
    (r"\bbhejdo\b", "bhej do"),
    (r"\bbhejdungi\b", "bhej dungi"),
    (r"\bbhejdunga\b", "bhej dunga"),
    (r"\bdekhlo\b", "dekh lo"),
    (r"\bsubmitkarna\b", "submit karna"),
    (r"\bcompletekarna\b", "complete karna"),
    (r"\bfinalizekarna\b", "finalize karna"),
    (r"\bdeploykarna\b", "deploy karna"),
    (r"\bkaltak\b", "kal tak"),
    (r"\bparsotak\b", "parso tak"),
    (r"\baajtak\b", "aaj tak"),
    (r"\bfridaytak\b", "Friday tak"),
    (r"\bmondaytak\b", "Monday tak"),
]

def clean_spoken_text(text: str) -> str:
    """Fix common Speech-to-Text phonetic joining and punctuation glitches."""
    if not text:
        return ""
    cleaned = text
    for pattern, repl in HINGLISH_FIXES:
        cleaned = re.sub(pattern, repl, cleaned, flags=re.I)

    # Ensure names are properly capitalized
    for name in COMMON_NAMES:
        cleaned = re.sub(rf"\b{name}\b", name, cleaned, flags=re.I)

    # Ensure proper spacing around punctuation
    cleaned = re.sub(r"\s+([,.?!;:])", r"\1", cleaned)
    cleaned = re.sub(r"([,.?!;:])(?=[A-Za-z])", r"\1 ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def diarize_conversation(
    raw_transcript: str,
    raw_turns: List[Dict[str, Any]] = None
) -> Tuple[str, List[str], List[Dict[str, str]]]:
    """
    Intelligently extracts, cleans, and diarizes multi-voice conversations
    into structured dialogue turns (Speaker 1, Speaker 2, or named speakers).
    """
    diarized_turns: List[Dict[str, str]] = []
    detected_speakers = set()

    # Strategy A: Use client captured speaker turns if provided
    if raw_turns and len(raw_turns) > 0:
        for turn in raw_turns:
            spk = turn.get("speaker", "").strip() or "Speaker 1"
            txt = clean_spoken_text(turn.get("text", "").strip())
            if not txt:
                continue

            # Check if text starts with explicit speaker label (e.g. "Alex: ...")
            m = re.match(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[:—\-]\s*(.*)$", txt)
            if m:
                spk = m.group(1).strip()
                txt = m.group(2).strip()

            detected_speakers.add(spk)
            diarized_turns.append({"speaker": spk, "text": txt})

    # Strategy B: If no structured turns or only one turn with multiple sentences
    if (not diarized_turns or len(diarized_turns) == 1) and raw_transcript:
        cleaned_transcript = clean_spoken_text(raw_transcript)

        # Split by explicit speaker prefixes, newlines, or sentence boundaries
        split_pattern = r"(?<=\n)|(?<=[.?!])\s+(?=[A-Z][a-z]+(?:\s+\d+|\s*\([^)]*\))?\s*[:—\-])|(?<=[.?!])\s+"
        segments = [s.strip() for s in re.split(split_pattern, cleaned_transcript) if s.strip()]

        current_speaker_idx = 1
        speakers_pool = ["Speaker 1", "Speaker 2", "Speaker 3"]
        parsed_turns: List[Dict[str, str]] = []

        for seg in segments:
            # Pattern 1: Explicit speaker prefix "Name: text" or "Speaker X: text"
            spk_match = re.match(r"^([A-Z][\w\s()-]+?)\s*[:—\-]\s*(.+)$", seg)
            if spk_match:
                spk = spk_match.group(1).strip()
                body = spk_match.group(2).strip()
                detected_speakers.add(spk)
                parsed_turns.append({"speaker": spk, "text": body})
                continue

            # Pattern 2: Dialogue vocatives e.g. "Priya ko kal tak..." or "Alex will verify..."
            detected_named_speaker = None
            for name in COMMON_NAMES:
                if re.search(rf"\b{name}\s+(?:ko|must|will|karega|karegi|should|needs to)\b", seg, re.I):
                    detected_named_speaker = name
                    break

            if detected_named_speaker:
                spk = detected_named_speaker
            else:
                spk = speakers_pool[(current_speaker_idx - 1) % len(speakers_pool)]
                current_speaker_idx += 1

            detected_speakers.add(spk)
            parsed_turns.append({"speaker": spk, "text": seg})

        if len(parsed_turns) > len(diarized_turns):
            diarized_turns = parsed_turns

    # Strategy C: Fallback if nothing was extractable
    if not diarized_turns:
        default_text = clean_spoken_text(raw_transcript) or "Meeting note recorded."
        diarized_turns = [{"speaker": "Speaker 1", "text": default_text}]
        detected_speakers.add("Speaker 1")

    # Build unified dialogue transcript
    formatted_lines = []
    for turn in diarized_turns:
        formatted_lines.append(f"{turn['speaker']}: {turn['text']}")
    unified_transcript = "\n".join(formatted_lines)

    sorted_speakers = sorted(list(detected_speakers))
    return unified_transcript, sorted_speakers, diarized_turns
