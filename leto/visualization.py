import abc
import streamlit as st


class Visualizer(abc.ABC):
    @abc.abstractmethod
    def visualize(self, query, response):
        pass


class DummyVisualizer(Visualizer):
    def visualize(self, query, response):
        st.write(f"**Query**: {query}")
        st.table(dict(entity_1=e1, relation=r, entity_2=e2) for e1, r, e2 in response)
