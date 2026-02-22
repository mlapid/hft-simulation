FROM grafana/grafana:latest

USER root

RUN apk add --no-cache curl jq

COPY infra/grafana/init.sh /init.sh
RUN chmod +x /init.sh

ENTRYPOINT ["/init.sh"]