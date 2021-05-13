import streamlit as st

from .loaders import get_loaders
from .storage import get_storages
from .query import DummyQueryResolver
from .visualization import DummyVisualizer
from io import StringIO


def bootstrap():
    st.title("🧠 LETO: Learning Engine Through Ontologies")

    storages = { cls.__name__:cls for cls in get_storages() }

    with st.sidebar:
        st.markdown("## 💾 Data storage info")
        storage_cls = storages[st.selectbox("Storage driver", list(storages))]

    storage = storage_cls()
    resolver = DummyQueryResolver()
    visualizer = DummyVisualizer()

    main, side = st.beta_columns((2, 1))

    with side:
        with st.beta_expander("🔥 Load new data", False):
            load_data(storage)

    with st.sidebar:
        st.write(f"Current size: {storage.size} tuples")

    with main:
        query_text = st.text_input("🔮 Enter a query for LETO")

        if query_text:
            response = resolver.query(query_text, storage)
            visualizer.visualize(query_text, response)


def load_data(storage):
    loaders = {cls.__name__: cls for cls in get_loaders()}
    loader_cls = loaders[st.selectbox("Loader", list(loaders))]
    loader = _build_cls(loader_cls)

    if st.button("🚀 Run"):
        for tuple in loader.load():
            storage.store_tuple(*tuple)


def _build_cls(cls):
    import typing
    import enum
    import io

    init_args = typing.get_type_hints(cls.__init__)
    init_values = {}

    for k, v in init_args.items():
        if v == int:
            init_values[k] = st.number_input(k, value=0)
        elif v == StringIO:
            init_values[k] = st.file_uploader(k, accept_multiple_files=False)
        elif v == str:
            init_values[k] = st.text_area(k, value="")
        elif issubclass(v, enum.Enum):
            values = { e.name: e.value for e in v }
            init_values[k] = values[st.selectbox(k, list(values))]
        elif v == io.BytesIO:
            init_values[k] = st.file_uploader(k)

    return cls(**init_values)
