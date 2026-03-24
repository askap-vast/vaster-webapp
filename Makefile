dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.volumes.yml up --build

dev-down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.volumes.yml down

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.volumes.yml up -d --build

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.volumes.yml down

staging:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.staging.yml -f docker-compose.volumes.yml up -d --build

staging-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.staging.yml -f docker-compose.volumes.yml down

cert-init-prod:
	./init-letsencrypt.sh vaster.duckdns.org $(EMAIL)

cert-init-staging:
	./init-letsencrypt.sh vaster-staging.duckdns.org $(EMAIL) --staging
