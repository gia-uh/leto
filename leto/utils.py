import os
import functools
import typing
import spacy
from pathlib import Path

import streamlit as st


def visitor(arg: str):
    def wrap(fn):
        implementations = {}
        base_type = typing.get_type_hints(fn)[arg]

        @functools.wraps(fn)
        def wrapper(**kwargs):
            best_match = base_type
            x = kwargs[arg]

            for type in implementations:
                if isinstance(x, type) and issubclass(type, best_match):
                    best_match = type

            if best_match == base_type:
                return fn(**kwargs)

            return implementations[type](**kwargs)

        def decorator(f):
            subtype = typing.get_type_hints(f)[arg]

            if not issubclass(subtype, base_type):
                raise TypeError(f"Cannot register function with type {subtype}.")

            implementations[subtype] = f
            return f

        wrapper.register = decorator
        return wrapper

    return wrap


data_directory = str(
    "/home/coder/leto/data/models"
)  # "/home/coder/leto/data/models"  # str(Path(__file__).parent.parent / "data" / "models")


def _ensure_data_directory():
    try:
        os.makedirs(data_directory)
    except:
        pass


def get_model(name: str = "en_core_web_sm") -> spacy.Language:
    """Get an spacy language model from different sources. First, tryes to load
    the model from disk, if fails, then load and install from original repo.

    Args:
        name (str): Name, identification for the language.

    Raises:
        e: IOError if no model with the specified name is found

    Returns:
        spacy.Language: Language
    """
    return spacy.load(name)

    # try:
    #     print("model loading", end="", flush=True)
    #     model = get_local_model(name)
    #     if not model:
    #         print("model not found locally at: ", data_directory)
    #         model = get_online_model(name)
    #     print(" done")
    #     return model
    # except Exception as e:
    #     raise e


@st.experimental_singleton
def get_local_model(name: str) -> spacy.Language:
    """Gets Language model and data from disk

    Args:
        name (str):  Name, identification for the language.

    Returns:
        spacy.Language | None: Preloaded language
    """
    try:
        return spacy.load(os.path.join(data_directory, name))
    except:
        return None


def save_model(model: spacy.Language, name: str):
    """Saves Language model data to disk

    Args:
        model (spacy.Language): Language model to save
        name (str): Name, identification for the language. If name is already in use will override saved data.
    """
    _ensure_data_directory()
    model.to_disk(os.path.join(data_directory, name))


def get_online_model(
    name: str, save_to_local: bool = True, pythonNick: str = "python"
) -> spacy.Language:
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
    if save_to_local:
        save_model(nlp, name)
    return nlp


class Text(str):
    def __new__(cls, *args, **kwargs):
        return cls.__new__(*args, **kwargs)
