# PyPI Trusted Publishing Setup

Configure PyPI Trusted Publishing for this project before attempting PyPI publication.

- PyPI project name: `aquote-router`
- GitHub owner: `tabman2026`
- GitHub repository: `aquote-router`
- Workflow file: `publish.yml`
- Environment: `pypi`
- Release tag: `v0.1.0`

The workflow uses GitHub OIDC Trusted Publishing and does not require storing PyPI credentials in the repository.

Current status: GitHub repository, tag, and release are online. The publish workflow ran and failed with PyPI Trusted Publishing `invalid-publisher`, so actual PyPI publication is pending Trusted Publisher configuration in the PyPI project backend.
