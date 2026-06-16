# GitHub Deployment Notes

## What Goes to GitHub

Commit source code, tests, docs, scripts, package manifests, sample CSV data, and frontend JSON snapshots under `src/data/`.

Do not commit:

- `.env`
- `data/`
- `node_modules/`
- `.tools/`
- `dist/`
- SQLite databases

These are already covered by `.gitignore`.

## Initial Push

If the GitHub repository already exists, add it as `origin`:

```bash
git remote add origin git@github.com:OWNER/REPO.git
git push -u origin codex/v1-0-rc-packaging
```

If using HTTPS:

```bash
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin codex/v1-0-rc-packaging
```

## CI

The repository includes `.github/workflows/ci.yml`. GitHub Actions runs:

- `npm ci`
- backend unit tests
- frontend build

## Release Tag

After the branch is merged, tag the RC:

```bash
git tag v1.0.0-rc.1
git push origin v1.0.0-rc.1
```
