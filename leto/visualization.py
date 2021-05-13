import abc
from leto.model import Relation
from typing import Iterable
import streamlit as st


class Visualizer(abc.ABC):
    @abc.abstractmethod
    def visualize(self, query, response):
        pass


class DummyVisualizer(Visualizer):
    def visualize(self, query, response: Iterable[Relation]):
        st.write(f"**Query**: {query}")

        for r in response:
            st.code(r)
