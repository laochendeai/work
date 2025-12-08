DOCKER_COMPOSE ?= docker-compose

.PHONY: start stop test

start:
	$(DOCKER_COMPOSE) up --build -d

stop:
	$(DOCKER_COMPOSE) down

test:
	$(DOCKER_COMPOSE) exec app python test_actions.py
