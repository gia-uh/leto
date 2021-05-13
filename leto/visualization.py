import abc
from leto.query import Query
from leto.model import Relation
from typing import Iterable
import streamlit as st


class Visualizer(abc.ABC):
    @abc.abstractmethod
    def visualize(self, query, response):
        pass


class DummyVisualizer(Visualizer):
    def visualize(self, query: Query, response: Iterable[Relation]):
        for r in response:
            st.code(r)
