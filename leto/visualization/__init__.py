import abc
from leto.query import Query, WhereQuery
from leto.model import Relation
from typing import Callable, List
import pydot
import pandas as pd
import streamlit as st


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
            for r in response:
                st.code(r)

        return Visualization(title="📋 Returned tuples", score=0, run=visualization)


class GraphVisualizer(Visualizer):
    pass


class MapVisualizer(Visualizer):
    def visualize(self, query: Query, response: List[Relation]) -> Visualization:
        if not isinstance(query, WhereQuery):
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
            st.write(df)
            st.map(df)

        return Visualization(title="🗺️ Map", score=len(df), run=visualization)

class SwitchVisualizer(Visualizer):
    def visualize(self, query: Query, response: Iterable[Relation]): 
        switch={HowManyQuery:self.visualize_HowMany}
        try:
            return switch[type(query)](query, response)
        except KeyError:
            for r in response:
                st.code(r)
        except Exception as e:
            #TODO: better handle resolve error
            raise e
        

    def visualize_HowMany(self, query:HowManyQuery,response: Iterable[Relation]): 
        entities = query.entities
        terms = query.terms
        interest_attributes = []
        #switch_paint={
        #            np.int64:self.bars,
        #            np.float64:self.bars,
        #            np.object:self.pie
        #            }
    
        for R in response:
            if R.label=='is_a' and R.entity_to.name in [x.name for x in entities]:
                for att in R.entity_from.__dict__.keys():
                    if att in terms: 
                        interest_attributes.append(att) 
        
        data = {'name':[R.entity_from.name for R in response]}
        for att in interest_attributes: 
            data[att]=[R.entity_from.get(att) for R in response]
        df=pd.DataFrame(data)
        df.set_index('name',inplace=True)
        for col in df.columns:
            try:
                df[col]=pd.to_numeric(df[col])
            except Exception:
                pass
            st.text(df[col].dtype)
            #switch_paint[df[col].dtype](df[col])
            st.plotly_chart(df[col].plot.hist())
        
        st.dataframe(df)
        st.dataframe(df.describe())
    
    def bars(self, data:pd.Series):
        st.plotly_chart(data.plot.hist())
    
    def pie(self, data:pd.Series):
        st.plotly_chart(data.plot.pie())
        
