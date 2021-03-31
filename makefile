app:
	docker-compose -f docker/docker-compose.yml up

image:
	docker-compose -f docker/docker-compose.yml build
