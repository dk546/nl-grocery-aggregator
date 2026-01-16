# Deployment Runbook - NL Grocery Aggregator

> This document provides step-by-step instructions for deploying the NL Grocery Aggregator backend and frontend services to Render.com.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Backend Deployment (FastAPI)](#backend-deployment-fastapi)
- [Streamlit UI Deployment](#streamlit-ui-deployment)
- [Mobile UI Deployment (Static Site)](#mobile-ui-deployment-static-site)
- [Post-Deployment Verification](#post-deployment-verification)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

1. **Render.com Account**: Sign up at https://render.com (free tier available)
2. **GitHub Access**: Repository must be accessible to Render (public or connected private repo)
3. **Required Secrets**:
   - Apify API token (for Albert Heijn and Jumbo scraping)
   - Picnic username and password (for Picnic scraping)
4. **Optional**: Postgres database (for analytics event persistence)

---

## Backend Deployment (FastAPI)

### Step 1: Create Backend Service from Blueprint

1. In Render dashboard, go to **Blueprints**
2. Click **New Blueprint**
3. Connect your GitHub repository: `nl-grocery-aggregator`
4. Select the repository and branch (usually `main`)
5. Render will detect `render.yaml` and create services automatically

### Step 2: Configure Backend Environment Variables

After the backend service is created, navigate to its **Environment** tab and set:

#### Required Environment Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `APIFY_TOKEN` | Apify API token for scraping | `apify_api_xxxxx...` |
| `PICNIC_USERNAME` | Picnic account email | `your-email@example.com` |
| `PICNIC_PASSWORD` | Picnic account password | `your-password` |

#### Required for Production CORS

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend URLs | `https://nl-grocery-aggregator-frontend.onrender.com,https://your-mobile-ui.onrender.com` |

**Important**: 
- Set `CORS_ALLOWED_ORIGINS` to your actual frontend URLs (Streamlit UI + Mobile UI)
- Do NOT include trailing slashes
- Separate multiple origins with commas (no spaces needed, but they're trimmed automatically)

#### Optional Environment Variables

| Variable | Description | When to Use |
|----------|-------------|-------------|
| `DATABASE_URL` | Postgres connection string | If you want analytics event persistence |
| `PYTHON_VERSION` | Python version | Already set in `render.yaml` (3.10.0) |

### Step 3: Deploy

1. Click **Manual Deploy** → **Deploy latest commit** (or push to trigger auto-deploy)
2. Wait for build to complete (usually 2-3 minutes)
3. Check **Logs** tab for startup confirmation:
   - Look for: `CORS allowed origins: [...]`
   - Look for: `Application startup complete`

### Step 4: Verify Backend Health

Once deployed, test the health endpoint:

```bash
curl https://your-backend-url.onrender.com/health
```

Expected response:
```json
{
  "status": "ok",
  "name": "NL Grocery Aggregator API",
  "version": "1.0.0",
  "uptime_seconds": 123,
  "db_enabled": false  // or true if DATABASE_URL is set
}
```

---

## Streamlit UI Deployment

### Step 1: Service Creation

The Streamlit service should be created automatically from `render.yaml`. If not:

1. In Render dashboard, click **New** → **Web Service**
2. Connect the same repository: `nl-grocery-aggregator`
3. Use these settings:
   - **Name**: `nl-grocery-aggregator-frontend`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run streamlit_app/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`

### Step 2: Configure Environment Variables

Set in the Streamlit service **Environment** tab:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `BACKEND_URL` | Backend API URL | `https://nl-grocery-aggregator.onrender.com` |
| `PYTHON_VERSION` | Python version | `3.10.0` (already set in render.yaml) |

**Important**: 
- Set `BACKEND_URL` to your actual backend service URL (from Step 1)
- Do NOT include trailing slash
- This is the URL the Streamlit UI will use to call the backend API

### Step 3: Deploy and Verify

1. Deploy the service (manual or auto-deploy)
2. Wait for build to complete
3. Open the service URL (e.g., `https://nl-grocery-aggregator-frontend.onrender.com`)
4. Verify:
   - UI loads without errors
   - Search functionality works
   - Cart operations work

---

## Mobile UI Deployment (Static Site)

The mobile UI is in a **separate private repository** (`smartbite-mobile-ui`). Deploy it as a **Static Site** on Render.

### Step 1: Create Static Site

1. In Render dashboard, click **New** → **Static Site**
2. Connect the repository: `smartbite-mobile-ui` (private repo)
3. Render will auto-detect Vite build settings

### Step 2: Configure Build Settings

| Setting | Value |
|---------|-------|
| **Name** | `smartbite-mobile-ui` (or your preferred name) |
| **Build Command** | `npm ci && npm run build` |
| **Publish Directory** | `dist` |

### Step 3: Configure Environment Variables

Set in the Static Site **Environment** tab:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `VITE_API_BASE_URL` | Backend API URL | `https://nl-grocery-aggregator.onrender.com` |

**Critical**: 
- Set `VITE_API_BASE_URL` to your **backend service URL** (not the Streamlit UI)
- Do NOT include trailing slash
- This is a **build-time variable** - changes require rebuild

### Step 4: Update Backend CORS

After deploying the mobile UI, **update the backend `CORS_ALLOWED_ORIGINS`** to include the mobile UI URL:

```
https://nl-grocery-aggregator-frontend.onrender.com,https://your-mobile-ui.onrender.com
```

Then redeploy the backend service for CORS changes to take effect.

### Step 5: Deploy and Verify

1. Deploy the static site (manual or auto-deploy)
2. Wait for build to complete
3. Open the service URL
4. Verify:
   - UI loads without CORS errors
   - Search works (calls backend)
   - Cart operations work (session ID persists)

---

## Post-Deployment Verification

### Smoke Test Checklist

Run these tests after deployment to verify everything works:

#### Backend Health Check

```bash
curl https://your-backend.onrender.com/health
```

**Expected**: `200 OK` with `"status": "ok"` and `db_enabled` field

#### Backend API Documentation

```bash
open https://your-backend.onrender.com/docs
```

**Expected**: Swagger UI loads and shows all endpoints

#### Search Endpoint Test

```bash
curl "https://your-backend.onrender.com/search?q=melk&retailers=ah,jumbo&size=5"
```

**Expected**: Returns JSON with `results` array containing products

#### Streamlit UI Test

1. Open Streamlit UI URL
2. Perform a search
3. Add items to cart
4. View basket

**Expected**: All operations work without errors

#### Mobile UI Test

1. Open mobile UI URL
2. Perform a search (should call backend)
3. Add items to cart
4. View basket

**Expected**: 
- No CORS errors in browser console
- Search returns results from backend
- Cart persists across page refreshes (session ID in localStorage)

#### CORS Verification

```bash
curl -H "Origin: https://your-mobile-ui.onrender.com" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Session-ID" \
     -X OPTIONS \
     https://your-backend.onrender.com/search
```

**Expected**: Response includes `Access-Control-Allow-Origin` header with your frontend URL

---

## Troubleshooting

### Backend Issues

#### CORS Errors

**Symptom**: Browser console shows CORS errors when calling backend from frontend

**Solution**:
1. Verify `CORS_ALLOWED_ORIGINS` is set in backend environment variables
2. Ensure frontend URL matches exactly (including `https://` protocol)
3. Check backend logs for: `CORS allowed origins: [...]`
4. Redeploy backend after changing CORS settings

#### Backend Not Starting

**Symptom**: Service shows "Unhealthy" or crashes on startup

**Check**:
1. View **Logs** tab for error messages
2. Verify required environment variables are set (APIFY_TOKEN, PICNIC_USERNAME, PICNIC_PASSWORD)
3. Check Python version matches (3.10.0)

#### Search Returns Empty Results

**Symptom**: `/search` endpoint returns empty `results: []`

**Possible Causes**:
1. Apify token invalid or expired
2. Picnic credentials incorrect
3. Retailer connectors failing (check logs)

**Solution**: Verify API credentials in environment variables

### Streamlit UI Issues

#### Backend Connection Failed

**Symptom**: Streamlit UI shows "Failed to fetch" or backend errors

**Solution**:
1. Verify `BACKEND_URL` is set correctly (no trailing slash)
2. Verify backend service is running and healthy
3. Check backend logs for incoming requests

### Mobile UI Issues

#### CORS Errors

**Symptom**: Browser console shows CORS errors

**Solution**:
1. Verify mobile UI URL is included in backend `CORS_ALLOWED_ORIGINS`
2. Ensure `VITE_API_BASE_URL` points to backend (not Streamlit UI)
3. Rebuild mobile UI after changing `VITE_API_BASE_URL` (it's a build-time variable)

#### API Calls Fail

**Symptom**: Network requests fail with 404 or connection errors

**Solution**:
1. Verify `VITE_API_BASE_URL` is correct (check in build logs)
2. Ensure backend service is running
3. Check browser network tab for actual request URLs

### General Issues

#### Environment Variables Not Applied

**Symptom**: Changes to environment variables don't take effect

**Solution**:
1. Ensure variables are set in Render dashboard (not just `render.yaml`)
2. Redeploy service after changing environment variables
3. For Vite (`VITE_*`), rebuild is required (build-time variables)

#### Database Not Enabled

**Symptom**: Analytics events not persisting

**Solution**:
1. Create a Postgres database in Render
2. Set `DATABASE_URL` in backend environment variables
3. Redeploy backend service
4. Verify with `/health` endpoint: `db_enabled: true`

---

## Security Notes

1. **Never commit secrets**: All secrets (APIFY_TOKEN, PICNIC_PASSWORD, etc.) must be set in Render dashboard, not in `render.yaml`
2. **CORS whitelist**: Only include trusted frontend URLs in `CORS_ALLOWED_ORIGINS`
3. **Session IDs**: Currently session-based (no auth). For production, consider implementing authentication
4. **API keys**: Keep Apify and Picnic credentials secure and rotate if compromised

---

## Next Steps

After successful deployment:

1. Monitor backend logs for errors
2. Set up Render health checks (automatic with `/health` endpoint)
3. Configure custom domain (optional, Render Pro plan)
4. Set up monitoring/alerts for service uptime
5. Consider adding authentication for production use

---

## Reference: Environment Variables Summary

### Backend Service

```
Required:
- APIFY_TOKEN
- PICNIC_USERNAME
- PICNIC_PASSWORD
- CORS_ALLOWED_ORIGINS

Optional:
- DATABASE_URL (for analytics persistence)
- PYTHON_VERSION (defaults to 3.10.0)
```

### Streamlit Service

```
Required:
- BACKEND_URL
- PYTHON_VERSION (defaults to 3.10.0)
```

### Mobile UI Static Site

```
Required (build-time):
- VITE_API_BASE_URL
```

---

*Last updated: Based on current deployment configuration*
