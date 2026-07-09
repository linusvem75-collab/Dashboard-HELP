# Retail Sales Intelligence Dashboard

An interactive Streamlit version of the retail sales analysis: temporal trends,
category profitability, customer segments, pricing sensitivity, and regional
market share — all filterable in real time.

## Files

```
streamlit_app/
├── app.py              # Main dashboard (6 tabs)
├── data_prep.py         # Cached data loading + cleaning logic
├── requirements.txt      # Python dependencies
└── data/
    └── mock_dataset.csv  # Bundled sample dataset (used if no file is uploaded)
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

The app works out of the box using the bundled sample dataset. Anyone using
the deployed app can also upload their own CSV from the sidebar (it must
follow the same column structure: `Order Date`, `Ship Date`, `Sales`,
`Profit`, `UnitPrice`, `Discount`, `Product Category`, `Product Sub-Category`,
`Customer Segment`, `Region & District`, etc.).

---

## Deploying it as a public website

Here are your realistic options, roughly ordered from easiest/free to
most flexible/production-grade.

### 1. Streamlit Community Cloud (easiest, free)
Best if: you just want a shareable link fast, and don't mind a public GitHub repo.

1. Push this folder to a public (or private, on paid tiers) GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. Click "New app," pick the repo/branch, set the main file to `app.py`.
4. Deploy — you get a URL like `https://your-app.streamlit.app`.
5. Any push to the branch auto-redeploys.

Limits: shared compute resources, apps sleep after inactivity (free tier),
1 GB RAM on the free tier — plenty for this dataset size.

### 2. Hugging Face Spaces (free, good for public demos)
Best if: you want a free permanent URL with a bit more visibility/community reach.

1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space), SDK = Streamlit.
2. Push these files to the Space's git repo (it works like a normal git remote).
3. The Space builds automatically from `requirements.txt` and `app.py`.

### 3. Render / Railway / Fly.io (free-to-cheap, more control)
Best if: you want a persistent, always-on app without managing servers yourself.

General pattern (Render as example):
1. Push the folder to GitHub.
2. In Render, "New Web Service" → connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. Render gives you a `https://your-app.onrender.com` URL.

Railway and Fly.io follow the same shape (detect Python, install
requirements, run the start command with the platform's `$PORT`).

### 4. Docker + any cloud (most portable, works anywhere)
Best if: you want to deploy to AWS/GCP/Azure/your own VPS, or need this to
run inside existing company infrastructure.

Create a `Dockerfile` in this folder:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t retail-dashboard .
docker run -p 8501:8501 retail-dashboard
```

From there, push the image to any container host:
- **AWS**: ECS/Fargate, App Runner, or EC2 + Docker
- **GCP**: Cloud Run (easiest — scales to zero, pay per use)
- **Azure**: Container Apps or App Service
- A plain VPS (DigitalOcean, Linode, etc.) with Docker installed, behind Nginx + a domain + Let's Encrypt for HTTPS

### 5. Internal/enterprise deployment
If this needs to sit behind your company's auth (SSO, VPN-only access):
- **Streamlit in Snowflake** or **Streamlit for Teams** style internal hosting if your org already uses Snowflake/Databricks
- Deploy the Docker image to an internal Kubernetes cluster and put it behind your existing reverse proxy / SSO gateway (e.g., Nginx + OAuth2 Proxy, or your cloud provider's IAP)

---

## Which one should you actually pick?

- **Just want to share this with a few colleagues today** → Streamlit Community Cloud.
- **Want a permanent free public demo link** → Hugging Face Spaces.
- **Want something always-on with a custom domain, still cheap** → Render or Fly.io.
- **Need it inside company infrastructure / behind SSO** → Docker image + your existing cloud/K8s setup.

## A note on the bundled dataset

The sample CSV bundled in `data/` is what loads by default so the dashboard
works immediately after deployment. If you're deploying this for real use
with sensitive sales data, do **not** commit real customer data to a public
GitHub repo — instead, either keep the repo private, or remove the bundled
CSV and rely entirely on the sidebar file uploader so the data never touches
the deployed codebase.
