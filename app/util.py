from typing import List
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def unwrap_comments_into_text(items):
    text = ""
    if len(items):
        for item in items:
            if "text" in item:
                text += str(item["text"])
            if "children" in item and len(item["children"]):
                text += unwrap_comments_into_text(item["children"])
    return str(text)

def keywords_in_sentence(words: List[str], sentence: str):
    sentence_chunk = sentence.lower().split(" ")
    for word in words:
        if word.lower() in sentence_chunk:
            return True
    return False

def sentiment_analysis(text: str):
    analzyer = SentimentIntensityAnalyzer()
    vs = analzyer.polarity_scores(text)
    return vs["compound"]