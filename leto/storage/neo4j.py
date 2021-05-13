import os
from neo4j import GraphDatabase, basic_auth, Session
from neo4j.exceptions import ServiceUnavailable


username = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "12345678")
neo4jVersion = os.getenv("NEO4J_VERSION", "")
database = os.getenv("NEO4J_DATABASE", "neo4j")
port = os.getenv("PORT", 7687)
url = os.getenv("NEO4J_URI", f"bolt://neo4j:{port}")


class GraphStorage:
    """
    GraphStorage:
        class for handling operations concerning neo4j database. It wraps main functions as
        creating nodes / relationships between them. With each wrap, Graph storage accepts
        property dicts or even well formed where clauses, giving some flexibility degree.
        As a more advanced option, the class exposes a method to run directly queries onto
        the database server.
    """

    def __init__(self, uri = url, user = username, password = password):
        self.driver = GraphDatabase.driver(uri, auth = basic_auth(user, password))

    def close(self):
        self.driver.close()

    def _get_size(self, tx):
        for record in tx.run("MATCH (n1)-[r]->(n2) RETURN count(r)"):
            return record.values()[0]

    @property
    def size(self):
        with self.driver.session() as session:
            return session.read_transaction(self._get_size)

    def create_entity(self, name:str, entity_type:str, source:str, **args):
        with self.driver.session() as session:
            result = session.read_transaction(self._find_node_by, "Entity", name = name)
            if (len(result) > 0):
                session.close()
                print(f"matched Entity {result[0]}")
                return result[0]

            args["name"] = name
            args["type"] = entity_type
            args["source"] = source
            result = session.write_transaction(self._create_node, "Entity", **args)
            session.close()
            print(f"created Entity {result[0]}")
            return result[0]

    def create_relationship(self, entity1_name:str, entity2_name:str, relationship_name:str, **args):
        with self.driver.session() as session:
            # Write transactions allow the driver to handle retries and transient errors
            result = session.write_transaction(self._create_relationship, relationship_name , "Entity", {"name":entity1_name} , "Entity", {"name":entity2_name}, **args)
            # for record in result:
            #     print("Created friendship between: {p1}, {p2}".format(
            #         p1=record['p1'], p2=record['p2']))

    def run_read_query(self, query:str):
        with self.driver.session() as session:
            return session.read_transaction(self._run_query, query=query)

    def run_write_query(self, query:str):
        with self.driver.session() as session:
            return session.write_transaction(self._run_query, query=query)

    @staticmethod
    def _run_query(tx, query:str):
        return tx.run(query)

    @staticmethod
    def _find_node_by(tx, node_type:str, where:str = None, **args):
        if (not where):
            where = " AND ".join([f'node.{arg[0]} = "{arg[1]}"' for arg in args.items()])

        query = (
            f"MATCH (node:{node_type}) "
            f"WHERE {where} "
            f"RETURN DISTINCT node"
        )

        result = tx.run(query)
        return [record["node"]._properties for record in result]

    @staticmethod
    def _create_node(tx, node_type:str, properties:str = None, **args):
        if (not properties):
            properties = ", ".join([f'{arg[0]}:"{arg[1]}"' for arg in args.items()])

        query = (
            f"CREATE (node:{node_type} {{{properties}}}) "
            f"RETURN node"
        )

        result = tx.run(query)
        return [record["node"]._properties for record in result]

    @staticmethod
    def _create_relationship(tx, relationship_name:str, nodeType1:str, properties1:dict, node_type2:str, properties2:dict, **args):
        where1 = " AND ".join([f'p1.{arg[0]} = "{arg[1]}"' for arg in properties1.items()])
        where2 = " AND ".join([f'p2.{arg[0]} = "{arg[1]}"' for arg in properties2.items()])
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

"""
Usage example:

    app = GraphStorage()
    app.create_entity("Raul Lala", "Person", "")
    app.create_entity("Lorenzo Cardaño", "Person", "", work="Raise dragons")
    app.create_entity("Julio Cardaño", "Person", "", hobby="Fight dragons")
    app.create_relationship("Raul Lala", "Lorenzo Cardaño", "FriedsWith", sice = "2018", level = "casual")
    app.create_relationship("Raul Lala", "Julio Cardaño", "FriedsWith", sice = "2019", level = "casual")
    app.create_relationship("Lorenzo Cardaño", "Julio Cardaño", "Rival", sice = "2020", level = "intense")
"""