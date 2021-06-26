import abc
import math
from leto.query import MatchQuery, Query, WhatQuery, WhereQuery, WhoQuery, HowManyQuery
from leto.model import Relation
from typing import Callable, List
import pandas as pd
import streamlit as st
import graphviz

import plotly.express as px

class Visualization:
    def __init__(self, title: str, score: float, run: Callable) -> None:
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
    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        def visualization():
            graph = graphviz.Digraph()

            entities = set(e.name for e in query.entities)
            main_entities = set()

            for tuple in response:
                for e in [tuple.entity_from, tuple.entity_to]:
                    color = "white"

                    if e.name in entities:
                        color = "green"
                        main_entities.add(e)

                    graph.node(e.name, fillcolor=color, style="filled")

                graph.edge(tuple.entity_from.name, tuple.entity_to.name, label=tuple.label)

            for e in main_entities:
                for attr, value in e.attrs.items():
                    graph.node(f"{attr}={value}", shape="rectangle", fillcolor="yellow", style="filled")
                    graph.edge(e.name, f"{attr}={value}")

            st.write(graph)

        return Visualization(title="🔗 Entity graph", score=max(0.1, math.log2(len(response))), run=visualization)

class MapVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        if not isinstance(query, (WhereQuery, WhatQuery)):
            return Visualization.Empty()

        mapeable = []

        for tuple in response:
            for e in [tuple.entity_from, tuple.entity_to]:
                if "lon" in e.attrs:
                    mapeable.append(dict(name=e.name, lat=float(e.lat), lon=float(e.lon)))

        if not mapeable:
            return Visualization.Empty()

        df = pd.DataFrame(mapeable).set_index("name")

        def visualization():
            st.map(df)

        return Visualization(title="🗺️ Map", score=len(df) / len(response), run=visualization)

class CountVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]):
        if not isinstance(query, HowManyQuery):
            return Visualization.Empty()

        entities = query.entities
        terms = query.terms

        interest_attributes = []

        for R in response:
            if R.label == "is_a" and R.entity_to.name in [x.name for x in entities]:
                for att in R.entity_from.__dict__.keys():
                    if att in terms:
                        interest_attributes.append(att)

        if not interest_attributes:
            return Visualization.Empty()

        data = {"name": [R.entity_from.name for R in response]}
        for att in interest_attributes:
            data[att] = [R.entity_from.get(att) for R in response]

        df = pd.DataFrame(data)
        df.set_index("name", inplace=True)
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass

        def visualization():
            def bars(data: pd.Series,col):
                pd.set_option('plotting.backend', 'plotly')
                st.plotly_chart(data[col].plot.hist())

            def pie(data: pd.Series,col):
                st.plotly_chart(px.pie(df,col))

            switch_paint={
                       'int64':bars,
                       'float64':bars,
                       'object':pie
                       }

            for col in df.columns:
                switch_paint[str(df.dtypes[col])](df,col)

        return Visualization(title="📊 chart", score=len(df), run=visualization)
