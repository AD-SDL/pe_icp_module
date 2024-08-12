FROM ghcr.io/ad-sdl/wei

LABEL org.opencontainers.image.source=https://github.com/AD-SDL/python_template_module
LABEL org.opencontainers.image.description="An example module that implements a basic sleep(t) function"
LABEL org.opencontainers.image.licenses=MIT

#########################################
# Module specific logic goes below here #
#########################################

RUN mkdir -p python_template_module

COPY ./src python_template_module/src
COPY ./README.md python_template_module/README.md
COPY ./pyproject.toml python_template_module/pyproject.toml
COPY ./tests python_template_module/tests

RUN --mount=type=cache,target=/root/.cache \
    pip install ./python_template_module


CMD ["python", "python_template_module.py"]

#########################################
