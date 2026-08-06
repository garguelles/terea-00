COMPOSE := podman compose

.PHONY: migrations migrate start

migrations:
	$(COMPOSE) exec web python manage.py makemigrations

migrate:
	$(COMPOSE) exec web python manage.py migrate

start:
	$(COMPOSE) up
