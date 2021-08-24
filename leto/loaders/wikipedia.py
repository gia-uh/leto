from typing import Iterable
import spacy
import wikipedia
from leto.model import Entity, Relation
from leto.loaders.unstructured import get_svo_tripplets, get_model
from leto.loaders.unstructured import Language
import subprocess
from leto.loaders import Loader


def get_coreference_resolved_docs(nlp: spacy.Language, docs: Iterable[str]):
    updated_docs = []
    for doc in nlp.pipe(docs):
        new_doc = []
        for token in doc:
            tok = doc._.coref_chains.resolve(token) or token
            tok_text = (
                " and ".join([t.text for t in tok])
                if (isinstance(tok, list))
                else tok.text
            )
            tok_text += token.whitespace_
            new_doc.append(tok_text)

        updated_docs.append("".join(new_doc))
    return updated_docs


class WikipediaLoader(Loader):
    """
    Load all the content from a specific Wikipedia page.
    """

    def __init__(self, query: str, language: Language) -> None:
        self.query = query
        self.language = language

    def load(self):
        if self.language is Language.es:
            wikipedia.set_lang("es")

        page = wikipedia.page(self.query)
        return _seed_content(page.content, self.language)


def _seed_content(content: str, language: Language):
    nlp = get_model(language)

    ready_content = content
    if language is Language.en:  # download english model
        subprocess.run(["python3", "-m", "coreferee", "install", "en"])
        nlp.add_pipe("coreferee")
        ready_content = get_coreference_resolved_docs(nlp, [content])[0]

    for triplet in get_svo_tripplets(nlp, ready_content):
        subject_str = " ".join(
            map(lambda x: str(x).strip().lower(), triplet.subject)
        ).strip()
        verb_str = "_".join(
            map(lambda x: str(x.lemma_.strip().lower()), triplet.verb)
        ).strip()
        object_str = " ".join(
            map(lambda x: str(x).strip().lower(), triplet.object)
        ).strip()

        subject_types = set(map(lambda x: x.ent_type_, triplet.subject))
        object_types = set(map(lambda x: x.ent_type_, triplet.object))

        # remove unnecessarily repeated relations without accurate type
        if any(subject_types):
            try:
                subject_types.remove("")
                subject_types.remove(" ")
            except:
                pass

        if any(object_types):
            try:
                object_types.remove("")
                object_types.remove(" ")
            except:
                pass

        # create relations
        for subject_type in subject_types:
            subject_entity = Entity(
                subject_str,
                subject_type
                if not (subject_type.isspace() or subject_type == "")
                else "THING",
            )

            for object_type in object_types:
                object_entity = Entity(
                    object_str,
                    object_type
                    if not (object_type.isspace() or object_type == "")
                    else "THING",
                )
            relation = Relation(verb_str, subject_entity, object_entity)
            yield relation


"""
Example:

seed_from_wikipedia("October revolution")
seed_from_wikipedia("World War II")
seed_from_wikipedia("Lenin")
"""
