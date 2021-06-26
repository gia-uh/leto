import abc
import math
from leto.query import MatchQuery, Query, WhatQuery, WhereQuery, WhoQuery
from leto.model import Relation
from typing import Callable, List
import pandas as pd
import streamlit as st
import graphviz


class Visualization:
    def __init__(self, title:str, score:float, run:Callable) -> None:
        self.score = score
        self.title = title
        self.run = run

    def visualize(self):
        with st.beta_expander(self.title, self.score > 0):
            self.run()

    def valid(self) -> bool:
        return True

    class Empty:
        score = 0
        title = None

        def valid(self) -> bool:
            return False


class Visualizer(abc.ABC):
    @abc.abstractmethod
    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        pass


class DummyVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        def visualization():
            st.code("\n".join(str(r) for r in response))

        return Visualization(title="📋 Returned tuples", score=0, run=visualization)


class GraphVisualizer(Visualizer):
    def visualize(self, query: MatchQuery, response: List[Relation]) -> Visualization:
        if not isinstance(query, (MatchQuery, WhatQuery, WhoQuery)):
            return Visualization.Empty()

        def visualization():
            graph = graphviz.Digraph()

            entities = set(e.name for e in query.entities)

            for tuple in response:
                for e in [tuple.entity_from, tuple.entity_to]:
                    color = "white"

                    if e.name in entities:
                        color = "green"

                    graph.node(e.name, fillcolor=color, style="filled")

                graph.edge(tuple.entity_from.name, tuple.entity_to.name, label=tuple.label)

            st.write(graph)

        return Visualization(title="🔗 Entity graph", score=max(0.1, math.log2(len(response))), run=visualization)

class MapVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        if not isinstance(query, (WhereQuery, WhatQuery)):
            return Visualization.Empty()

        mapeable = []

        for tuple in response:
            for e in [tuple.entity_from, tuple.entity_to]:
                if e.attr("lon"):
                    mapeable.append(dict(name=e.name, lat=float(e.lat), lon=float(e.lon)))

        if not mapeable:
            return Visualization.Empty()

        df = pd.DataFrame(mapeable).set_index("name")

        def visualization():
            st.map(df)

        return Visualization(title="🗺️ Map", score=len(df) / len(response), run=visualization)