# Welcome to the LETO MVP docs

In this documentation you will find the necessary instructions to set up an interact with the LETO application.

!!! warning
    LETO is a work-in-progress, and it's currently not suitable for production use. Everything in this documentation can change at any time until the APIs are fully stabilized.

## Quick start

The easiest way to get LETO up and running at the moment is to clone the source code repository and spin up the development environment.
You will need `docker` and `git` installed.
If you are on Linux, there's a `makefile` ready for you.

```bash
$ git clone https://github.com/LETO-ai/leto-mvp
$ make
```

This will spin up an instance of the LETO UI, the neo4j backend, and these docs.
Then navigate to <locahost:8501> to interact with the UI.

!!! note
    Refer to the [user guide](./guide) for details about using the application.

## Collaboration

In LETO we use trunk-based development. Developers use short-lived branches which are pushed to the central repository, and merged back to the `main` branch as quickly as possible.

For development, you will need Visual Studio Code (or another suitable editor). You will work in the development enviroment described in the previous section.

!!! note
    Refer to the [development guide](./dev) for more details.
