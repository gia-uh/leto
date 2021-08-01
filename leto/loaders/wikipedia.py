import json
from typing import Iterable
import spacy
import wikipedia
from leto.model import Entity, Relation
from leto.loaders.unstructured import get_svo_tripplets, get_model
from leto.storage.neo4j_storage import GraphStorage
from leto.loaders.unstructured import Language
import subprocess
import urllib
from string import punctuation
import nltk
import itertools
import opennre


ENTITY_TYPES = [
    "human",
    "person",
    "company",
    "enterprise",
    "business",
    "geographic region",
    "human settlement",
    "geographic entity",
    "territorial entity type",
    "organization",
]


def wikifier(text, lang="en", threshold=0.7):
    """Function that fetches entity linking results from wikifier.com API"""
    # Prepare the URL.
    data = urllib.parse.urlencode(
        [
            ("text", text),
            ("lang", lang),
            ("userKey", "tgbdmkpmkluegqfbawcwjywieevmza"),
            ("pageRankSqThreshold", "%g" % threshold),
            ("applyPageRankSqThreshold", "true"),
            ("nTopDfValuesToIgnore", "100"),
            ("nWordsToIgnoreFromList", "100"),
            ("wikiDataClasses", "true"),
            ("wikiDataClassIds", "false"),
            ("support", "true"),
            ("ranges", "false"),
            ("minLinkFrequency", "2"),
            ("includeCosines", "false"),
            ("maxMentionEntropy", "3"),
        ]
    )
    url = "http://www.wikifier.org/annotate-article"
    # Call the Wikifier and read the response.
    req = urllib.request.Request(url, data=data.encode("utf8"), method="POST")
    with urllib.request.urlopen(req, timeout=60) as f:
        response = f.read()
        response = json.loads(response.decode("utf8"))
    # Output the annotations.
    results = list()
    for annotation in response["annotations"]:
        # Filter out desired entity classes
        if ("wikiDataClasses" in annotation) and (
            any([el["enLabel"] in ENTITY_TYPES for el in annotation["wikiDataClasses"]])
        ):

            # Specify entity label
            if any(
                [
                    el["enLabel"] in ["human", "person"]
                    for el in annotation["wikiDataClasses"]
                ]
            ):
                label = "Person"
            elif any(
                [
                    el["enLabel"]
                    in ["company", "enterprise", "business", "organization"]
                    for el in annotation["wikiDataClasses"]
                ]
            ):
                label = "Organization"
            elif any(
                [
                    el["enLabel"]
                    in [
                        "geographic region",
                        "human settlement",
                        "geographic entity",
                        "territorial entity type",
                    ]
                    for el in annotation["wikiDataClasses"]
                ]
            ):
                label = "Location"
            else:
                label = "Thing"

            results.append(
                {
                    "title": annotation["title"],
                    "wikiId": annotation["wikiDataItemId"],
                    "label": label,
                    "characters": [
                        (el["chFrom"], el["chTo"]) for el in annotation["support"]
                    ],
                }
            )
        else:
            pass
    return results


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
        nlp.add_pipe("coreferee")
        ready_content = get_coreference_resolved_docs(nlp, [content])[0]

    doc = nlp(ready_content)
    # First get all the entities in the sentence
    entities = []
    # for sent in doc.sents:
    #     entities += wikifier(sent)

    relation_model = opennre.get_model("wiki80_bert_softmax")
    relations_list = []
    for sentence in doc.sents:
        try:
            sentence_entities = wikifier(sentence)
        except:
            continue
        entities += sentence_entities
        s_entities = dict(map(lambda x: (x["wikiId"], x), sentence_entities))
        # Iterate over every permutation pair of entities
        for combination in itertools.combinations(s_entities.keys(), 2):
            for source in s_entities[combination[0]]["characters"]:
                for target in s_entities[combination[1]]["characters"]:
                    # Relationship extraction with OpenNRE
                    data = relation_model.infer(
                        {
                            "text": sentence.text,
                            "h": {"pos": [source[0], source[1] + 1]},
                            "t": {"pos": [target[0], target[1] + 1]},
                        }
                    )
                    reverseData = relation_model.infer(
                        {
                            "text": sentence.text,
                            "h": {"pos": [target[0], target[1] + 1]},
                            "t": {"pos": [source[0], source[1] + 1]},
                        }
                    )

                    relation = None
                    if data[0] == reverseData[0]:
                        if data[1] > reverseData[1] and data[1] > 0.7:
                            relation = {
                                "source": s_entities[combination[0]],
                                "target": s_entities[combination[1]],
                                "type": data[0],
                            }

                        if reverseData[1] > data[1] and reverseData[1] > 0.7:
                            relation = {
                                "source": s_entities[combination[1]],
                                "target": s_entities[combination[0]],
                                "type": reverseData[0],
                            }
                    else:
                        if data[1] > 0.7:
                            relation = {
                                "source": s_entities[combination[0]],
                                "target": s_entities[combination[1]],
                                "type": data[0],
                            }

                        if reverseData[1] > 0.7:
                            relation = {
                                "source": s_entities[combination[1]],
                                "target": s_entities[combination[0]],
                                "type": reverseData[0],
                            }

                    if not relation is None:
                        relations_list.append(relation)
                        subject_entity = Entity(
                            relation["source"]["title"],
                            relation["source"]["label"],
                            wikiId=relation["source"]["wikiId"],
                        )
                        object_entity = Entity(
                            relation["target"]["title"],
                            relation["target"]["label"],
                            wikiId=relation["target"]["wikiId"],
                        )
                        graph_relation = Relation(
                            relation["type"], subject_entity, object_entity
                        )
                        try:
                            graph_db.store(graph_relation)
                            print("Stored relation:", graph_relation, sep=" ")
                        except:
                            pass

    entities_set = set(entities)
    print(
        f"created {len(entities_set)} entities and {len(relations_list)} relationships"
    )


def seed_from_wikipedia(wikipedia_page_title: str, language: Language = Language.en):
    if language is Language.es:
        wikipedia.set_lang("es")

    page = wikipedia.page(wikipedia_page_title)
    _seed_content(page.content, language)


def query_wikipedia(query: str):
    return wikipedia.search(query)


"""
Example:

seed_from_wikipedia("October revolution")
seed_from_wikipedia("World War II")
seed_from_wikipedia("Lenin")
"""

# if __name__ == "__main__":
#     seed_from_wikipedia("Lenin")
