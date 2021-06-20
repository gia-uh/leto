import wikipedia
from leto.model import Entity, Relation
from leto.storage.neo4j_storage import GraphStorage
from leto.loaders.unstructured import get_model, get_svo_tripplets

def _store_svo_triplets(text:str):
    storage = GraphStorage()
    nlp = get_model("en_core_web_sm")
    for triplet in get_svo_tripplets(nlp, text):
        try:
            subject = Entity(" ".join(map(lambda x: str(x).lower(), triplet[0])), "Something")
            object = Entity(" ".join(map(lambda x: str(x).lower(), triplet[2])), "Something")
            relation = Relation("_".join(map(lambda x: str(x).lower(), triplet[1])), subject, object)
            storage.store(relation)
            print("stored relation:", relation)
        except:
            print("failed to create relation:", relation)
            continue

def seed_python_knowledge():
    page = wikipedia.page(wikipedia.search("Python programming language")[0])
    _store_svo_triplets(page.content)

def seed_football_knowledge():
    page = wikipedia.page(wikipedia.search("Football")[0])
    _store_svo_triplets(page.content)

def run_seed():
    seed_python_knowledge()
    seed_football_knowledge()

if (__name__ == "__main__"):
    run_seed()