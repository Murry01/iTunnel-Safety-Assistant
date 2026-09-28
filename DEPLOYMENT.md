# GitHub, Docker, CI/CD, and web deployment guide

This project is a full-stack application: a Vite/React frontend, a FastAPI
backend, local SQLite/LanceDB research stores, and an external Neo4j database.
GitHub Pages publishes static files only, so it cannot run this backend. The
recommended proof-of-concept deployment is one Docker web service built from
the GitHub repository. The included `render.yaml` uses Render for that service.

## 1. Security checks before the first commit

1. Revoke the OpenAI credential that previously appeared in `.env.template`.
2. Keep real credentials only in `.env`. The included `.gitignore` excludes it.
3. Check whether the accident dataset can legally and ethically be published.
   Begin with a **private** GitHub repository if this is uncertain.
4. Review the staged files before every commit:

   ```powershell
   git status
   git diff --cached
   ```

`accidents.db` and `lancedb/` are intentionally retained as frozen runtime
assets. They total less than 5 MB. Remove them and rebuild the deployment design
if the source data cannot be stored in GitHub.

## 2. Install Git and Docker on Windows

Install Git for Windows or GitHub Desktop, then restart PowerShell. Verify:

```powershell
git --version
```

Install Docker Desktop and verify:

```powershell
docker version
docker compose version
```

## 3. Create and push the GitHub repository

On GitHub, create an empty private repository. Do not initialize it with a
README, `.gitignore`, or license because this local project already has files.

From the project root:

```powershell
Set-Location "C:\Users\USER\Desktop\construction_rag"

git init
git config user.name "YOUR NAME"
git config user.email "YOUR-GITHUB-EMAIL"

git add .
git status
git commit -m "Initial research proof-of-concept"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Git Credential Manager should open a browser for authentication. If `origin`
already exists, inspect it with `git remote -v` and change it with:

```powershell
git remote set-url origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
```

For later changes:

```powershell
git add .
git commit -m "Describe the change"
git push
```

## 4. Run the Docker deployment locally

The multi-stage `Dockerfile` builds the React frontend and copies it into the
FastAPI image. The backend then serves both the UI and `/api` from one origin.

When Docker connects to Neo4j Desktop on the Windows host, use this value in
your local `.env`:

```dotenv
NEO4J_URI=bolt://host.docker.internal:7687
```

Build and run:

```powershell
docker compose up --build
```

Open:

```text
http://localhost:8000
http://localhost:8000/api/health
```

Stop the application:

```powershell
docker compose down
```

Remove the container and its persisted local chat volume only when the chat
history is no longer needed:

```powershell
docker compose down --volumes
```

## 5. Deploy the web application from GitHub

The hosted container cannot connect to Neo4j Desktop through `localhost` or
`host.docker.internal`. Use Neo4j Aura or another network-accessible Neo4j
instance for deployment.

1. Create or select a dedicated hosted Neo4j database.
2. Load the corrected graph into that dedicated database using the existing
   ingestion command and its hosted credentials.
3. Create a Render account and connect the GitHub account containing the repo.
4. In Render, select **New > Blueprint** and choose this repository. Render will
   detect `render.yaml`.
5. Enter the requested secret values:
   - `OPENAI_API_KEY`
   - `NEO4J_URI`
   - `NEO4J_USER`
   - `NEO4J_PASSWORD`
6. Create the service and wait for the Docker build and health check.
7. Open the assigned `onrender.com` URL and verify `/api/health`, the UI, a
   statistical question, a retrieval question, and a graph question.

The free Render service has an ephemeral filesystem and can spin down when
idle. The application will still run, but `chats.db` can be reset after a
restart or redeploy. Add a paid persistent disk mounted at `/app/runtime` if
conversation history must survive deployments.

## 6. CI/CD behavior

The workflow `.github/workflows/ci.yml` runs on pull requests and pushes to
`main`. It performs three checks:

1. installs Python dependencies and runs the offline evaluation tests;
2. installs and builds the React frontend;
3. builds the complete Docker image.

The included Render Blueprint uses:

```yaml
autoDeployTrigger: checksPass
```

Therefore, pushes to `main` deploy only after the GitHub Actions checks pass.
Pull requests run CI without deploying. Keep repository workflow-token
permissions read-only unless a later workflow has a specific need for write
access.

## 7. Recommended GitHub settings

Under **Settings > Branches**, protect `main` and require the three CI jobs
before merging. Under **Settings > Secrets and variables > Actions**, add
secrets only if a future workflow needs them; this CI workflow does not need
OpenAI or Neo4j credentials. Application secrets belong in the Render service.

Useful official references:

- GitHub: adding local code to a repository — https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github
- GitHub Actions for Python — https://docs.github.com/en/actions/tutorials/build-and-test-code/python
- GitHub Actions secrets — https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
- Docker multi-stage builds — https://docs.docker.com/get-started/docker-concepts/building-images/multi-stage-builds/
- Render Docker services — https://render.com/docs/docker
- Render Blueprint specification — https://render.com/docs/blueprint-spec
