import os
from typing import Iterable, Union

from numpy import rate
from leto.model import Entity, Relation
from leto.query import (
    Query,
    QueryResolver,
)
from leto.storage import Storage

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
        self.entities = set(self.get_entity_names())
        self.entity_types = set(self.get_entity_types())
        self.relationships = set(self.get_relationship_types())
        self.attributes = set(self.get_attribute_types())

    def close(self):
        self.driver.close()

    def get_relationship_types(self):
        with self.driver.session() as session:
            results = []

            for record in session.run("CALL db.relationshipTypes()"):
                results.append(record["relationshipType"])

            return results

    def get_entity_types(self):
        with self.driver.session() as session:
            results = []

            for record in session.run("CALL db.labels()"):
                results.append(record["label"])

            return results

    def get_attribute_types(self):
        with self.driver.session() as session:
            results = []

            for record in session.run("CALL db.schema.nodeTypeProperties()"):
                results.append(record["propertyName"])

            return results

    def get_entity_names(self):
        with self.driver.session() as session:
            results = []

            for record in session.run("MATCH (e1) RETURN e1.name"):
                results.append(record["e1.name"])

            return results

    @property
    def size(self):
        with self.driver.session() as session:
            for record in session.run("MATCH (n1)-[r]->(n2) RETURN count(r)"):
                return record.values()[0]

    def store(self, entity_or_relation: Union[Entity, Relation]):
        if isinstance(entity_or_relation, Entity):
            self.create_entity(entity_or_relation)
        elif isinstance(entity_or_relation, Relation):
            self.create_relationship(entity_or_relation)
        else:
            raise ValueError(f"{entity_or_relation} is not Entity or Relation")

    def create_entity(self, entity: Entity):
        self.entities.add(entity.name)
        self.entity_types.add(entity.type)

        for attr in entity.attrs:
            self.attributes.add(attr)

        attribute_str = ",".join(
            f"n.{key} = {repr(value)}" for key, value in entity.attrs.items()
        )

        query = f"MERGE (n:{entity.type} {{ name: {repr(entity.name)} }})"

        if attribute_str:
            query += f"""
            ON CREATE SET {attribute_str}
            ON MATCH SET {attribute_str}
            """

        with self.driver.session() as session:
            session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{entity.type}) ON (n.name)")
            session.run(query)

    def create_relationship(self, relation: Relation):
        self.relationships.add(relation.label)

        attributes_str = ",".join(
            f"{key}: {repr(value)}" for key, value in relation.attrs.items()
        )

        with self.driver.session() as session:
            session.run(
            f"""
            MATCH (n1:{relation.entity_from.type} {{ name:{repr(relation.entity_from.name)} }}),
                  (n2:{relation.entity_to.type} {{ name:{repr(relation.entity_to.name)} }})
            CREATE (n1)-[r:{relation.label} {{ {attributes_str} }}]->(n2)
            """
            )

    def get_query_resolver(self) -> QueryResolver:
        return GraphQueryResolver(self)


class GraphQueryResolver(QueryResolver):
    """
    A query resolver attached to a Neo4j backend.
    """

    def __init__(self, storage: GraphStorage) -> None:
        self.storage = storage

    def _resolve(self, query: Query, breadth: int, max_entities: int) -> Iterable[Relation]:
        if not query.entities:
            return

        where_entity = " OR ".join(f'n1.name = "{e}"' for e in query.entities)

        cypher = f"""
        MATCH p=(n1)-[*..{breadth}]-(n2)
        WHERE ({where_entity}) AND none(r IN relationships(p) WHERE type(r) = "has_source")
        RETURN nodes(p) as nodes, relationships(p) as edges
        LIMIT {max_entities}
        """

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
