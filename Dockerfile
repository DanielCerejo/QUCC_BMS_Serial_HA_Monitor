ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

#COPY requirements.txt /

RUN apk add --no-cache python3  py3-pyserial py3-paho-mqtt
RUN rm -fr /root/.cache

COPY monitor.py /
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]