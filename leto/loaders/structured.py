from re import L
from typing import List

import uuid

from ..loaders import Loader
import pandas as pd
from itertools import permutations, product
from io import BytesIO
from leto.model import Entity, Relation, Source
from collections.abc import Mapping


class FrozenDict(Mapping):
    def __init__(self, *args, **kwargs):
        self._d = dict(*args, **kwargs)

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __hash__(self):
        return hash(tuple(sorted(self._d.items())))


class CSVLoader(Loader):
    """
    Load structured data in table format from a CSV file.
    """

    DATE_NAMES = [
        "date",
        "timestamp",
    ]

    def __init__(self, path: BytesIO) -> None:
        self.path = path

    @classmethod
    def title(cls):
        return "From CSV file"

    def _get_source(self, name, **metadata) -> Source:
        return Source(name, method="csv", loader="CSVLoader", **metadata)

    def _load(self):
        df = pd.read_csv(self.path)

        column_types = {
            column: self._infer_type(column, df[column]) for column in df.columns
        }

        entity_columns = []
        main_entity_id = None

        for c,t in column_types.items():
            if t == "index" and main_entity_id is None:
                main_entity_id = c
                continue

            if t in ['index', 'relation']:
                entity_columns.append(c)

        names_to_entities = {}
        attribute_columns = [ c for c,t in column_types.items() if t == "attribute" ]

        # Create all other entities
        for column in entity_columns:
            for tupl in df.itertuples():
                name = getattr(tupl, column)
                type = column.title()

                e = Entity(name=name, type=type)
                names_to_entities[name] = e
                yield e

        # Create the main entity
        for tupl in df.itertuples():
            attributes = { c:getattr(tupl, c) for c in attribute_columns }

            name = getattr(tupl, main_entity_id) if main_entity_id is not None else str(uuid.uuid4())
            type = main_entity_id.title() if main_entity_id is not None else "Fact"

            e = Entity(name=name, type=type, **attributes)
            yield e

            # Create all relations
            for column in entity_columns[1:]:
                entity_from = e
                entity_to = names_to_entities[getattr(tupl, column)]
                label = f"has_{column.lower()}"

                yield Relation(label=label, entity_from=entity_from, entity_to=entity_to)


    def _infer_type(self, name: str, df: pd.Series):
        # Try a bunch of heuristics

        if df.dtype in ["float64", "float32", "int"]:
            return "attribute"

        if df.dtype == "object" and df.is_unique:
            return "index"

        return "relation"
