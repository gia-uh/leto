from typing import List
import streamlit as st

from .loaders import get_loaders
from .storage import Storage, get_storages
from .query import QueryParser, QueryResolver, get_parsers
from .visualization import DummyVisualizer, Visualizer, MapVisualizer
from io import StringIO


def bootstrap():
    st.title("🧠 LETO: Learning Engine Through Ontologies")

    with st.sidebar:
        storages = { cls.__name__:cls for cls in get_storages() }
        st.markdown("## 💾 Data storage info")
        storage_cls = storages[st.selectbox("Storage driver", list(storages))]

    storage: Storage = storage_cls()
    resolver: QueryResolver = storage.get_query_resolver()
    visualizers: List[Visualizer] = [DummyVisualizer(), MapVisualizer()]

    main, side = st.beta_columns((2, 1))

    with side:
        with st.beta_expander("🔥 Load new data", False):
            load_data(storage)

    with st.sidebar:
        st.write(f"Current size: {storage.size} tuples")

    with st.sidebar:
        parsers = { cls.__name__:cls for cls in get_parsers() }
        st.markdown("## 🧙‍♂️ Query parsing")
        parser_cls = parsers[st.selectbox("Query parser", list(parsers))]

    parser: QueryParser = parser_cls()

    with main:
        query_text = st.text_input("🔮 Enter a query for LETO")

        if query_text:
            query = parser.parse(query_text)

            st.write("#### 💡 Interpreting query as:")
            st.code(query)

            response = list(resolver.resolve(query))

            visualizations = [visualizer.visualize(query, response) for visualizer in visualizers]
            visualizations = [v for v in visualizations if v.valid()]
            visualizations.sort(key=lambda v: v.score, reverse=True)

            for viz in visualizations:
                viz.visualize()


def load_data(storage):
    loaders = {cls.__name__: cls for cls in get_loaders()}
    loader_cls = loaders[st.selectbox("Loader", list(loaders))]

    docstring = loader_cls.__doc__

    if docstring is not None:
        st.write(loader_cls.__doc__)

    loader = _build_cls(loader_cls)

    if st.button("🚀 Run"):
        for i, relation in enumerate(loader.load()):
            storage.store(relation)

        st.success(f"🥳 Succesfully loaded {i+1} tuples!")


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
