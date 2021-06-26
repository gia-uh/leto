app:
	docker-compose -f docker/docker-compose.yml up

image:
	docker-compose -f docker/docker-compose.yml build

pull-safe:
	docker pull docker.uclv.cu/letoai/leto:latest
	docker tag docker.uclv.cu/letoai/leto:latest letoai/leto:latest

clean-neo4j:
	sudo rm -rf data/neo4j

test:
	pytest leto --doctest-modules --cov leto

format:
	black leto