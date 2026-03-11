#!/bin/bash
set -e

DOMAIN="${1:?Usage: $0 <domain> <email> [--staging]}"
EMAIL="${2:?Usage: $0 <domain> <email> [--staging]}"
STAGING=0

for arg in "$@"; do
    [ "$arg" = "--staging" ] && STAGING=1
done

if [ "$STAGING" -eq 1 ]; then
    COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.staging.yml -f docker-compose.volumes.yml"
else
    COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.volumes.yml"
fi

echo "### Downloading recommended TLS parameters..."
$COMPOSE run --rm --no-deps --entrypoint sh certbot -c \
    "wget -q -O /etc/letsencrypt/options-ssl-nginx.conf \
         https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf && \
     wget -q -O /etc/letsencrypt/ssl-dhparams.pem \
         https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem"

echo "### Creating dummy certificate for $DOMAIN..."
$COMPOSE run --rm --no-deps --entrypoint sh certbot -c \
    "mkdir -p /etc/letsencrypt/live/$DOMAIN && \
     openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
         -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
         -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
         -subj '/CN=localhost' 2>/dev/null"

echo "### Starting nginx..."
$COMPOSE up --no-deps -d nginx

echo "### Waiting for nginx to be ready..."
sleep 5

echo "### Requesting Let's Encrypt certificate for $DOMAIN..."
$COMPOSE run --rm --no-deps certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

echo "### Reloading nginx..."
$COMPOSE exec nginx nginx -s reload

echo "### Done! Certificate issued for $DOMAIN"
echo "### You can now run 'make prod' or 'make staging' to start the full stack."
