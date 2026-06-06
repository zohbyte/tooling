FROM nginx:alpine
RUN apk add --no-cache apache2-utils gettext
COPY default.conf.template /etc/nginx/conf.d/default.conf.template
COPY start.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]
