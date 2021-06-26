import wikipedia
from leto.model import Entity, Relation
from leto.loaders.unstructured import get_svo_tripplets, get_model
from leto.storage.neo4j_storage import GraphStorage
from leto.loaders.unstructured import Language


def _seed_content(content: str, language: Language):

    graph_db = GraphStorage()
    nlp = get_model(language)

    for triplet in get_svo_tripplets(nlp, content):
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
            try:
                graph_db.store(relation)
                print("Stored relation:", relation, sep=" ")
            except:
                pass


def seed_knowledge(wikipedia_page: str, language: Language = Language.en):
    if language is Language.es:
        wikipedia.set_lang("es")

    page = wikipedia.page(wikipedia_page)
    _seed_content(page.content, language)


def query_wikipedia(query: str):
    return wikipedia.search(query)


"""
Example:

seed_knowledge("October revolution")
seed_knowledge("World War II")
"""
