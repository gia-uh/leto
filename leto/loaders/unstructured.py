import spacy
import io
from textacy.extract import subject_verb_object_triples
from leto.utils import Text, get_model

import enum

from ..loaders import Loader


class Language(str, enum.Enum):
    es = "es_core_news_sm"
    en = "en_core_web_sm"


class SVOFromText(Loader):
    """
    Load subject-verb-object triplets from natural language text.
    """

    def __init__(self, text: Text, language: Language) -> None:
        self.text = text
        self.language = language

    @classmethod
    def title(cls):
        return "From Plain Text"

    def _load(self):
        nlp = get_model(self.language)

        for subj, verb, obj in get_svo_tripplets(nlp, self.text):
            yield (
                "_".join(s.text for s in subj),
                "_".join(s.text for s in verb),
                "_".join(s.text for s in obj),
            )


class SVOFromFile(Loader):
    """
    Load subject-verb-object triplets from natural language in a text file.
    """

    def __init__(self, file: io.BytesIO, language: Language) -> None:
        self.file = file
        self.language = language

    @classmethod
    def title(cls):
        return "From Text File"

    def _load(self):
        nlp = get_model(self.language)

        for line in self.file.readlines():
            for subj, verb, obj in get_svo_tripplets(nlp, line.decode("utf8")):
                yield (
                    "_".join(s.text for s in subj),
                    "_".join(s.text for s in verb),
                    "_".join(s.text for s in obj),
                )


def get_svo_tripplets(nlp: spacy.Language, text: str):
    """Get simple subject - verb - object triples from text.

    Args:
        nlp (spacy.Language): Language model pipeline for text processing
        text (str): Text where the extraction will occur

    Returns:
        SVO triples Generator: Sunject - verb - object triples generator
    """
    doc = nlp(text)
    return subject_verb_object_triples(doc)


"""
Usage Example:

nlp = get_model("en_core_web_sm")
for triplet in get_svo_tripplets(nlp, "The user knows nothing, and yet, owns a lot. The sister does not like cookies"):
    print(triplet)
"""
