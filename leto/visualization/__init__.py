import abc
import json
import math
from typing import Callable, List

import collections

import altair as alt
import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
from pyvis.network import Network
import networkx as nx
import json

from leto.model import Relation
from leto.query import Query
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


def shorten(string, length, dots="..."):
    if len(string) > length:
        return string[: length - len(dots)] + dots

    return string


class GraphVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        def visualization():
            graph = nx.DiGraph()
            entity_types = {}

            if len(response) > 100:
                return Visualization.Empty()

            entities = set(query.entities)
            main_entities = set()

            skip_types = frozenset(["Source", "Event"])

            for tuple in response:
                for e in [tuple.entity_from, tuple.entity_to]:
                    if e.type not in entity_types:
                        entity_types[e.type] = len(entity_types)

                    generated = e.get("_generated") == "true"
                    label = e.type if generated else e.name
                    full_label = e.type if generated else f"{e.name} : {e.type}"

                    tooltip = [f"<b>{full_label}</b>"] + [
                        f"{attr} = {shorten(str(value), 50)}"
                        for attr, value in e.attrs.items()
                        if not attr.startswith("_")
                    ]

                    graph.add_node(
                        e.id,
                        shape="circle",
                        label=shorten(label, 8),
                        title="<br/>".join(tooltip),
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
            nt.set_options(
                json.dumps({"physics": {"barnesHut": {"springLength": 150}}})
            )

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
                if not (
                    query.mentions(entity=e.name)
                    or query.mentions(relation=tuple.label)
                ):
                    continue

                if e.name in query.entities and e.name in self.visualizables:
                    countries.append(e)

                if "lat" in e.attrs and "lon" in e.attrs:
                    locations.append(e)

        if not countries + locations:
            return Visualization.Empty()

        regions = set(d.name for d in countries)

        def visualization():
            countries = [
                dict(name=feature["properties"]["name"], label="Country", **feature)
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
            icons = pd.DataFrame(
                [dict(name=e.name, label=e.type, **e.attrs) for e in locations]
            )
            icons["icon_data"] = [icon_data] * len(icons)

            iconlayer = pdk.Layer(
                "IconLayer",
                icons,
                get_icon="icon_data",
                get_size=40,
                get_position=["lon", "lat"],
                pickable=True,
            )

            layers = []
            view_state = None

            if countries:
                layers.append(geojson)
                lonlat = []

                for f in countries:
                    for polygon in f["geometry"]["coordinates"]:
                        if isinstance(polygon[0], float):
                            lonlat.append(dict(lon=polygon[0], lat=polygon[1]))

                        else:
                            for point in polygon:
                                lonlat.append(dict(lon=point[0], lat=point[1]))

                view_state = pdk.data_utils.compute_view(pd.DataFrame(lonlat), 1.0)

            if locations:
                layers.append(iconlayer)
                view_state = pdk.data_utils.compute_view(icons[["lon", "lat"]], 1.0)

            map = pdk.Deck(
                layers=layers,
                initial_view_state=view_state,
                tooltip={"text": "{name}:{label}"},
            )

            st.pydeck_chart(map)

        return Visualization(
            title="🗺️ Map",
            score=len(countries + locations) / len(response),
            run=visualization,
        )


class CountEntitiesVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]):
        entities = collections.defaultdict(list)
        relations = []

        for R in response:
            for e in [R.entity_from, R.entity_to]:
                if e.get("_generated"):
                    continue

                entities[e.type].append(e.name)

            relations.append(R.label)

        if not entities and not relations:
            return Visualization.Empty()

        def visualization():
            for type, instances in entities.items():
                df = pd.DataFrame([dict(name=e, type=type) for e in instances])
                names = set(instances)

                if 1 < len(names) < 20:
                    st.write(f"#### {type}")
                    st.plotly_chart(px.pie(df, "name"))

        return Visualization(
            "🕸️ Entities and Relations",
            1,
            run=visualization,
        )


class SchemaVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]):
        data_entities = []
        data_relations = []
        entities = set()

        for R in response:
            data_relations.append(dict(label=R.label, attribute="label", count=1))

            for key, value in R.attrs.items():
                data_relations.append(dict(label=R.label, attribute=key, count=1))

            for e in [R.entity_from, R.entity_to]:
                entities.add(e)

        for e in entities:
            data_entities.append(dict(type=e.type, attribute="name", count=1))

            for key, value in e.attrs.items():
                data_entities.append(dict(type=e.type, attribute=key, count=1))

        if not data_entities:
            return Visualization.Empty()

        data_entities = pd.DataFrame(data_entities)
        data_entities = data_entities.groupby(["type", "attribute"]).sum().reset_index()

        data_relations = pd.DataFrame(data_relations)
        data_relations = (
            data_relations.groupby(["label", "attribute"]).sum().reset_index()
        )

        def visualization():
            st.write("#### Entities")
            st.table(data_entities)

            st.write("#### Relations")
            st.table(data_relations)

        return Visualization(
            "⚙️ Schema",
            score=(len(data_entities) + len(data_relations)) / len(response),
            run=visualization,
        )


class AttributeVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]):
        data = []

        if len(query.attributes) < 1 or len(query.labels) != 1:
            return Visualization.Empty()

        attributes = query.attributes[0]
        label = query.labels[0]

        for R in response:
            entity = None

            if R.entity_from.type == label:
                entity = R.entity_from
            if R.entity_to.type == label:
                entity = R.entity_to

            values = {}
            for attribute in query.attributes:
                values[attribute] = R.entity_from.get(attribute) or R.entity_to.get(
                    attribute
                )

            if not values or entity is None:
                continue

            row = {label: entity.name}
            row.update(**values)

            data.append(row)

        if not data:
            return Visualization.Empty()

        df = pd.DataFrame(data)
        print(df, flush=True)

        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass

        def visualization():
            for attr in query.attributes:
                chart = alt.Chart(df).mark_point().encode(y=label, x=attr)

                st.altair_chart(chart)

        return Visualization(
            title="📊 Attribute values", score=len(df), run=visualization
        )


class PredictVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]):
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

        attributes = set(query.attributes) - set(["date"])

        for r in response:
            e1 = r.entity_from
            e2 = r.entity_to

            if e2.type not in query.labels:
                continue

            if not "date" in e1.attrs:
                continue

            for attr in attributes:
                value = e1.attrs.get(attr)

                if not value:
                    continue

                entity_field = r.label
                attribute_field = attr
                data.append({r.label: e2.name, "date": e1.attrs["date"], attr: value})

        if not data:
            return Visualization.Empty()

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        print(df, flush=True)

        def visualization():
            chart = alt.Chart(df)
            chart = chart.mark_line()
            chart = chart.encode(
                x="date:T",
                y=alt.Y(f"sum({attribute_field}):Q", title=attribute_field),
                color=f"{entity_field}",
                tooltip=[
                    alt.Tooltip(entity_field),
                    alt.Tooltip(attribute_field),
                    alt.Tooltip("date"),
                ],
            )

            st.altair_chart(chart, use_container_width=True)

        return Visualization(title="📈 Timeseries", score=2, run=visualization)


def get_visualizers():
    return [
        DummyVisualizer(),
        GraphVisualizer(),
        MapVisualizer(),
        SchemaVisualizer(),
        CountEntitiesVisualizer(),
        AttributeVisualizer(),
        TimeseriesVisualizer(),
        # PredictVisualizer(),
    ]
