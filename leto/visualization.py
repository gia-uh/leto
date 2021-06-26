import abc
from leto.query import Query
from leto.model import Relation
from typing import Iterable
import streamlit as st
from leto.query import HowManyQuery
import pandas as pd
import numpy as np
import plotly
pd.options.plotting.backend = 'plotly'

class Visualizer(abc.ABC):
    @abc.abstractmethod
    def visualize(self, query, response):
        pass


class DummyVisualizer(Visualizer):
    def visualize(self, query: Query, response: Iterable[Relation]):
        for r in response:
            st.code(r)

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
        
