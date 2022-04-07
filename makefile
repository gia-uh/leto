app:
	docker-compose -f docker/docker-compose.yml up --remove-orphans

image:
	docker-compose -f docker/docker-compose.yml build

shell:
	docker exec -it leto bash

.PHONY: docs
docs:
	docker exec -it leto-docs mkdocs gh-deploy
	git commit -a -m "Deployed"

pull:
	docker pull letoai/leto:latest

pull-safe:
	docker pull docker.uclv.cu/letoai/leto:latest
	docker tag docker.uclv.cu/letoai/leto:latest letoai/leto:latest
	docker pull docker.uclv.cu/neo4j:latest
	docker tag docker.uclv.cu/neo4j:latest neo4j/neo4j:latest

clean-neo4j:
	sudo rm -rf data/neo4j* && docker-compose -f docker/docker-compose.yml restart neo4j

test:
	docker-compose -f docker/docker-compose.yml run leto pytest -v tests

format:
	docker-compose -f docker/docker-compose.yml run leto black leto