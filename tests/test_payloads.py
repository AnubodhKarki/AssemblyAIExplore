from assemblyai_explorer.payloads import build_params_snapshot, build_transcript_payload


def test_build_transcript_payload_with_auto_language_and_prompts():
    payload = build_transcript_payload(
        audio_url="https://example.com/audio.mp3",
        model="universal-3-pro",
        language_code=None,
        punctuate=True,
        format_text=True,
        speaker_labels=True,
        speakers_expected=2,
        sentiment_analysis=True,
        entity_detection=True,
        auto_highlights=True,
        iab_categories=True,
        filter_profanity=True,
        disfluencies=True,
        keyterms_input="opal, Oprah Winfrey,  test ",
        prompt_input="  This is an interview.  ",
    )

    assert payload["audio_url"] == "https://example.com/audio.mp3"
    assert payload["speech_models"] == ["universal-3-pro"]
    assert payload["language_detection"] is True
    assert payload["speaker_labels"] is True
    assert payload["speakers_expected"] == 2
    assert payload["sentiment_analysis"] is True
    assert payload["entity_detection"] is True
    assert payload["auto_highlights"] is True
    assert payload["iab_categories"] is True
    assert payload["filter_profanity"] is True
    assert payload["disfluencies"] is True
    assert payload["keyterms_prompt"] == ["opal", "Oprah Winfrey", "test"]
    assert payload["prompt"] == "This is an interview."


def test_build_transcript_payload_with_explicit_language_and_no_optional_prompts():
    payload = build_transcript_payload(
        audio_url="https://example.com/audio.mp3",
        model="universal-2",
        language_code="en_us",
        punctuate=False,
        format_text=False,
        speaker_labels=False,
        speakers_expected=0,
        sentiment_analysis=False,
        entity_detection=False,
        auto_highlights=False,
        iab_categories=False,
        filter_profanity=False,
        disfluencies=False,
        keyterms_input=" , ",
        prompt_input="",
    )

    assert payload["language_code"] == "en_us"
    assert "language_detection" not in payload
    assert "speaker_labels" not in payload
    assert "keyterms_prompt" not in payload
    assert "prompt" not in payload


def test_build_params_snapshot_contains_only_expected_fields():
    snapshot = build_params_snapshot(
        speaker_labels=True,
        sentiment_analysis=False,
        entity_detection=True,
        auto_highlights=False,
        iab_categories=True,
    )

    assert snapshot == {
        "speaker_labels": True,
        "sentiment_analysis": False,
        "entity_detection": True,
        "auto_highlights": False,
        "iab_categories": True,
    }
