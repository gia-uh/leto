from ..loaders import Loader
import pandas as pd
import numpy as np
from fuzzywuzzy import process
from io import BytesIO
from leto.model import Entity, Relation


class CSVLoader(Loader):
    """
    Load structured data in table format from a CSV file.
    """
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
            yield Relation(
                entity_from=Entity(str(self.index), type="THING"),
                label="same_as",
                entity_to=Entity(str(col)),
                type="THING",
            )

        properties = [x for x in self.col if (x not in self.cand + [self.index])]
        for col in properties:
            yield Relation(
                entity_from=Entity(str(self.index), type="THING"),
                label="has_property",
                entity_to=Entity(str(col), type="PROP"),
            )

        for col in self.col:
            yield Relation(
                entity_from=Entity(
                    str(col), type="PROP" if col in properties else "THING"
                ),
                label="is_a",
                entity_to=Entity(str(self.df[col].dtype), type="TYPE"),
            )

        for i, row in self.df.iterrows():
            prop = row[properties].to_dict()
            prop["alt_id"] = row[self.cand].to_dict()
            yield Relation(
                entity_from=Entity(name=str(row.at[self.index]), type="THING", **prop),
                label="is_a",
                entity_to=Entity(str(self.index), type="THING"),
            )
