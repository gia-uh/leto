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


class MultiCSVLoader(Loader):
    """Load entities and relations from one or more CSV files,
    automatically inferring entity names, attributes, and relations.
    """

    def __init__(self, files: List[BytesIO]) -> None:
        self.files = files

    def _get_source(self, name, **metadata) -> Source:
        return Source(name, method="csv", loader="MultiCSVLoader", **metadata)

    @staticmethod
    def infer_index(df):
        """infer an index column using uniqueness and text similarity to 'ID' and 'name'"""
        cand = [
            x for x in df.columns if df[x].is_unique and str(df[x].dtype) == "object"
        ]
        similarity_name = process.extractOne("name", cand)
        similarity_id = process.extractOne("id", cand)
        index = max([similarity_name, similarity_id], key=lambda x: x[1])[0]
        cand.remove(index)
        properties = [x for x in df.columns if (x not in cand + [index])]
        return index, cand, properties

    def _load(self):  # -> Iterable[Relation]:
        dataframes = {
            fp.name.split("/")[-1].split(".")[0]: pd.read_csv(fp) for fp in self.files
        }

        def update_columns():
            column_partition = {}
            columns = {
                (df_name, col): {
                    "is_unique": df[col].is_unique,
                    "col_type": str(df[col].dtype),
                    "values": set(df[col].values),  # .remove(None),
                    "is_index": False,
                    "is_cand": False,
                }
                for df_name, df in dataframes.items()
                for col in df.columns
            }
            for df_name, df in dataframes.items():
                index, cand, properties = self.infer_index(df)
                column_partition[df_name] = {
                    "index": index,
                    "cand": cand,
                    "properties": properties,
                }
                columns[(df_name, index)]["is_index"] = True
                for col in cand:
                    columns[(df_name, col)]["is_cand"] = True
            return columns, column_partition

        columns, column_partition = update_columns()

        for df_name, df in dataframes.items():
            index, cand, properties = self.infer_index(df)
            for col in cand:
                yield Relation(
                    entity_from=Entity(".".join([df_name, str(index)]), type="THING"),
                    label="same_as",
                    entity_to=Entity(".".join([df_name, str(col)]), type="THING"),
                )
            for col in properties:
                yield Relation(
                    entity_from=Entity(".".join([df_name, str(index)]), type="THING"),
                    label="has_property",
                    entity_to=Entity(".".join([df_name, str(col)]), type="PROP"),
                )
            for col in [index] + cand + properties:
                yield Relation(
                    entity_from=Entity(
                        ".".join([df_name, str(col)]),
                        type="PROP" if col in properties else "THING",
                    ),
                    label="is_a",
                    entity_to=Entity(
                        ".".join([df_name, str(df[col].dtype)]), type="TYPE"
                    ),
                )

        dataframes = {
            df_name: df.rename(lambda x: ".".join([df_name, x]), axis="columns")
            for df_name, df in dataframes.items()
        }
        columns = {
            (df_name, ".".join([df_name, col])): prop
            for ((df_name, col), prop) in columns.items()
        }

        foreign_keys = set()

        for i in range(len(dataframes)):

            for ((df_name1, col1), prop1), ((df_name2, col2), prop2) in permutations(
                columns.items(), r=2
            ):
                if (
                    df_name1 != df_name2
                    and (prop2["is_index"] or prop2["is_cand"])
                    and prop1["values"].issubset(prop2["values"])
                ):
                    foreign_keys.add(
                        FrozenDict(
                            **{
                                "key": col1,
                                "from": df_name1,
                                "to": df_name2,
                                "in": col2,
                            }
                        )
                    )
                    yield Relation(
                        entity_from=Entity(
                            ".".join([df_name1, str(col1)]), type="THING"
                        ),
                        label="same_as",
                        entity_to=Entity(".".join([df_name2, str(col2)]), type="THING"),
                    )

                    _df = pd.merge(
                        dataframes[df_name1],
                        dataframes[df_name2],
                        left_on=col1,
                        right_on=col2,
                        how="left",
                        suffixes=["", "_"],
                    )
                    dataframes[df_name1] = _df[[x for x in _df if x[-1] != "_"]]

                columns, column_partition = update_columns()

        entities = {}
        for df_name, df in dataframes.items():
            for i, row in df.iterrows():
                prop = row[
                    [
                        x
                        for x in df.columns
                        if x
                        not in [column_partition[df_name]["index"]]
                        + column_partition[df_name]["cand"]
                    ]
                ].to_dict()
                prop["alt_id"] = row[column_partition[df_name]["cand"]].to_dict()

                entity_from = Entity(
                    name=str(row.at[str(column_partition[df_name]["index"])]),
                    type="THING",
                    **prop
                )
                if not entities.get(df_name):
                    entities[df_name] = []
                entities[df_name].append(entity_from)
                # yield
                yield Relation(
                    entity_from=entity_from,
                    label="is_a",
                    entity_to=Entity(
                        str(".".join([df_name, column_partition[df_name]["index"]])),
                        type="THING",
                    ),
                )
        for k in foreign_keys:
            e_from = entities[k["from"]]
            e_to = entities[k["to"]]
            for e_f, e_t in product(e_from, e_to):
                if e_f.get(k["key"]) in [e_t.name] + list(e_t.get("alt_id").values()):
                    yield Relation(
                        entity_from=e_f,
                        label=k["key"],
                        entity_to=e_t,
                    )

    @classmethod
    def title(cls):
        return "From CSV files"
