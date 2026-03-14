def build_transcript_payload(
    *,
    audio_url: str,
    model: str,
    language_code: str | None,
    punctuate: bool,
    format_text: bool,
    speaker_labels: bool,
    speakers_expected: int,
    sentiment_analysis: bool,
    entity_detection: bool,
    auto_highlights: bool,
    iab_categories: bool,
    filter_profanity: bool,
    disfluencies: bool,
    keyterms_input: str,
    prompt_input: str,
) -> dict:
    # Keep this function pure so request-shaping is easy to test and safe to change.
    payload = {
        "audio_url": audio_url,
        "speech_models": [model],
        "punctuate": punctuate,
        "format_text": format_text,
    }

    if language_code:
        payload["language_code"] = language_code
    else:
        payload["language_detection"] = True

    if speaker_labels:
        payload["speaker_labels"] = True
        if speakers_expected > 0:
            payload["speakers_expected"] = speakers_expected
    if sentiment_analysis:
        payload["sentiment_analysis"] = True
    if entity_detection:
        payload["entity_detection"] = True
    if auto_highlights:
        payload["auto_highlights"] = True
    if iab_categories:
        payload["iab_categories"] = True
    if filter_profanity:
        payload["filter_profanity"] = True
    if disfluencies:
        payload["disfluencies"] = True

    # The API expects a list of clean terms, so we normalize user text input here.
    keyterms = [k.strip() for k in keyterms_input.split(",") if k.strip()]
    if keyterms:
        payload["keyterms_prompt"] = keyterms
    if prompt_input.strip():
        payload["prompt"] = prompt_input.strip()

    return payload


def build_params_snapshot(
    *,
    speaker_labels: bool,
    sentiment_analysis: bool,
    entity_detection: bool,
    auto_highlights: bool,
    iab_categories: bool,
) -> dict:
    return {
        "speaker_labels": speaker_labels,
        "sentiment_analysis": sentiment_analysis,
        "entity_detection": entity_detection,
        "auto_highlights": auto_highlights,
        "iab_categories": iab_categories,
    }
