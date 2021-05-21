import functools
import typing

import streamlit as st


def visitor(arg:str):
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
