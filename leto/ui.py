import streamlit as st

from .loaders import get_loaders
from .storage import DummyStorage
from .query import DummyQueryResolver
from .visualization import DummyVisualizer
from .loaders.structured import CsvLoader
from io import StringIO


storage = DummyStorage()
resolver = DummyQueryResolver()
visualizer = DummyVisualizer()


def bootstrap():
    st.title("🧠 LETO: Learning Engine Through Ontologies")

    main, side = st.beta_columns((2, 1))

    with side:
        with st.beta_expander("🔥 Load new data", False):
            load_data()

        with st.beta_expander("💾 Data storage info", True):
            st.write(f"Current size: {storage.size} tuples")

    with main:
        query_text = st.text_input("🔮 Enter a query for LETO")
        response = resolver.query(query_text, storage)
        visualizer.visualize(query_text, response)


def load_data():
    loaders = {cls.__name__: cls for cls in get_loaders()}
    loader_cls = loaders[st.selectbox("Loader", list(loaders))]
    loader = _build_cls(loader_cls)

    if st.button("🚀 Run"):
        for tuple in loader.load():
            storage.store_tuple(*tuple)


def _build_cls(cls):
    import typing

    init_args = typing.get_type_hints(cls.__init__)
    init_values = {}

    for k, v in init_args.items():
        if v == int:
            init_values[k] = st.number_input(k, value=0)
        if v == StringIO:
            init_values[k] = st.file_uploader(k, accept_multiple_files=False)

    return cls(**init_values)
