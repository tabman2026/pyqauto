# Manual GitHub Publish Steps

Use these steps if the GitHub CLI is unavailable or not authenticated.

```bash
git remote add origin https://github.com/<owner>/aquote-router.git
git branch -M main
git push -u origin main
git push origin v0.1.0
```

Then create a public GitHub repository named `aquote-router`, add topics from the README, and create a release for tag `v0.1.0` using `CHANGELOG.md`.
