from leto.model import Entity, Relation, Source
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

    def _get_source(self, name, **metadata) -> Source:
        return Source(name, method="text", loader="SVOFromText", **metadata)

    def _sentences(self):
        yield self.text

    def _load(self):
        nlp = get_model(self.language)

        for sentence in self._sentences():
            for subj, verb, obj in get_svo_tripplets(nlp, sentence):
                yield Relation(
                    label="_".join(s.lemma_ for s in verb),
                    entity_from=Entity("_".join(s.text for s in subj), "Thing"),
                    entity_to=Entity("_".join(s.text for s in obj), "Thing"),
                )


class SVOFromFile(SVOFromText):
    """
    Load subject-verb-object triplets from natural language in a text file.
    """

    def __init__(self, file: io.BytesIO, language: Language) -> None:
        self.file = file
        self.language = language

    @classmethod
    def title(cls):
        return "From Text File"

    def _get_source(self, name, **metadata) -> Source:
        return Source(name, method="text", loader="SVOFromFile", **metadata)

    def _sentences(self):
        with open(self.file) as fp:
            for line in fp:
                yield line


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
