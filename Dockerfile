# Supervisor 2026.04.0 and newer no longer pass BUILD_FROM, so the default is
# required: without it "FROM $BUILD_FROM" expands to an empty image name and the
# build fails with "base name ($BUILD_FROM) should not be blank".
# A build.yaml with build_from is deprecated as well, the base image lives here.
# Keep the ARG so older Supervisors and the builder actions can still override.
#
# Do NOT switch this to base-python: that image compiles CPython into
# /usr/local and puts /usr/local/bin first in PATH, so it does not see the
# /usr/lib/python3.x/site-packages of the py3-* apk packages below and monitor.py
# dies with "ModuleNotFoundError: No module named 'serial'". With base-python you
# would have to install with pip instead of apk.
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.24
FROM ${BUILD_FROM}

ENV LANG C.UTF-8

# python3, pyserial 3.5 and paho-mqtt 1.6.1 from Alpine, all matching the system
# python of the image (paho-mqtt must stay on 1.x, monitor.py uses the old API)
RUN apk add --no-cache python3 py3-pyserial py3-paho-mqtt

COPY monitor.py /
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
