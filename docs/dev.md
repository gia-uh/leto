# Welcome to LETO's development guide

This guide explains LETO's architecture and guidelines on how to extend and modify it.

## Overview of LETO's architecture

At the highest level, LETO is an application composed of two services: a frontend written in [streamlit](https://streamlit.io) and a backend stored in [neo4j](https://neo4j.com). All the data is LETO is stored in a single graph database in `neo4j`, using some conventions to determine how it is interpreted.

The frontend is a streamlit app which follows a very simple cycle:

1. Load new data (if necessary)
2. Parse a query
3. Compute a response
4. Visualize the response

This cycle is implemented as a streamlined process in `leto/ui.py` which in turn uses several components to weave everything. Let's look at each step in more detail.

Data enters LETO via a `Loader`, a class that implements a single `_load()` method that returns an iterable of `Entity` and `Relation` instances.
An `Entity` is just a name plus a type, and some opaque attributes. Likewise, a `Relation` has a label, and the two entities it connects. All relations in LETO are directed.

In the main application cycle, the currently selected loader is first instantiated with the corresponding parameters and then executed.
The resulting iterable is given to a `Storage` instance, which can be either `GraphStorage` (the default) or a `DummyStorage` (which is there just for testing purposes).

An `Storage` inheritor needs to supply a `store` method with receives either an entity or a relation.
They also provide a `size()` method for instrospection.

Once stored any newly created data, the main application loop proceeds to parse the current query. A `QueryParser` implementation is used here, which receives a `string` as input and returns an instance of the `Query` class. Different sub-instances of `Query` exist, but they all share the same basic structure: a list of entities, a list of relations, and a list of attributes. Currently implemented query parsers are based on some hard-coded rules on top of a `spacy` tokenization of the query, hence they perform basic entity detection and the rules are based on POS-tags and other syntactic cues.

Once parsed, the query is fed to a `QueryResolver` instance, which is provided by the `Storage` implementation. This will return a sub-graph in the form of a list of tuples, i.e., `Relation` instances. How smart can this resolution be is left to the implementation of the query resolver. In `GraphStorage` the query resolver generates a set of neo4j queries based on some rules that try to find the most similar entities and relations in the graph. There's also currently a simplistic implementation of a similarity engine using `spacy` word embeddings, but this is still in a very crude state.

Finally, the response (as a list of tuples) is fed to a list of `Visualizer` instances. Each visualizer has some specific rules that determine whether it applies, and if so, it produces a callable method to be run for generating the actual visualization. For example, the basic graph visualizer just outputs the graph as a `pydot` image. However, the map visualizer will inspect the tuples to see if it finds something with geographical information, and if so, it generates a map with the corresponding points.

## Adding new data sources

To add a new data source, you need to provide a new implementation of `Loader`. As explained, this implementation must provide a `_load()` method which yields `Entity` or `Relation` instances one at a time.

A `Loader` also provides a `_get_source()` method with outputs an entity of type `Source`. This basically holds metadata that is then linked to all the entities created from the `_load()`.

As an example, here's a dummy implementation that loads data from a manually entered text in the format `entity - relation - entity`:

```python
class ManualLoader(Loader):
    @classmethod
    def title(cls):
        return "Manually enter tuples"

    def __init__(self, tuples: Text) -> None:
        self.tuples = tuples

    def _get_source(self, name, **metadata) -> Source:
        return Source(name, method="manual", loader="ManualLoader", **metadata)

    def _load(self):
        for line in self.tuples.split("\n"):
            e1, r, e2 = line.split("-")
            e1 = e1.strip()
            r = r.strip()
            e2 = e2.strip()

            yield Relation(
                label=r,
                entity_from=Entity(name=e1, type="Thing"),
                entity_to=Entity(name=e2, type="Thing"),
            )
```

Finally, on `leto/loaders/__init__.py`, method `get_loaders()`, add a line importing your loader and include it into the returned list.

## Adding new visualizations

To add a new visualization, you need to provide a new implementation of `Visualizer`. This implementation must provide a method `visualize` which in turn returns a `Visualization` instance. A visualization instance basically has title, a score, and a callable method that is invoked when the visualization must be executed.

This callable will be run in a `streamlit` container context, so you can directly use `st.*` methods to construct any visualization logic you desire.
The recommended approach is to implement whatever preprocessing logic is necessary in the `visualize()` method, and just perform actual visualization logic inside the callback.

In the `visualize()` method, you'll have access to both the original query and the response. The `score` value is used to sort the visualizations, so you should set it to value that is roughly proportional to how informative the visualization is. This score is unbounded.

Here's an example of a very simple visualizer:

```python
class DummyVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        def visualization():
            st.code("\n".join(str(r) for r in response))

        return Visualization(title="📋 Returned tuples", score=0, run=visualization)
```

Finally, on `leto/visualization/__init__.py`, method `get_visualizers()` add your implementation to the returned list.
