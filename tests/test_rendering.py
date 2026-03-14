from assemblyai_explorer.rendering import extract_iab_topic_scores


def test_extract_iab_topic_scores_handles_mixed_shapes():
    data = [
        {"label": "Technology > Software", "relevance": 0.91},
        {
            "labels": [
                {"label": "Business > Finance", "relevance": 0.72},
                {"label": "Broken"},
            ]
        },
        {"labels": []},
    ]

    scores = extract_iab_topic_scores(data)

    assert scores == [
        {"label": "Technology > Software", "relevance": 0.91},
        {"label": "Business > Finance", "relevance": 0.72},
    ]
