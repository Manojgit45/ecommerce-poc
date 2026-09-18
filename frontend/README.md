# Frontend

This folder contains the runnable storefront for the demo.

## Run locally

1. Start the product backend on `http://localhost:8080`.
2. Start the frontend:

```bash
cd frontend
BACKEND_URL=http://localhost:8080 python app.py
```

3. Open `http://localhost:3000`.

## Docker

```bash
cd frontend
docker build -t ecommerce-frontend:local .
docker run --rm -p 3000:3000 -e BACKEND_URL=http://host.docker.internal:8080 ecommerce-frontend:local
```

The app proxies `/api/*` requests to the product service so the browser can talk to one origin.
