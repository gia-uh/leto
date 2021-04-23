import spacy
import os
import textacy

data_directory = "/src/data/models"
                                   
def get_model(name:str)-> spacy.Language:
    """Get an spacy language model from different sources. First, tryes to load
    the model from disk, if fails, then load and install from original repo.

    Args:
        name (str): Name, identification for the language.

    Raises:
        e: IOError if no model with the specified name is found

    Returns:
        spacy.Language: Language
    """    
    try:
        model = get_local_model(name)
        if (not model):
            model = get_online_model(name)
        return model
    except Exception as e:
        raise e
    
def get_local_model(name:str) -> spacy.Language:
    """Gets Language model and data from disk

    Args:
        name (str):  Name, identification for the language.

    Returns:
        spacy.Language | None: Preloaded language
    """    
    try:
        return spacy.load(name).from_disk(os.path.join(data_directory, name))
    except:
        return None

def save_model(model: spacy.Language, name:str):
    """Saves Language model data to disk

    Args:
        model (spacy.Language): Language model to save
        name (str): Name, identification for the language. If name is already in use will override saved data.
    """    
    config = model.config
    model.to_disk(os.path.join(data_directory, name))

def get_online_model(name:str, save_to_local:bool = True, pythonNick:str = "python") -> spacy.Language:
    """Load and install spacy language model from original repo. If save_to_local then save to disk after load.

    Args:
        name (str): Name, identification for the language.
        save_to_local (bool, optional): Enable save model to disk. Defaults to True.
        pythonNick (str, optional): Python alias used for current python version. Defaults to "python".

    Returns:
        spacy.Language: Name, identification for the language.
    """    
    os.system(f"{pythonNick} -m spacy download {name}")
    nlp = spacy.load(name)
    if (save_to_local):
        save_model(nlp, name)
    return nlp

def get_svo_tripplets(nlp: spacy.Language, text:str): 
    """Get simple subject - verb - object triples from text.

    Args:
        nlp (spacy.Language): Language model pipeline for text processing
        text (str): Text where the extraction will occur

    Returns:
        SVO triples Generator: Sunject - verb - object triples generator
    """    
    doc = nlp(text)
    return textacy.extract.subject_verb_object_triples(doc)
    

"""
Usage Example:

nlp = get_model("en_core_web_sm")
for triplet in get_svo_tripplets(nlp, "The user knows nothing, and yet, owns a lot. The sister does not like cookies"):
    print(triplet)
"""
