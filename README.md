# Vimo Assistant

## Poetry

This project uses poetry. It's a modern dependency management
tool.

To run the project use this set of commands:

```bash
poetry install
poetry run python -m app
```

This will start the server on the configured host.

You can find swagger documentation at `/api/docs`. For example <http:localhost:8000/api/docs>.

You can read more about poetry here: <https://python-poetry.org/>

## Docker

You can start the project with docker using this command:

```bash
docker-compose up --build
```

If you want to develop in docker with autoreload and exposed ports add `-f deploy/docker-compose.dev.yml` to your docker command.
Like this:

```bash
docker-compose -f docker-compose.yml -f deploy/docker-compose.dev.yml --project-directory . up --build
```

This command exposes the web application on port 8000, mounts current directory and enables autoreload.

But you have to rebuild image every time you modify `poetry.lock` or `pyproject.toml` with this command:

```bash
docker-compose build
```

## Project structure

```bash
$ tree "app"
app
├── core                   # module contains project configuration
├── db                     # module contains db configurations
│   ├── dao                # Data Access Objects. Contains different classes to interact with database.
│   └── models             # Package contains different models for ORMs.
├── repositories           # Package contains different repositories for logic applications.
├── schemas                # Package contains different schemas for pydantic.
├── services               # Package for different external services such as rabbit or redis, openai etc.
├── utils                  # Package for different utilities.
├── static                 # Static content.
└── web                    # Package contains web server. Handlers, startup config.
    ├── api                # Package with all handlers.
    │   └── router.py      # Main router.
    ├── application.py     # FastAPI application configuration.
    └── lifespan.py        # Contains actions to perform on startup and shutdown.
├── __main__.py            # Startup script. Starts uvicorn.
```

## Configuration

This application can be configured with environment variables.

You can create `.env` file in the root directory and place all
environment variables here.

An example of .env file:

```bash
RELOAD="True"
PORT="8000"
ENVIRONMENT="dev"
```

You can read more about BaseSettings class here: <https://pydantic-docs.helpmanual.io/usage/settings/>

## Pre-commit

To install pre-commit simply run inside the shell:

```bash
pre-commit install
```

pre-commit is very useful to check your code before publishing it.
It's configured using .pre-commit-config.yaml file.

By default it runs:

* black (formats your code);
* mypy (validates types);
* ruff (spots possible bugs);

You can read more about pre-commit here: <https://pre-commit.com/>

## How to use the template

1. Clone the repository.
2. Write the code logic of Dify tools to the repository in `app/repositories` directory.
3. Write the API at `app/web/api/router.py`. Use the `make_response` function from `app/utils/api_utils.py` to create a response.
4. Add some dependencies to `pyproject.toml` if needed. And run `poetry install`.
5. Run the application with `python3 -m app` or with docker.
