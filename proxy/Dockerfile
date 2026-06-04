FROM nginxinc/nginx-unprivileged:1-alpine
LABEL maintainer="Brazos Safety Systems"

COPY ./default.conf.tpl /etc/nginx/default.conf.tpl
COPY ./run.sh /run.sh

ENV LISTEN_PORT=8080
ENV APP_HOST=app
ENV APP_PORT=8080
ENV DOMAIN=localhost

USER root
RUN touch /etc/nginx/conf.d/default.conf \
    && chown nginx:nginx /etc/nginx/conf.d/default.conf \
    && chmod +x /run.sh

USER nginx

CMD ["/run.sh"]
