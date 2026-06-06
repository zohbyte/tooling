#!/bin/sh
set -e

if [ -z "$FRONTEND_USER" ] || [ -z "$FRONTEND_PASS" ]; then
  echo "Environment variables FRONTEND_USER and FRONTEND_PASS must be set"
  exit 1
fi

htpasswd -bc /etc/nginx/.htpasswd "$FRONTEND_USER" "$FRONTEND_PASS"

# Default conf is static and already contains Nginx variable markers ($host etc).
# Using cp removes envsubst failure modes for escaped nginx variables and keeps config simple.
cp /etc/nginx/conf.d/default.conf.template /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
