FROM python:3.13

RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    pip3 install --no-cache-dir -r /tmp/requirements.txt

RUN --mount=type=bind,source=req_ha_default_config,target=/tmp/req_ha_default_config \
    pip3 install --no-cache-dir -r /tmp/req_ha_default_config

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -ms /bin/bash $USERNAME

USER $USERNAME
