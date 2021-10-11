import abc
import json
import math
from typing import Callable, List

import altair as alt
import graphviz
import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
from leto.model import Relation
from leto.query import (
    HowManyQuery,
    MatchQuery,
    PredictQuery,
    Query,
    WhatQuery,
    WhereQuery,
    WhoQuery,
)
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LinearRegression, LogisticRegression


class Visualization:
    def __init__(self, title: str, score: float, run: Callable) -> None:
        self.score = score
        self.title = title
        self.run = run

    def visualize(self):
        with st.expander(self.title, self.score > 0):
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

            entities = set(query.entities)
            main_entities = set()

            for tuple in response:
                for e in [tuple.entity_from, tuple.entity_to]:
                    color = "white"

                    if e.name in entities:
                        color = "green"
                        main_entities.add(e)

                    graph.node(e.name, fillcolor=color, style="filled")

                graph.edge(
                    tuple.entity_from.name, tuple.entity_to.name, label=tuple.label
                )

            for e in main_entities:
                for attr, value in e.attrs.items():
                    graph.node(
                        f"{attr}={value}",
                        shape="rectangle",
                        fillcolor="yellow",
                        style="filled",
                    )
                    graph.edge(e.name, f"{attr}={value}")

            st.write(graph)

        return Visualization(
            title="🔗 Entity graph",
            score=max(0.1, math.log2(len(response))),
            run=visualization,
        )


class MapVisualizer(Visualizer):
    def __init__(self) -> None:
        with open("/home/coder/leto/data/countries.geo.json") as fp:
            self.data = json.load(fp)["features"]

    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        if not isinstance(query, (WhereQuery, WhatQuery)):
            return Visualization.Empty()

        mapeable = []

        for tuple in response:
            for e in [tuple.entity_from, tuple.entity_to]:
                if "lon" in e.attrs:
                    mapeable.append(
                        dict(name=e.name, lat=float(e.lat), lon=float(e.lon))
                    )

        if not mapeable:
            return Visualization.Empty()

        regions = set(d["name"] for d in mapeable)
        df = pd.DataFrame(mapeable).set_index("name")

        def visualization():
            data = [
                feature
                for feature in self.data
                if feature["properties"]["name"] in regions
            ]

            geojson = pdk.Layer(
                "GeoJsonLayer",
                data,
                opacity=0.8,
                stroked=False,
                filled=True,
                extruded=True,
                wireframe=True,
                get_elevation=1,
                get_fill_color=[255, 255, 255],
                get_line_color=[255, 255, 255],
            )
            map = pdk.Deck(layers=[geojson])

            st.pydeck_chart(map)

        return Visualization(
            title="🗺️ Map", score=len(df) / len(response), run=visualization
        )


class CountVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]):
        if not isinstance(query, HowManyQuery):
            return Visualization.Empty()

        entities = set(str(e) for e in query.entities)
        field = str(query.attributes[0])
        attributes = [str(a) for a in query.attributes[1:]]

        data = []

        for R in response:
            if R.label == "is_a" and R.entity_to.name in entities:
                attrs = {attr: R.entity_from.get(attr) for attr in attributes}
                value = R.get(field)
                attrs[field] = R.get(field)

                if value is not None:
                    data.append(dict(name=R.entity_from.name, **attrs))

        if not data:
            return Visualization.Empty()

        df = pd.DataFrame(data)
        df.set_index("name", inplace=True)

        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass

        def visualization():
            def bars(data: pd.Series, col):
                pd.set_option("plotting.backend", "plotly")
                st.plotly_chart(data[col].plot.hist())

            def pie(data: pd.Series, col):
                st.plotly_chart(px.pie(df, col))

            switch_paint = {"int64": bars, "float64": bars, "object": pie}

            for col in df.columns:
                switch_paint[str(df.dtypes[col])](df, col)

        return Visualization(title="📊 Chart", score=len(df), run=visualization)


class PredictVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]):
        if not isinstance(query, PredictQuery):
            return Visualization.Empty()

        entities = query.entities
        terms = set(str(a) for a in query.attributes)

        target_attributes = set()
        features = set()

        for relation in response:
            attrs = set(relation.entity_from.attrs)
            attrs.update(relation.attrs)

            targets = attrs & terms

            if not targets:
                continue

            target_attributes.update(targets)
            features.update(attrs - targets)

        data = []
        targets = []

        for relation in response:
            datum = {
                k: relation.entity_from.get(k) or relation.get(k) for k in features
            }
            target = {
                k: relation.entity_from.get(k) or relation.get(k)
                for k in target_attributes
            }

            if None in datum.values() or None in target.values():
                continue

            data.append(datum)
            targets.append(target)

        print(data, targets)

        def visualization():
            vect = DictVectorizer()
            X = vect.fit_transform(data)

            for attr in target_attributes:
                y = [d.get(attr) for d in targets]

                if isinstance(y[0], (int, float)):
                    model = LinearRegression()
                    model.fit(X, y)
                    coef = model.coef_.reshape(1, -1)
                else:
                    model = LogisticRegression()
                    model.fit(X, y)
                    coef = model.coef_

                features_weights = [
                    dict(feature=f, weight=abs(w), positive=w > 0)
                    for f, w in vect.inverse_transform(coef)[0].items()
                ]
                features_weights = pd.DataFrame(features_weights)

                chart = (
                    alt.Chart(features_weights, title=f"Features predicting {attr}")
                    .mark_bar()
                    .encode(y="feature", x="weight", color="positive")
                )

                st.altair_chart(chart, use_container_width=True)

        return Visualization(title="🧠 Prediction", score=1, run=visualization)
