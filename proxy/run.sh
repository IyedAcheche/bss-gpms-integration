#!/bin/sh
set -e

envsubst '${LISTEN_PORT} ${APP_HOST} ${APP_PORT} ${DOMAIN}' \
    < /etc/nginx/default.conf.tpl \
    > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
