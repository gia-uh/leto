app:
	docker-compose -f docker/docker-compose.yml up

image:
	docker-compose -f docker/docker-compose.yml build

pull-safe:
	docker pull docker.uclv.cu/letoai/leto:latest
	docker tag docker.uclv.cu/letoai/leto:latest letoai/leto:latest
