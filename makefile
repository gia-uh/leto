app:
	docker-compose -f docker/docker-compose.yml up

image:
	docker-compose -f docker/docker-compose.yml build

shell:
	docker-compose -f docker/docker-compose.yml run leto bash

pull:
	docker pull letoai/leto:latest

pull-safe:
	docker pull docker.uclv.cu/letoai/leto:latest
	docker tag docker.uclv.cu/letoai/leto:latest letoai/leto:latest

clean-neo4j:
	sudo rm -rf data/neo4j

test:
	pytest leto tests --doctest-modules --cov leto

format:
	black leto