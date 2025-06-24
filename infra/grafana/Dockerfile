FROM grafana/grafana:latest

USER root

RUN apk add --no-cache curl jq

COPY init.sh /init.sh
RUN chmod +x /init.sh

ENTRYPOINT ["/init.sh"]