import streamlit as st


def extract_iab_topic_scores(iab_results: list[dict]) -> list[dict]:
    topic_scores = []
    for item in iab_results:
        if "label" in item and "relevance" in item:
            topic_scores.append(item)
        for label_item in item.get("labels", []):
            if "label" in label_item and "relevance" in label_item:
                topic_scores.append(label_item)
    return topic_scores


def render_results(result: dict, params: dict, allow_expanders: bool = True):
    if result["status"] == "error":
        st.error(f"Transcription failed: {result.get('error', 'Unknown error')}")
        return

    st.subheader("Transcript")
    st.write(result.get("text", ""))

    if params.get("speaker_labels") and result.get("utterances"):
        st.subheader("Speaker Diarization")
        rows = [
            {
                "Speaker": u["speaker"],
                "Start (s)": round(u["start"] / 1000, 2),
                "End (s)": round(u["end"] / 1000, 2),
                "Text": u["text"],
            }
            for u in result["utterances"]
        ]
        st.dataframe(rows, use_container_width=True)

    if params.get("sentiment_analysis") and result.get("sentiment_analysis_results"):
        st.subheader("Sentiment Analysis")
        sentiments = result["sentiment_analysis_results"]
        counts = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0}
        for sentiment in sentiments:
            counts[sentiment["sentiment"]] = counts.get(sentiment["sentiment"], 0) + 1
        st.bar_chart(counts)
        if allow_expanders:
            with st.expander("Sentence details"):
                for sentiment in sentiments:
                    st.write(f"**{sentiment['sentiment']}** — {sentiment['text']}")
        else:
            st.caption("Sentence details")
            for sentiment in sentiments:
                st.write(f"**{sentiment['sentiment']}** — {sentiment['text']}")

    if params.get("entity_detection") and result.get("entities"):
        st.subheader("Entities")
        rows = [{"Type": entity["entity_type"], "Text": entity["text"]} for entity in result["entities"]]
        st.dataframe(rows, use_container_width=True)

    if params.get("auto_highlights") and result.get("auto_highlights_result", {}).get("results"):
        st.subheader("Key Phrases")
        rows = [
            {"Phrase": item["text"], "Count": item["count"], "Rank": round(item["rank"], 3)}
            for item in result["auto_highlights_result"]["results"]
        ]
        st.dataframe(rows, use_container_width=True)

    if params.get("iab_categories") and result.get("iab_categories_result", {}).get("results"):
        st.subheader("Topics (IAB)")
        topic_scores = extract_iab_topic_scores(result["iab_categories_result"]["results"])
        if topic_scores:
            top = sorted(topic_scores, key=lambda x: x["relevance"], reverse=True)[:10]
            rows = [{"Topic": t["label"].split(">")[-1].strip(), "Relevance": round(t["relevance"], 3)} for t in top]
            st.dataframe(rows, use_container_width=True)
