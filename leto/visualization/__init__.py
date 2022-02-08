import abc
import json
import math
from typing import Callable, List

import altair as alt
import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
from pyvis.network import Network
import networkx as nx
import json

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
            st.code(
                "\n".join(
                    str(r) for r in response if r.entity_from.type != "TimeseriesEntry"
                )
            )

        return Visualization(title="📋 Returned tuples", score=0, run=visualization)


class GraphVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        def visualization():
            graph = nx.DiGraph()
            entity_types = {}

            entities = set(query.entities)
            main_entities = set()

            skip_types = frozenset(["Source", "Event"])

            for tuple in response:
                for e in [tuple.entity_from, tuple.entity_to]:
                    if e.type not in entity_types:
                        entity_types[e.type] = len(entity_types)

                    label = e.name

                    if len(label) > 8:
                        label = label[:6] + "..."

                    graph.add_node(
                        e.id,
                        shape="circle",
                        label=label,
                        title=f"{e.name}:{e.type}",
                        group=entity_types[e.type],
                    )

                graph.add_edge(
                    tuple.entity_from.id,
                    tuple.entity_to.id,
                    label=tuple.label,
                    arrows="to",
                )

            nt = Network(height="500px", width="100%")
            nt.from_nx(graph)
            nt.toggle_physics(True)
            nt.set_options(json.dumps({"barnessHut": {"springLength": 150}}))

            nt.show("/home/coder/leto/data/graph.html")
            st.components.v1.html(
                open("/home/coder/leto/data/graph.html").read(), height=500
            )

        return Visualization(
            title="🔗 Entity graph",
            score=max(0.1, math.log2(len(response))),
            run=visualization,
        )


class MapVisualizer(Visualizer):
    def __init__(self) -> None:
        with open("/home/coder/leto/data/countries.geo.json") as fp:
            self.data = json.load(fp)["features"]
            self.visualizables = set(
                feature["properties"]["name"] for feature in self.data
            )

    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        countries = []
        locations = []

        for tuple in response:
            for e in [tuple.entity_from, tuple.entity_to]:
                if e.name in self.visualizables:
                    countries.append(e)

                if 'lat' in e.attrs and 'lon' in e.attrs:
                    locations.append(e)

        if not countries + locations:
            return Visualization.Empty()

        regions = set(d.name for d in countries)

        def visualization():
            countries = [
                dict(name=feature['properties']['name'], **feature)
                for feature in self.data
                if feature["properties"]["name"] in regions
            ]

            geojson = pdk.Layer(
                "GeoJsonLayer",
                countries,
                opacity=0.8,
                stroked=False,
                filled=True,
                extruded=True,
                wireframe=True,
                pickable=True,
                get_elevation=1,
                get_fill_color=[255, 255, 255],
                get_line_color=[255, 255, 255],
            )

            icon_data = {
                # Icon from Wikimedia, used the Creative Commons Attribution-Share Alike 3.0
                # Unported, 2.5 Generic, 2.0 Generic and 1.0 Generic licenses
                "url": "https://raw.githubusercontent.com/LETO-ai/resources/main/pin.png",
                "width": 242,
                "height": 242,
                "anchorY": 242,
            }
            icons = pd.DataFrame([dict(name=e.name, **e.attrs) for e in locations])
            icons["icon_data"] = [icon_data] * len(icons)

            iconlayer = pdk.Layer(
                "IconLayer",
                icons,
                get_icon="icon_data",
                get_size=40,
                get_position=['lon', 'lat'],
                pickable=True,
            )

            layers = []
            view_state = None

            if locations:
                layers.append(iconlayer)
                view_state = pdk.data_utils.compute_view(icons[["lon", "lat"]], 0.1)

            if countries:
                layers.append(geojson)

            map = pdk.Deck(layers=layers, initial_view_state=view_state, tooltip={"text": "{name}"})
            st.pydeck_chart(map)

        return Visualization(
            title="🗺️ Map", score=len(countries + locations) / len(response), run=visualization
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


class TimeseriesVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        data = []
        entity_field = None
        attribute_field = None

        for r in response:
            e = r.entity_from

            if e.type != "TimeseriesEntry":
                continue

            if r.entity_to.type == "Source":
                continue

            if not "date" in e.attrs:
                continue

            for attr in query.attributes:
                value = e.attrs.get(attr)

                if not value:
                    continue

                entity_field = r.label
                attribute_field = attr
                data.append(
                    {r.label: r.entity_to.name, "date": e.attrs["date"], attr: value}
                )

        if not data:
            return Visualization.Empty()

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        if query.groupby:
            df = df.groupby(
                [entity_field, pd.Grouper(key="date", freq=query.groupby[0].upper())]
            )
            df = getattr(df, query.aggregate)().reset_index()

        def visualization():
            chart = alt.Chart(df)

            if query.groupby:
                chart = chart.mark_bar()
            else:
                chart = chart.mark_line()

            chart = chart.encode(
                x="date:T",
                y=f"{attribute_field}:Q",
                color=f"{entity_field}",
            )

            st.altair_chart(chart, use_container_width=True)

        return Visualization(title="📈 Timeseries", score=2, run=visualization)


def get_visualizers():
    return [
        DummyVisualizer(),
        GraphVisualizer(),
        MapVisualizer(),
        CountVisualizer(),
        PredictVisualizer(),
        TimeseriesVisualizer(),
    ]
