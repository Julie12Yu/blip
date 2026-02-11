# blip

## Environment setup

Create your env file from the template so the app and Docker builds have the required variables.

```bash
cp .env.model .env
# Edit .env and set the values (Supabase URL/key, API keys, etc.)
```

- **Root `.env.model`** – Used by the Python app, API/cron image, and old FastAPI deployment. Copy to `.env` at the repo root.
- **`blip-react/.env.model`** – Used by the React app (`REACT_APP_URL`, `REACT_APP_KEY`). Copy to `blip-react/.env` for local dev; for Docker, pass these as build-args (see below).

### Docker and env

- **API / old_deployment_stuff images**: Set env at runtime with an env file:
  ```bash
  docker run --env-file .env your-image
  ```
- **blip-react image**: React bakes `REACT_APP_*` at build time. Build with args from your env:
  ```bash
  docker build -f blip-react/Dockerfile --build-arg REACT_APP_URL="$(grep REACT_APP_URL blip-react/.env | cut -d= -f2-)" --build-arg REACT_APP_KEY="$(grep REACT_APP_KEY blip-react/.env | cut -d= -f2-)" -t blip-react ./blip-react
  ```
  Or use a `docker-compose` build that passes the env file.

Do not commit `.env`; keep it in `.gitignore`.