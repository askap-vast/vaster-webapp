# Contributing to the `YWANG - VAST` project

## Development environment setup

Required:

- docker
- docker-compose

Create your python environment:

- `python -m venv env`, `source env/bin/activate`, `pip install -r requirements.txt -r requirements_dev.txt`

### Running dev version with `docker compose`

1. build the docker containers and run
   - `docker compose up -d`

In this development mode, changes to most of your files will be auto-reloaded by the Django StatReloader

1. shut down containers (but persist volumes)
   - `docker-compose down`
2. shut down containers and delete volumes
   - `docker-compose down -v`

If you want to create new fixtures you can run `docker-compose exec web python manage.py dumpdata <app.model> --indent 4 > <app>>/fixtures/<model>.json` where `<app.model>` is the model (table) you are dumping, and `<model>.json` is the location of the fixture to be written.

## Style guide

This repository has implemented a pre-commit hook which will check that files are formatted correctly before committing changes to github.

### The formatters

The following formatters are configured:

- black
  - A python formatter (eg, inspects your .py files)
  - Will re-write your files to obey a given format
  - The formatting changes are mostly around spacing, line breaks, and quotes - the sort of things that don't change the operation of your code.
- flake8
  - A python linter
  - Will not re-write your files
  - Checks for compliance with [PEP8](https://peps.python.org/pep-0008/)
  - Any violations will be reported and left for you to fix.
  - (if you **really** want to keep a line of code then append `# noqa` and flake8 will pass it)
- prettier
  - A formatter for .html, .css, .yaml, .md (and a bunch of other things)
  - Will re-write your files
  - Has been set up to ignore all the files in the `static` directory

If you try to commit code that doesn't conform to these formatters your commit will be rejected

### Install

run `pre-commit install` in the repo root directory to enable the pre-commit hooks.

### Running

The hooks will be run automatically whenever you try to `git commit`.
They can be run manually via `pre-commit run` to see if your commit is going to be accepted, this will give feedback on which files (lines) are failing.
If you are using VSCode as your IDE then when you press the "commit" button you might get a pop-up that says there is an error with the commit.
In this case press the "Command Output" button to see the output from the pre-commit checks.
