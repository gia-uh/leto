import os
import collections
from typing import Iterable, Tuple, Union
from leto.model import Entity, Relation
from leto.query import (
    Query,
    QueryResolver,
)
from leto.storage import Storage
from leto.utils import get_model

from neo4j import GraphDatabase, basic_auth

import streamlit as st


username = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "letoai")
neo4jVersion = os.getenv("NEO4J_VERSION", "")
port = os.getenv("PORT", 7687)
url = os.getenv("NEO4J_URI", f"bolt://neo4j:{port}")


@st.experimental_singleton
def get_neo4j_driver():
    return GraphDatabase.driver(url, auth=basic_auth(username, password))


class EmbeddingMap:
    def __init__(self, storage=None) -> None:
        self.entities = {}
        self.relations = {}
        self.model = get_model()

        if storage is not None:
            with st.spinner("Loading relationships"):
                for relation in storage.get_relationship_types():
                    self.register_relation(relation)

                for entity in storage.get_entity_names():
                    self.register_entity(entity)

    def register_entity(self, entity: str):
        doc = self.model(entity.replace("_", " "))
        self.entities[entity] = doc

    def solve_entity(self, entity):
        best_match = 0
        match = None

        for key, doc in self.entities.items():
            similarity = doc.similarity(entity)

            if similarity > best_match:
                best_match = similarity
                match = key

        return match

    def register_relation(self, relation: str):
        doc = self.model(relation.replace("_", " "))
        self.relations[relation] = doc

    def solve_relation(self, relation):
        best_match = 0
        match = None

        for key, doc in self.relations.items():
            similarity = doc.similarity(relation)

            if similarity > best_match:
                best_match = similarity
                match = key

        return match


@st.experimental_singleton
def embedding_map(_storage=None):
    return EmbeddingMap(_storage)


@st.experimental_singleton
def Neo4jStorage():
    print("Creating new instance of Neo4j GraphStorage")
    return GraphStorage()


class GraphStorage(Storage):
    """
    Class for handling operations concerning neo4j database. It wraps main functions as
    creating nodes / relationships between them. With each wrap, Graph storage accepts
    property dicts or even well formed where clauses, giving some flexibility degree.
    As a more advanced option, the class exposes a method to run directly queries onto
    the database server.
    """

    def __init__(self):
        self.driver = get_neo4j_driver()
        # self.embedding_map = embedding_map(self)

        self.entities = set(self.get_entity_names())
        self.relationships = set(self.get_relationship_types())
        self.attributes = set(self.get_attribute_types())

    def close(self):
        self.driver.close()

    def _get_size(self, tx):
        for record in tx.run("MATCH (n1)-[r]->(n2) RETURN count(r)"):
            return record.values()[0]

    def get_relationship_types(self):
        with self.driver.session() as session:
            return session.read_transaction(self._get_relationship_types)

    def get_attribute_types(self):
        with self.driver.session() as session:
            return session.read_transaction(self._get_attribute_types)

    def get_entity_names(self):
        with self.driver.session() as session:
            return session.read_transaction(self._get_entity_names)

    def _get_entity_names(self, tx):
        results = []

        for record in tx.run("MATCH (e1) RETURN e1.name"):
            results.append(record["e1.name"])

        return results

    def _get_relationship_types(self, tx):
        results = []

        for record in tx.run("CALL db.relationshipTypes()"):
            results.append(record["relationshipType"])

        return results

    def _get_attribute_types(self, tx):
        results = []

        for record in tx.run("CALL db.schema.nodeTypeProperties()"):
            results.append(record["propertyName"])

        return results

    @property
    def size(self):
        with self.driver.session() as session:
            return session.read_transaction(self._get_size)

    def store(self, entity_or_relation: Union[Entity, Relation]):
        if isinstance(entity_or_relation, Entity):
            self.create_entity(entity_or_relation)

        else:
            self.create_entity(entity_or_relation.entity_from)
            self.create_entity(entity_or_relation.entity_to)
            self.create_relationship(entity_or_relation)

    def create_entity(self, entity: Entity):
        self.entities.add(entity.name)

        for attr in entity.attrs:
            self.attributes.add(attr)

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
        self.relationships.add(relation.label)

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


MAX_ENTITIES: int = 1000


class GraphQueryResolver(QueryResolver):
    """
    A query resolver attached to a Neo4j backend.
    """

    def __init__(self, storage: GraphStorage) -> None:
        self.storage = storage

    def _resolve(self, query: Query, breadth: int) -> Iterable[Relation]:
        if not query.entities:
            return

        where_entity = " OR ".join(f'n1.name = "{e}"' for e in query.entities)

        cypher = f"""
        MATCH p=(n1)-[*1..{breadth}]-(n2)
        WHERE {where_entity} AND none(r IN relationships(p) WHERE type(r) = 'has_source')
        RETURN nodes(p) as nodes, relationships(p) as edges
        LIMIT {MAX_ENTITIES}
        """

        print(cypher, flush=True)

        with self.storage.driver.session() as session:
            for edges in session.read_transaction(self._run_query, cypher):
                for e in edges:
                    n1 = e.start_node
                    n2 = e.end_node

                    yield Relation(
                        label=e.type,
                        entity_from=Entity(type=list(n1.labels)[0], **n1._properties),
                        entity_to=Entity(type=list(n2.labels)[0], **n2._properties),
                        **e._properties,
                    )

    @staticmethod
    def _run_query(tx, query):
        result = []

        for record in tx.run(query):
            result.append(record["edges"])

        return result
