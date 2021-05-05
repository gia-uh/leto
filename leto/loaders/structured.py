from ..loaders import Loader
import pandas as pd
import numpy as np
from fuzzywuzzy import process
from io import BytesIO


class CsvLoader(Loader):
    def __init__(self, path: BytesIO) -> None:
        self.path = path
        

    def infer_index(self):
        """infer an index column using uniqueness and text similarity to 'ID' and 'name'"""
        cand = [
            x
            for x in self.col
            if self.df[x].is_unique and str(self.df[x].dtype) == "object"
        ]
        similarity_name = process.extractOne("name", cand)
        similarity_id = process.extractOne("id", cand)
        self.index = max([similarity_name, similarity_id], key=lambda x: x[1])[0]
        cand.remove(self.index)
        self.cand = cand

    def load(self):
        """
        yields index column,'same_as',all unique columns
        yields index column,'has_property',all non unique columns
        yields all columns,'is_a',column type
        yields entity with properties,'is_a', index column
        """

        self.df = pd.read_csv(self.path)
        self.col = self.df.columns
        self.index = None
        self.infer_index()
        # self.corr=self.df.select_dtypes(include=np.number).corr()

        for col in self.cand:
            yield ({"id": self.index}, {"id": "same_as"}, {"id": col})

        properties = [x for x in self.col if (x not in self.cand + [self.index])]
        for col in properties:
            yield ({"id": self.index}, {"id": "has_property"}, {"id": col})

        for col in self.col:
            yield ({"id": col}, {"id": "is_a"}, {"id": str(self.df[col].dtype)})

        for row in self.df.iterrows():
            entity = {"id": row.at[self.index]}
            entity.update(row[properties].to_json())
            entity["alt_id"] = row[self.cand].to_json()
            yield (entity, {"id": "is_a"}, {"id": self.index})
