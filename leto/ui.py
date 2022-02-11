from random import shuffle
from typing import List
from leto.query.rules import RuleBasedQueryParser
import streamlit as st
from textwrap import dedent

from .loaders import get_loaders
from .storage import Storage, get_storages
from .query import QueryParser, QueryResolver, get_parsers
from .visualization import Visualizer, get_visualizers
from io import StringIO


def bootstrap():
    st.title("🧠 LETO: Learning Engine Through Ontologies")

    with st.sidebar:
        with st.expander("⚙️ Config", False):
            storages = {cls.__name__: cls for cls in get_storages()}
            storage_cls = storages[st.selectbox("💾 Storage driver", list(storages))]
            storage: Storage = _build_cls(storage_cls)
            storage_size = st.empty()
            storage_size.metric(f"No. of facts", storage.size)
            parser: QueryParser = RuleBasedQueryParser(storage)
            query_breadth = int(
                st.number_input("🔮 Query breadth", value=2, min_value=1)
            )
            max_entities = int(
                st.number_input("🔮 Max results", value=100, min_value=1)
            )

            if st.button("💣 Clear database"):
                storage.clear()
                storage_size.metric(f"No. of facts", storage.size)

        with st.expander("🔥 Load new data", True):
            load_data(storage, storage_size)

    resolver: QueryResolver = storage.get_query_resolver()
    visualizers: List[Visualizer] = get_visualizers()

    main, side = st.columns((2, 1))

    with side:
        st.markdown("### ❓ Example queries")
        st.info(
            "Follow the tutorial at https://leto-ai.github.io/tutorial to load the data necessary to run the following queries."
        )
        example_queries()

    with main:
        query_text = st.text_input(
            "🔮 Enter a query for LETO", value=st.session_state.get("query_input", "")
        )

        if query_text:
            query = parser.parse(query_text)

            st.write("#### 💡 Interpreting query as:")
            st.code(query)

            response = resolver.resolve(query, query_breadth, max_entities)

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


def load_data(storage, widget):
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
        i = -1

        for i, entity_or_relation in enumerate(loader.load(**meta)):
            progress.warning(f"⚙️ Loading {i+1} facts...")
            print(entity_or_relation, flush=True)
            storage.store(entity_or_relation)

        if i >= 0:
            progress.success(f"🥳 Succesfully loaded {i+1} facts!")
        else:
            progress.warning(f"⚠️ No facts where found!")

        widget.metric(f"No. of facts", storage.size)


def example_queries():
    example_query = ""

    def set_example_query(q):
        st.session_state.query_input = q

    for q in [
        "alicante",
        "alicante mentions",
        "alicante ratings by location",
        "alicante ratings and likes by location",
        "spain tourists by country",
        "alicante ~unemploymentinfo",
        "alicante unemployment by municipality ~location"
    ]:
        st.button(f"❔ {q}", on_click=set_example_query, args=(q,))


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
        if v == float:
            init_values[k] = st.slider(k, value=0.5, min_value=0.0, max_value=1.0)
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
