app:
	docker-compose -f build/docker-compose.yml up

image:
	docker-compose -f build/docker-compose.yml build
