FROM ghcr.io/ad-sdl/wei

LABEL org.opencontainers.image.source=https://github.com/AD-SDL/pe_icp_module
LABEL org.opencontainers.image.description="An example module that implements a basic sleep(t) function"
LABEL org.opencontainers.image.licenses=MIT

#########################################
# Module specific logic goes below here #
#########################################

RUN mkdir -p pe_icp_module

COPY ./src pe_icp_module/src
COPY ./README.md pe_icp_module/README.md
COPY ./pyproject.toml pe_icp_module/pyproject.toml
COPY ./tests pe_icp_module/tests

RUN --mount=type=cache,target=/root/.cache \
    pip install ./pe_icp_module


CMD ["python", "pe_icp_module.py"]

#########################################
