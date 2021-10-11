from typing import List
import streamlit as st
from textwrap import dedent

from .loaders import get_loaders
from .storage import Storage, get_storages
from .query import QueryParser, QueryResolver, get_parsers
from .visualization import (
    DummyVisualizer,
    Visualizer,
    MapVisualizer,
    GraphVisualizer,
    CountVisualizer,
    PredictVisualizer,
)
from io import StringIO


def bootstrap():
    st.title("🧠 LETO: Learning Engine Through Ontologies")

    with st.sidebar:
        with st.expander("⚙️ Config", False):
            storages = {cls.__name__: cls for cls in get_storages()}
            storage_cls = storages[st.selectbox("💾 Storage driver", list(storages))]
            storage: Storage = _build_cls(storage_cls)
            st.metric(f"Current size (tuples)", storage.size)
            parsers = {cls.__name__: cls for cls in get_parsers()}
            parser_cls = parsers[st.selectbox("🧙‍♂️ Query parser", list(parsers))]
            parser: QueryParser = parser_cls(storage)

        with st.expander("🔥 Load new data", True):
            load_data(storage)

    resolver: QueryResolver = storage.get_query_resolver()
    visualizers: List[Visualizer] = [
        DummyVisualizer(),
        MapVisualizer(),
        GraphVisualizer(),
        CountVisualizer(),
        PredictVisualizer(),
    ]

    main, side = st.columns((2, 1))

    with side:
        st.markdown("### ❓ Example queries")
        st.info(
            "If you have loaded the example data, you can try some of these queries to see an example of LETO's functionality."
        )
        example_queries()

    with main:
        query_text = st.text_input("🔮 Enter a query for LETO", key="query_input")

        if query_text:
            query = parser.parse(query_text)
            response = resolver.resolve(query)

            st.write("#### 💡 Interpreting query as:")
            st.code(query)

            if not response:
                st.error("😨 No data was found to answer that query!")
                st.stop()

            visualizations = [
                visualizer.visualize(query, response) for visualizer in visualizers
            ]
            visualizations = [v for v in visualizations if v.valid()]
            visualizations.sort(key=lambda v: v.score, reverse=True)

            for viz in visualizations:
                viz.visualize()


def load_data(storage):
    loaders = {cls.title(): cls for cls in get_loaders()}
    loader_cls = loaders[st.selectbox("Loader", list(loaders))]

    docstring = dedent(loader_cls.__doc__)

    if docstring is not None:
        st.write(docstring)

    loader = _build_cls(loader_cls)

    metadata = st.text_area("🏷️ Metadata").split("\n")
    meta = {}

    for line in metadata:
        if line:
            k, v = line.split("=")
            meta[k.strip()] = v.strip()

    if st.button("🚀 Run"):
        progress = st.empty()

        for i, relation in enumerate(loader.load(**meta)):
            progress.warning(f"⚙️ Loading {i+1} tuples...")
            try:
                storage.store(relation)
            except Exception as e:
                print(e)

        progress.success(f"🥳 Succesfully loaded {i+1} tuples!")


def example_queries():
    example_query = ""

    for q in [
        "show me info about Cuba",
        "who has led a Revolution",
        "where has there been a Revolution",
        "Cuban Revolution and Vladimir Illich Lenin",
        "how much is the salary of a DataScientist by gender",
        "which features predict salary in a DataScientist",
    ]:
        if st.button(f"❔ {q}"):
            st.session_state.query_input = q


def _build_cls(cls):
    import typing
    import enum
    import io
    from leto.utils import Text

    init_args = typing.get_type_hints(cls.__init__)
    init_values = {}

    for k, v in init_args.items():
        if v == int:
            init_values[k] = st.number_input(k, value=0)
        elif v == StringIO:
            init_values[k] = st.file_uploader(k, accept_multiple_files=False)
        elif v == str:
            init_values[k] = st.text_input(k, value="")
        elif v == Text:
            init_values[k] = st.text_area(k, value="")
        elif v == io.BytesIO:
            init_values[k] = st.file_uploader(k)
        elif v == List[io.BytesIO]:
            init_values[k] = st.file_uploader(k, accept_multiple_files=True)
        elif issubclass(v, enum.Enum):
            values = {e.name: e.value for e in v}
            init_values[k] = values[st.selectbox(k, list(values))]

    return cls(**init_values)
