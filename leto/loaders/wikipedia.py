import itertools
import json
import urllib
from typing import Iterable

import opennre
import spacy
from leto.loaders import Loader
from leto.loaders.unstructured import Language
from leto.model import Entity, Relation, Source
from leto.utils import get_model

import wikipedia


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
        if "wikiDataClasses" in annotation:
            results.append(
                {
                    "title": annotation["title"],
                    "wikiId": annotation["wikiDataItemId"],
                    "label": annotation["wikiDataClasses"],
                    "characters": [
                        (el["chFrom"], el["chTo"]) for el in annotation["support"]
                    ],
                }
            )
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

    def __init__(
        self, query: str, language: Language, sensitivity: float=0.7
    ) -> None:
        self.query = query
        self.language = language
        self.relationship_min_score = sensitivity

    def _get_source(self, name, **metadata) -> Source:
        return Source(name, method="web", loader="WikipediaLoader", **metadata)

    def _load(self):
        if self.language is Language.es:
            wikipedia.set_lang("es")

        page = wikipedia.page(self.query)
        return _seed_content(page.content, self.language, self.relationship_min_score)


def _seed_content(content: str, language: Language, relationship_min_score=0.7):
    nlp = get_model(language)

    ready_content = content
    # if language is Language.en:  # download english model
    #     try:
    #         nlp.add_pipe("coreferee")
    #     except:
    #         (statusCode,_) = subprocess.getstatusoutput("python -m coreferee install en")
    #         if (statusCode != 0):
    #             raise Exception("Failed to install en model for Coreferee")
    #         nlp.add_pipe("coreferee")

    #     ready_content = get_coreference_resolved_docs(nlp, [content])[0]

    doc = nlp(ready_content)
    # First get all the entities in the sentence
    entities = []

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
                        if (
                            data[1] > reverseData[1]
                            and data[1] > relationship_min_score
                        ):
                            relation = {
                                "source": s_entities[combination[0]],
                                "target": s_entities[combination[1]],
                                "type": data[0],
                            }

                        if (
                            reverseData[1] > data[1]
                            and reverseData[1] > relationship_min_score
                        ):
                            relation = {
                                "source": s_entities[combination[1]],
                                "target": s_entities[combination[0]],
                                "type": reverseData[0],
                            }
                    else:
                        if data[1] > relationship_min_score:
                            relation = {
                                "source": s_entities[combination[0]],
                                "target": s_entities[combination[1]],
                                "type": data[0],
                            }

                        if reverseData[1] > relationship_min_score:
                            relation = {
                                "source": s_entities[combination[1]],
                                "target": s_entities[combination[0]],
                                "type": reverseData[0],
                            }

                    if not relation is None:
                        relations_list.append(relation)

                        subject_entity = Entity(
                            relation["source"]["title"],
                            "thing",
                            wikiId=relation["source"]["wikiId"],
                        )

                        object_entity = Entity(
                            relation["target"]["title"],
                            "thing",
                            wikiId=relation["target"]["wikiId"],
                        )

                        graph_relation = Relation(
                            relation["type"].replace(" ", "_"),
                            subject_entity,
                            object_entity,
                        )

                        # Generate every "is_a" relations for the subject entity
                        for slabel in relation["source"]["label"]:
                            label_entity = Entity(slabel["enLabel"], "thing")
                            label_relation = Relation(
                                "is_a", subject_entity, label_entity
                            )
                            yield label_relation
                            break

                        # Generate every "is_a" relations for the object entity
                        for slabel in relation["target"]["label"]:
                            label_entity = Entity(slabel["enLabel"], "thing")
                            label_relation = Relation(
                                "is_a", object_entity, label_entity
                            )
                            yield label_relation
                            break

                        # Generate relation between subject and object entities
                        yield graph_relation

    entities_set = set([e["wikiId"] for e in entities])
    print(
        f"created {len(entities_set)} entities and {len(relations_list)} relationships"
    )


def seed_from_wikipedia(wikipedia_page_title: str, language: Language = Language.en):
    if language is Language.es:
        wikipedia.set_lang("es")

    page = wikipedia.page(wikipedia_page_title)
    yield from _seed_content(page.content, language)


def query_wikipedia(query: str):
    return wikipedia.search(query)
