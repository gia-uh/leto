import os
from typing import Iterable, Tuple
from leto.model import Entity, Relation
from leto.query import (
    Query,
    QueryResolver,
    WhatQuery,
    WhereQuery,
    WhichQuery,
    WhoQuery,
    HowManyQuery,
    PredictQuery,
    MatchQuery,
)
from leto.storage import Storage

from neo4j import GraphDatabase, basic_auth

import streamlit as st


username = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "12345678")
neo4jVersion = os.getenv("NEO4J_VERSION", "")
port = os.getenv("PORT", 7687)
url = os.getenv("NEO4J_URI", f"bolt://neo4j:{port}")


class GraphStorage(Storage):
    """
    GraphStorage:
        class for handling operations concerning neo4j database. It wraps main functions as
        creating nodes / relationships between them. With each wrap, Graph storage accepts
        property dicts or even well formed where clauses, giving some flexibility degree.
        As a more advanced option, the class exposes a method to run directly queries onto
        the database server.

    Usage:
    ```python
    app = GraphStorage()
    raul = Entity("Raul Lala", "Person")
    lorenzo = Entity("Lorenzo Cardaño", "Person", work="Raise dragons")
    julio = Entity("Julio Cardaño", "Person", hobby="Fight dragons")

    closet = Entity("Closet", "Thing")
    drawer = Entity("Drawer", "Thing")

    raul_friendswith_lorenzo = Relation("friendswith", raul, lorenzo, is_mutual = True)
    raul_friendswith_julio = Relation("friendswith", raul, julio, is_mutual = True)
    lorenzo_rivalswith_julio = Relation("rivalswith", lorenzo, julio, is_mutual = True)
    lorenzo_have_closet = Relation("have", lorenzo, closet)
    raul_uses_closet = Relation("use", raul, closet)
    closet_have_drawer = Relation("have", closet, drawer, amount="many")

    app.store(raul_friendswith_lorenzo)
    app.store(raul_friendswith_julio)
    app.store(lorenzo_rivalswith_julio)
    app.store(lorenzo_have_closet)
    app.store(raul_uses_closet)
    app.store(closet_have_drawer)
    ```
    """

    def __init__(self):
        self.driver = GraphDatabase.driver(url, auth=basic_auth(username, password))

    def close(self):
        self.driver.close()

    def _get_size(self, tx):
        for record in tx.run("MATCH (n1)-[r]->(n2) RETURN count(r)"):
            return record.values()[0]

    @property
    def size(self):
        with self.driver.session() as session:
            return session.read_transaction(self._get_size)

    def store(self, relation: Relation):
        self.create_entity(relation.entity_from)
        self.create_entity(relation.entity_to)
        self.create_relationship(relation)

    def create_entity(self, entity: Entity):
        with self.driver.session() as session:
            attrs = entity.attrs.copy()
            result = session.read_transaction(
                self._find_node_by, entity.type, name=entity.name
            )

            if len(result) > 0:
                return result[0]

            result = session.write_transaction(
                self._create_node, type=entity.type, name=entity.name, **attrs
            )
            return result[0]

    def create_relationship(self, relation: Relation):
        with self.driver.session() as session:
            # Write transactions allow the driver to handle retries and transient errors
            result = session.write_transaction(
                self._create_relationship,
                relation.label,
                relation.entity_from.type,
                {"name": relation.entity_from.name},
                relation.entity_to.type,
                {"name": relation.entity_to.name},
                **relation.attrs,
            )

    def run_read_query(self, query: str, data_reader):
        with self.driver.session() as session:
            results = session.read_transaction(
                self._run_query, query=query, data_reader=data_reader
            )
            if len(results) == 0:
                print("No data was found")
            return results

    def run_write_query(self, query: str):
        with self.driver.session() as session:
            return session.write_transaction(self._run_query, query=query)

    @staticmethod
    def _run_query(tx, query: str, data_reader):
        result = tx.run(query)
        results = []
        for record in result:
            results.append(data_reader(record))
        return results

    @staticmethod
    def _find_node_by(tx, node_type: str, where: str = None, **args):
        if not where:
            where = " AND ".join(
                [f'node.{arg[0]} = "{arg[1]}"' for arg in args.items()]
            )

        query = f"MATCH (node:{node_type}) " f"WHERE {where} " f"RETURN DISTINCT node"

        result = tx.run(query)
        return [record["node"]._properties for record in result]

    @staticmethod
    def _create_node(tx, type: str, **args):
        properties = ", ".join([f"{arg[0]}:{repr(arg[1])}" for arg in args.items()])

        query = f"CREATE (node:{type} {{{properties}}}) " f"RETURN node"

        result = tx.run(query)
        return [record["node"]._properties for record in result]

    @staticmethod
    def _create_relationship(
        tx,
        relationship_name: str,
        nodeType1: str,
        properties1: dict,
        node_type2: str,
        properties2: dict,
        **args,
    ):
        where1 = " AND ".join(
            [f'p1.{arg[0]} = "{arg[1]}"' for arg in properties1.items()]
        )
        where2 = " AND ".join(
            [f'p2.{arg[0]} = "{arg[1]}"' for arg in properties2.items()]
        )
        properties = ", ".join([f'{arg[0]}:"{arg[1]}"' for arg in args.items()])

        match_query = (
            f"MATCH (p1:{nodeType1})-[:{relationship_name}]->(p2:{node_type2}) WHERE {where1} AND {where2}"
            f"RETURN DISTINCT p2"
        )
        match_result = tx.run(match_query)

        qsep = "AND" if where2 else ""
        query = (
            f"MATCH (p1:{nodeType1}), (p2:{node_type2}) WHERE {where1} {qsep} {where2}"
            f"AND NOT (p1)-[:{relationship_name}]->(p2)"
            f"CREATE (p1) -[:{relationship_name} {{{properties}}}]-> (p2)"
        )

        result = tx.run(query)
        p1 = [record["p1"]._properties for record in result]
        p2 = [record["p1"]._properties for record in result]
        return result

    def get_query_resolver(self) -> QueryResolver:
        return GraphQueryResolver(self)


class GraphQueryResolver(QueryResolver):
    """
    Usage:
    ```python
    app = GraphStorage()
    resolver = GraphQueryResolver(app)
    pprint(resolver.resolve(MatchQuery(["Closet", "Drawer", "Julio Cardaño"], match_relations=False)))
    pprint(resolver.resolve(WhoQuery("Lorenzo Cardaño", "friendswith")))
    pprint(resolver.resolve(WhatQuery("Closet", "have")))
    ```
    """

    def __init__(self, storage: GraphStorage) -> None:
        self.storage = storage

    def _make_triplet_reader(
        self, entity_from_tag: str, relation_tag: str, entity_to_tag: str
    ):
        def read_triplet_result(record):
            entity_from = record[entity_from_tag]
            entity_to = record[entity_to_tag]
            relationship = record[relation_tag]
            return (entity_from, relationship, entity_to)

        return read_triplet_result

    def _make_single_reader(self, entity_tag):
        def read_single_result(record):
            return record[entity_tag]

        return read_single_result

    def _build_entity_from_node(self, node) -> Entity:
        entity_properties = node._properties.copy()
        entity_name = entity_properties.pop("name")
        return Entity(entity_name, list(node.labels)[0], **entity_properties)

    def _build_relation_from_triplet(self, triplet) -> Relation:
        """
        builds a relation from a processed record using a function generated by `_make_triplet_reader`

        triplet argument is assumed to have the following structure:
        `(node [entity from], relation, node [entity to])`
        """
        entity_from = self._build_entity_from_node(triplet[0])
        entity_to = self._build_entity_from_node(triplet[2])
        return Relation(
            triplet[1].type, entity_from, entity_to, **triplet[1]._properties
        )

    def _resolve_triplet_query(
        self, entity_name: str, relation: str = None, entity_type=None
    ):
        cypher_query = (
            f'MATCH (e{"" if entity_type is None else f":{entity_type}"})-[r{"" if relation is None else f":{relation}"}]->(e2)'
            f'WHERE e.name = "{entity_name}"'
            f"RETURN e, r, e2"
        )
        triplets = self.storage.run_read_query(
            cypher_query, data_reader=self._make_triplet_reader("e", "r", "e2")
        )
        results = []
        for triplet in triplets:
            results.append(self._build_relation_from_triplet(triplet))
        return results

    def _resolve_single_query(self, entity_name: str, entity_type=None):
        cypher_query = f'MATCH (e{"" if entity_type is None else f":{entity_type}"}) WHERE e.name = "{entity_name}" RETURN e'
        singles = self.storage.run_read_query(
            cypher_query, data_reader=self._make_single_reader("e")
        )
        results = []
        for single in singles:
            results.append(self._build_entity_from_node(single))
        return results

    def _resolve_query(self, query: Query) -> Iterable[Relation]:
        switch = {
            WhoQuery: self.resolve_who,
            WhatQuery: self.resolve_what,
            WhichQuery: self.resolve_which,
            MatchQuery: self.resolve_match,
            WhereQuery: self.resolve_where,
            HowManyQuery: self.resolve_howmany,
            PredictQuery: self.resolve_predict,
        }

        try:
            return switch[type(query)](query)
        except Exception as e:
            # TODO: better handle resolve error
            raise e

    def resolve_where(self, query: WhereQuery) -> Iterable[Relation]:
        entities = list(query.entities)

        # Expand entities to contain instances of is_a
        for entity in query.entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e2.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)

                if relation.label == "is_a":
                    yield relation
                    entities.append(relation.entity_from)

        # Solving where e1 is related with e2
        for entity in entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e1.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)

                if relation.entity_to.type != "Place":
                    continue

                yield relation

    def resolve_who(self, query: WhoQuery) -> Iterable[Relation]:
        entities = list(query.entities)

        # Expand entities to contain instances of is_a
        for entity in query.entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e2.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)

                if relation.label == "is_a":
                    yield relation
                    entities.append(relation.entity_from)

        # Solving where e1 is the who
        for entity in entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e2.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)

                if relation.label in query.terms:
                    yield relation

    def resolve_which(self, query: WhichQuery) -> Iterable[Relation]:
        entities = list(query.entities)

        # Expand entities to contain instances of is_a
        for entity in query.entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e2.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)

                if relation.label == "is_a":
                    yield relation
                    entities.append(relation.entity_from)

        # Solving where e1 is the who
        for entity in entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e1.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)

                if relation.label in query.terms:
                    yield relation

    def resolve_what(self, query: WhatQuery) -> Iterable[Relation]:
        # Solving when e1 is_a what they are asking
        for entity in query.entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e2.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)

                if relation.label == "is_a":
                    yield relation

        # Solving for e1
        for entity in query.entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e1.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)
                yield relation

    def resolve_match(self, query: MatchQuery) -> Iterable[Relation]:
        entities = list(query.entities)

        # Expand entities to contain instances of is_a
        for entity in query.entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e2.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)

                if relation.label == "is_a":
                    yield relation
                    entities.append(relation.entity_from)

        for entity in entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e1.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)
                yield relation

        for entity in entities:
            e1, r, e2 = Q.vars("e1 r e2")

            for t in (
                Q(self.storage)
                .match(e1[r] >> e2)
                .where({e2.name: entity.name})
                .get(e1, r, e2)
            ):
                relation = self._build_relation_from_triplet(t)
                yield relation

    def resolve_howmany(self, query: HowManyQuery) -> Iterable[Relation]:
        for entity in query.entities:

            e0, r0, e1 = Q.vars("e0 r0 e1")

            q = Q(self.storage)
            q._query_body = [
                f"MATCH (e0)-[r0:is_a*1..]->(e1) WHERE e1.name = {repr(entity.name)}"
            ]

            for t in q.get(e0, r0, e1):
                relation = self._build_relation_from_triplet((t[0], t[1][0], t[2]))

                if query.field in relation.attrs:
                    yield relation

    def resolve_predict(self, query: PredictQuery) -> Iterable[Relation]:
        for entity in query.entities:
            e0, r0, e1 = Q.vars("e0 r0 e1")

            q = Q(self.storage)
            q._query_body = [
                f"MATCH (e0)-[r0:is_a*1..]->(e1) WHERE e1.name = {repr(entity.name)}"
            ]

            for t in q.get(e0, r0, e1):
                relation = self._build_relation_from_triplet((t[0], t[1][0], t[2]))
                yield relation


class Q:
    def __init__(self, storage: GraphStorage) -> None:
        self._storage = storage
        self._query_body = []

    def match(self, path) -> "Q":
        self._query_body.append(Q.Match(path))
        return self

    def where(self, kwargs: dict) -> "Q":
        self._query_body.append(Q.Where(kwargs))
        return self

    def get(self, *items) -> "Iterable[Relation]":
        self._query_body.append(Q.Return(*items))
        q = str(self)

        def reader(record):
            return [record[str(item)] for item in items]

        return self._storage.run_read_query(q, reader)

    def __str__(self) -> str:
        return "\n".join(str(q) for q in self._query_body)

    @staticmethod
    def vars(names: str) -> "Tuple[Q.Var]":
        for name in names.split():
            yield Q.Var(name)

    class Var:
        def __init__(self, name: str) -> None:
            self._name = name

        def __getitem__(self, other) -> "Q.HalfPath":
            return Q.HalfPath(self, other)

        def __str__(self) -> str:
            return self._name

        def __getattr__(self, attr):
            return f"{self._name}.{attr}"

    class HalfPath:
        def __init__(self, entity, relation) -> None:
            self.entity = entity
            self.relation = relation

        def __rshift__(self, other) -> "Q.FullPath":
            return Q.FullPath(self.entity, self.relation, other)

    class FullPath:
        def __init__(self, e1, r, e2) -> None:
            self.e1 = e1
            self.r = r
            self.e2 = e2

        def __str__(self):
            return f"({self.e1}) - [{self.r}] -> ({self.e2})"

    class Match:
        def __init__(self, path) -> None:
            self.path = path

        def __str__(self) -> str:
            return f"MATCH {self.path}"

    class Where:
        def __init__(self, kwargs) -> None:
            self.kwargs = kwargs

        def __str__(self) -> str:
            return "WHERE " + " AND ".join(
                f"{key} = {repr(value)}" for key, value in self.kwargs.items()
            )

    class Return:
        def __init__(self, *items) -> None:
            self.items = items

        def __str__(self) -> str:
            return "RETURN " + ", ".join([str(item) for item in self.items])
