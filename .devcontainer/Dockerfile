FROM mcr.microsoft.com/devcontainers/python:3.13

RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    pip3 install --no-cache-dir -r /tmp/requirements.txt

RUN --mount=type=bind,source=req_ha_default_config.txt,target=/tmp/req_ha_default_config.txt \
    pip3 install --no-cache-dir -r /tmp/req_ha_default_config.txt
