import uuid
from collections.abc import Mapping
from io import BytesIO
from typing import List
from numpy import isin

import pandas as pd
from leto.loaders.unstructured import Language
from leto.model import Entity, Relation, Source
from leto.utils import get_model

from ..loaders import Loader


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

    def __init__(
        self,
        paths: List[BytesIO],
        main_entity: str = "",
        language: Language = Language.en,
    ) -> None:
        self.paths = paths
        self.main_entity = main_entity
        self.language = language

    @classmethod
    def title(cls):
        return "From CSV file"

    def _get_source(self, name, **metadata) -> Source:
        return Source(name, method="csv", loader="CSVLoader", **metadata)

    def _strip_column_name(self, column_name: str):
        if ":" in column_name:
            return column_name.split(":")[0]

        return column_name

    def _load(self):
        for path in self.paths:
            df = pd.read_csv(path)

            column_types = {
                column: self._infer_type(column, df[column]) for column in df.columns
            }

            entity_columns = []
            main_entity_id = None

            for c, t in column_types.items():
                if t == "index" and main_entity_id is None:
                    main_entity_id = c
                    continue

                if t in ["index", "relation"]:
                    entity_columns.append(c)

            names_to_entities = {}
            attribute_columns = [
                c for c, t in column_types.items() if c not in entity_columns
            ]

            # Create all other entities
            for column in entity_columns:
                for i, tupl in df.iterrows():
                    name = tupl[column]

                    if not isinstance(name, str):
                        continue

                    name = name.strip()
                    type = self._strip_column_name(column).title()

                    e = Entity(name=name, type=type)
                    names_to_entities[name] = e
                    yield e

            text_columns = [c for c, t in column_types.items() if t == "text"]
            nlp = get_model(self.language) if text_columns else None

            # Create the main entity
            for i, tupl in df.iterrows():
                attributes = {
                    self._strip_column_name(c): getattr(tupl, c)
                    for c in attribute_columns
                    if getattr(tupl, c)
                }

                name = (
                    tupl[main_entity_id].strip()
                    if main_entity_id is not None
                    else str(uuid.uuid4())
                )
                type = (
                    main_entity_id.title()
                    if main_entity_id
                    else self.main_entity or "Event"
                )

                main = Entity(name=name, type=type, **attributes)
                yield main

                # Create all relations
                for column in entity_columns:
                    entity_to = names_to_entities.get(tupl[column], None)

                    if entity_to is None:
                        continue

                    label = self._strip_column_name(column).lower()

                    yield Relation(label=label, entity_from=main, entity_to=entity_to)

                # Create all entities mentioned in the text fields
                for c in text_columns:
                    text = tupl[c]
                    entities = [
                        Entity(e.text.strip(), e.label_) for e in nlp(text).ents
                    ]

                    for e in entities:
                        if e.type == "LOC":
                            e.type = "Location"
                        elif e.type == "PER":
                            e.type = "Person"
                        elif e.type == "ORG":
                            e.type = "Organization"
                        else:
                            continue

                        yield Relation(
                            entity_from=main, entity_to=e, label="mention", field=c
                        )

    def _infer_type(self, name: str, df: pd.Series):
        # Try a bunch of heuristics

        if name.endswith(":text"):
            return "text"

        if name.endswith(":attr"):
            return "attribute"

        if name.endswith(":rel"):
            return "relation"

        if name == "date" or name.endswith(":date"):
            return "date"

        if df.dtype in ["float64", "float32", "int"]:
            return "number"

        if df.dtype == "object" and df.is_unique:
            return "index"

        if df.dtype == "object" and df.str.len().max() > 30:
            return "text"

        if df.dtype == "object":
            return "relation"

        return "attribute"
