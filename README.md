# NL Grocery Aggregator

A full-stack application that aggregates grocery product search results from multiple Dutch supermarkets (Albert Heijn, Jumbo, Picnic, and Dirk). This repository contains the **FastAPI backend service** and a **Streamlit pilot/demo UI**. The production mobile UI is developed in a separate private repository.

## Live Demo

👉 **Streamlit Pilot UI**: https://nl-grocery-aggregator-frontend.onrender.com

> ⚠️ This is a demo application. Prices, availability, and health insights are illustrative.

## Table of Contents

- [Repositories](#repositories)
- [Features](#features)
- [Mobile UI (Production)](#mobile-ui-production)
- [Integration Contract](#integration-contract)
- [Project Structure](#project-structure)
- [Local Development](#local-development)
- [API Endpoints](#api-endpoints)
- [Production Deployment](#production-deployment)
- [Running Tests](#running-tests)
- [Architecture Notes](#architecture-notes)
- [Limitations](#limitations)

## Repositories

This project consists of **two repositories**:

### 1. `nl-grocery-aggregator` (This Repository - Public)
- **FastAPI Backend**: REST API for product search, cart management, analytics, and more
- **Streamlit Pilot UI**: Internal/demo interface for testing and development
- **Deployment**: `render.yaml` configuration for Render.com deployment
- **Status**: Source of truth for backend API and pilot UI

### 2. `smartbite-mobile-ui` (Private Repository)
- **Repository**: https://github.com/dk546/smartbite-mobile-ui
- **Tech Stack**: Vite + React + TypeScript
- **Status**: Production direction, exported from Google Stitch/AI Studio
- **Integration**: Consumes backend API from this repository

## Features

### Backend (FastAPI)
- **Unified Product Search**: Search for products across Albert Heijn, Jumbo, Picnic, and Dirk in a single API call
- **Normalized Product Schema**: All products are normalized into a consistent format regardless of retailer
- **Health Tagging**: Automatic classification of products as "healthy", "unhealthy", or "neutral"
- **Price Comparison**: Automatically marks the cheapest option for products with the same name
- **Shopping Cart**: In-memory cart management with session-based isolation
- **Savings Finder**: Analyze basket items and find cheaper alternatives across retailers
- **Saved Baskets/Templates**: Save and reuse basket configurations as named templates
- **Event Logging**: Internal event logging system for analytics (search, cart, savings, templates)
  - Postgres-backed persistence (when `DATABASE_URL` is set) with file-based fallback
  - Non-blocking event logging that never breaks the application
  - Tracks: search events, cart operations, smart swaps, recipe views, template operations
- **Analytics API**: REST endpoints for querying event analytics
  - `GET /analytics/events/recent` - Retrieve recent events
  - `GET /analytics/events/counts` - Get event type counts over time windows
  - Gracefully handles database disabled state with safe fallbacks
- **Search Caching**: TTL-based in-memory cache for search results (60-second TTL)
- **Delivery Slots**: Retrieve available delivery time slots (currently Picnic only)
- **Health Check Endpoint**: `/health` endpoint for monitoring and status checks with uptime information
- **RESTful API**: Clean FastAPI endpoints with automatic OpenAPI documentation

### Pilot UI (Streamlit - Internal/Demo)
The Streamlit interface serves as a **pilot/demo/internal tool** for testing backend functionality. It includes:

- **Search & Compare**: Interactive product search with filters, health tags, and price comparison
- **My Basket**: Shopping cart management with savings finder and smart suggestions
- **Health Insights**: Basket health analytics dashboard
- **Recipes**: Recipe collection with ingredient management
- **Analytics Dashboard**: Internal analytics visualization (demo/internal use only)
- **System Status**: Backend health monitoring and API documentation

> **Note**: The Streamlit UI is for internal use and demo purposes. The mobile UI in `smartbite-mobile-ui` is the production direction.

## Mobile UI (Production)

The production mobile UI is built with Vite + React + TypeScript in the separate `smartbite-mobile-ui` repository (private). This is the **production direction**, while the Streamlit UI serves as an internal demo/pilot tool.

#### Local Development

1. **Clone the repository** (private):
   ```bash
   git clone <smartbite-mobile-ui-repo-url>
   cd smartbite-mobile-ui
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment variables**:
   Create a `.env` file:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```
   > Replace with your backend URL in production (e.g., `https://nl-grocery-aggregator.onrender.com`)

4. **Start development server**:
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:5173` (or another port if 5173 is busy).

#### Production Deployment (Render Static Site)

1. **Build Configuration**:
   - **Build Command**: `npm ci && npm run build`
   - **Publish Directory**: `dist`
   - **Environment Variable**: `VITE_API_BASE_URL=https://your-backend-url.onrender.com`

2. **Deployment Steps**:
   - Connect the `smartbite-mobile-ui` repository to Render
   - Select "Static Site" service type
   - Configure build and publish settings as above
   - Set `VITE_API_BASE_URL` to point to your backend service
   - Deploy!

> **Note**: The mobile UI builds at deploy time, so the `VITE_API_BASE_URL` environment variable must be set in Render's dashboard before building.

## Integration Contract

The mobile UI (`smartbite-mobile-ui`) consumes the backend API from this repository. This section defines the integration contract between frontend and backend.

### Phase 1: Product Discovery (Current)
- **Primary Endpoint**: `GET /search`
  - Parameters: `q` (query), `retailers`, `size`, `page`, `sort_by`, `health_filter`

### Future Phases (Planned)
The following endpoints will be integrated in later phases:
- **Cart Management**: `POST /cart/add`, `POST /cart/remove`, `GET /cart/view`
- **Savings Analysis**: `GET /basket/savings`
- **Analytics**: `GET /analytics/events/recent`, `GET /analytics/events/counts`
- **Delivery**: `GET /delivery/slots`
- **Health Check**: `GET /health`

### Security Requirements

> ⚠️ **Important**: Security must be enforced at the API boundary.

- **No Secrets in Frontend**: All API keys, tokens, and sensitive credentials must be handled server-side only. Never expose secrets to the frontend.
- **AI/LLM Keys**: Any AI/LLM API keys (e.g., OpenAI, Anthropic) must remain on the backend and be exposed via backend endpoints only. Never call AI/LLM APIs directly from the frontend.
- **CORS Configuration**: Backend must configure CORS appropriately for the mobile UI domain.
- **Session Management**: Frontend must use session IDs or tokens as required by backend endpoints.

## Project Structure

```
nl-grocery-aggregator/
├── aggregator/              # Core aggregator logic
│   ├── connectors/         # Retailer-specific connectors
│   │   ├── base.py         # Base connector abstract class
│   │   ├── ah_connector.py # Albert Heijn connector (Apify-based)
│   │   ├── jumbo_connector.py # Jumbo connector (Apify-based)
│   │   ├── dirk_connector.py # Dirk connector (Apify-based)
│   │   └── picnic_connector.py # Picnic connector (python-picnic-api)
│   ├── cart.py             # Shopping cart management
│   ├── health.py           # Health tagging logic
│   ├── models.py           # Pydantic models for cart
│   ├── search.py           # Aggregated search logic
│   ├── savings.py          # Savings finder logic
│   ├── templates.py        # Saved basket templates
│   ├── events.py           # Event logging utility (DB + file fallback)
│   ├── db.py               # Database layer (Postgres persistence)
│   └── utils/              # Utility modules
│       ├── cache.py        # TTL cache for search results
│       └── units.py        # Unit normalization helpers
├── api/                    # FastAPI application
│   ├── main.py             # FastAPI app and endpoints
│   ├── schemas.py          # Pydantic request/response schemas
│   ├── config.py           # Configuration management
│   └── routers/            # API routers
│       ├── __init__.py
│       └── analytics.py    # Analytics endpoints router
├── streamlit_app/          # Streamlit pilot UI application
│   ├── app.py              # Main Streamlit entrypoint
│   ├── pages/              # Multi-page Streamlit app pages
│   ├── ui/                 # UI styling and components
│   └── utils/              # Frontend utilities
├── sandbox/                # Manual testing scripts
├── tests/                  # Test suite
├── render.yaml             # Render deployment configuration
└── requirements.txt        # Python dependencies
```

## Local Development

This guide covers running the backend (FastAPI) and pilot UI (Streamlit) locally for development.

### Prerequisites

- Python 3.10 or higher
- Virtual environment manager (conda or venv)

### 1. Create and Activate Virtual Environment

**Using conda:**
```bash
conda create -n supermarkt-env python=3.10
conda activate supermarkt-env
```

**Using venv:**
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Recommended: VS Code Multi-Root Workspace

To work with both repositories (`nl-grocery-aggregator` and `smartbite-mobile-ui`) simultaneously, we recommend setting up a VS Code Multi-Root Workspace. This gives Cursor (or VS Code) full context across both repos while keeping them separate.

**Steps:**

1. **Open VS Code/Cursor**
2. **File → Add Folder to Workspace...**
   - Add the `nl-grocery-aggregator` folder (this repository)
   - Add the `smartbite-mobile-ui` folder (private repository)
3. **File → Save Workspace As...**
   - Save as `SmartBite.code-workspace` (or any name you prefer)
   - Save it in a convenient location (e.g., parent directory containing both repos)

**Benefits:**
- Lets Cursor see backend schemas + frontend types while keeping repos separate
- Full codebase context for AI assistance across both repos
- Easy navigation between backend and frontend code
- Unified search across both repositories
- Separate Git histories maintained

**Cursor Tip:** Use `@nl-grocery-aggregator` and `@smartbite-mobile-ui` in prompts to scope your requests to specific repositories.

> **Note**: The `.code-workspace` file is optional and typically not committed to version control. Each repository maintains its own `.gitignore` and version history.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

The project uses `.env` file for local development. Environment variables are automatically loaded by `api.config` module when the application starts.

**Step 1: Copy the example file**
```bash
# Copy .env.example to .env (if it exists, otherwise create it manually)
# On Windows PowerShell:
Copy-Item .env.example .env
# On macOS/Linux:
cp .env.example .env
```

**Step 2: Fill in your credentials**

Edit `.env` file at the project root and add your actual API tokens and credentials:

```env
# Apify Configuration (required for AH, Jumbo, and Dirk connectors)
APIFY_TOKEN=your_apify_token_here
APIFY_AH_ACTOR_ID=harvestedge/my-actor
APIFY_JUMBO_ACTOR_ID=harvestedge/jumbo-supermarket-scraper
APIFY_DIRK_ACTOR_ID=harvestedge/dirk-supermarket-scraper

# Picnic Configuration (required for Picnic connector)
PICNIC_USERNAME=your_email@example.com
PICNIC_PASSWORD=your_password_here
PICNIC_COUNTRY_CODE=NL

# Backend URL (for Streamlit frontend - points to local backend by default)
BACKEND_URL=http://localhost:8000

# OpenAI API Key (optional - for AI Health Coach feature)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration (optional - enables Postgres persistence)
DATABASE_URL=postgresql://user:password@localhost:5432/nl_grocery_aggregator

# CORS Configuration (optional - for frontend API access)
# Comma-separated list of allowed origins (e.g., for mobile UI or custom frontend)
# If not set, defaults to: http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
# Example: CORS_ORIGINS=http://localhost:3000,https://myapp.example.com
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
```

**Important:** 
- The `.env` file is automatically loaded by `api.config` when importing `api.main` or `streamlit_app.app`.
- Never commit `.env` to version control (it contains secrets).
- For production on Render, environment variables are set in the Render dashboard (not via .env file).

#### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APIFY_TOKEN` | Yes* | - | Apify API token for AH, Jumbo, and Dirk connectors |
| `APIFY_AH_ACTOR_ID` | No | `harvestedge/my-actor` | Apify actor ID for Albert Heijn |
| `APIFY_JUMBO_ACTOR_ID` | No | `harvestedge/jumbo-supermarket-scraper` | Apify actor ID for Jumbo |
| `APIFY_DIRK_ACTOR_ID` | No | `harvestedge/dirk-supermarket-scraper` | Apify actor ID for Dirk |
| `PICNIC_USERNAME` | Yes* | - | Picnic account email/username |
| `PICNIC_PASSWORD` | Yes* | - | Picnic account password |
| `PICNIC_COUNTRY_CODE` | No | `NL` | Picnic country code |
| `BACKEND_URL` | No | `http://localhost:8000` | Backend API URL (used by Streamlit frontend) |
| `OPENAI_API_KEY` | No | - | OpenAI API key for AI Health Coach feature (optional) |
| `DATABASE_URL` | No | - | PostgreSQL connection string for persistent storage |
| `CORS_ORIGINS` | No | `http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of allowed CORS origins for API access (e.g., for mobile UI) |

*Required only if you want to use the corresponding retailer. You can use the API with just one retailer if desired.

### 4. Running the Backend (FastAPI)

Start the FastAPI server locally:

```bash
uvicorn api.main:app --reload --port 8000
```

The `--reload` flag enables auto-reload on code changes (development only).

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Note:** The `api.config` module automatically loads `.env` when `api.main` is imported, so all environment variables will be available to connectors.

### 5. Running the Pilot UI (Streamlit)

In a **separate terminal** (with the same virtual environment activated):

```bash
streamlit run streamlit_app/app.py
```

The Streamlit app will open in your browser at `http://localhost:8501`.

**Note:**
- The Streamlit app also imports `api.config`, so `.env` is loaded automatically.
- The `utils/api_client.get_backend_url()` function will use `BACKEND_URL` from `.env` (defaults to `http://localhost:8000`).
- If the backend is not running, the frontend will show connection errors in the UI.

### 6. Testing the End-to-End Flow

1. **Start the backend** in one terminal:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

2. **Start the Streamlit UI** in another terminal:
   ```bash
   streamlit run streamlit_app/app.py
   ```

3. **Test the search flow:**
   - Open the Streamlit app in your browser (usually opens automatically at `http://localhost:8501`)
   - Navigate to "Search & Compare" page from the sidebar
   - Search for a common product like "melk" (milk in Dutch)
   - Select all retailers (Albert Heijn, Jumbo, Picnic, Dirk)
   - Click "Search"
   - You should see product results with prices, health tags, and retailer information

4. **Check backend logs** in the terminal where uvicorn is running:
   - You should see structured logging output showing search request parameters, connector results counts, and aggregated response size

### Troubleshooting

**"APIFY_TOKEN is not set" error:**
- Ensure `.env` file exists at the project root
- Verify `APIFY_TOKEN=your_token` is in the `.env` file
- Check that `api.config` is being imported (it should be imported in `api/main.py`)

**"Could not connect to backend" in Streamlit:**
- Verify backend is running on `http://localhost:8000`
- Check `BACKEND_URL` in `.env` matches the backend URL
- Try accessing `http://localhost:8000/docs` directly in your browser

**Empty search results:**
- Check backend terminal logs for connector errors
- Verify API tokens are valid (Apify token for AH/Jumbo/Dirk, Picnic credentials)
- Some retailers may require valid accounts/API access

## API Endpoints

### Health Check

Check backend health status and uptime:

```bash
curl "http://127.0.0.1:8000/health"
```

**Response:**
```json
{
  "status": "ok",
  "name": "NL Grocery Aggregator API",
  "version": "1.0.0",
  "description": "Backend API for aggregating grocery products from Albert Heijn, Jumbo, Picnic, and Dirk",
  "uptime_seconds": 12345
}
```

### Search Products

Search for products across multiple retailers:

```bash
# Basic search
curl "http://127.0.0.1:8000/search?q=milk&retailers=ah,jumbo,picnic,dirk"

# Filter by specific retailer
curl "http://127.0.0.1:8000/search?q=cola&retailers=ah"

# Sort by price and filter healthy products
curl "http://127.0.0.1:8000/search?q=banana&retailers=ah,jumbo,dirk&sort_by=price&health_filter=healthy"
```

**Query Parameters:**
- `q` (required): Search query string
- `retailers` (optional): Comma-separated list of retailers (`ah`, `jumbo`, `picnic`, `dirk`). Default: `picnic,ah,jumbo` (dirk is supported when enabled)
- `size` (optional): Results per retailer (1-50). Default: `10`
- `page` (optional): Page number (0-indexed). Default: `0`
- `sort_by` (optional): Sort criterion (`price`, `retailer`, `health`). Default: `price`
- `health_filter` (optional): Filter by health tag (`healthy`, `unhealthy`). Default: `None`

### Shopping Cart

**Add item to cart:**
```bash
curl -X POST "http://127.0.0.1:8000/cart/add" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: user123" \
  -d '{
    "retailer": "ah",
    "product_id": "12345",
    "name": "Melk Halfvol",
    "price_eur": 1.99,
    "quantity": 2
  }'
```

**View cart:**
```bash
curl "http://127.0.0.1:8000/cart/view" \
  -H "X-Session-ID: user123"
```

**Remove item from cart:**
```bash
curl -X POST "http://127.0.0.1:8000/cart/remove?retailer=ah&product_id=12345&qty=1" \
  -H "X-Session-ID: user123"
```

### Basket Savings

**Find cheaper alternatives for basket items:**
```bash
curl "http://127.0.0.1:8000/basket/savings" \
  -H "X-Session-ID: user123"
```

### Saved Baskets/Templates

**List saved templates:**
```bash
curl "http://127.0.0.1:8000/api/basket/templates" \
  -H "X-Session-ID: user123"
```

**Save current basket as template:**
```bash
curl -X POST "http://127.0.0.1:8000/api/basket/templates" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: user123" \
  -d '{"name": "Weekly groceries"}'
```

### Analytics Endpoints

**Get recent events:**
```bash
curl "http://127.0.0.1:8000/analytics/events/recent?limit=100"
```

**Get event type counts:**
```bash
curl "http://127.0.0.1:8000/analytics/events/counts?since_hours=24"
```

**Query Parameters:**
- `/analytics/events/recent`: `limit` (optional, 1-1000, default: 100)
- `/analytics/events/counts`: `since_hours` (optional, 1-168, default: 24)

**Note:** These endpoints always return a valid response, even when the database is disabled. The `db_enabled` field indicates whether database persistence is active.

For complete API documentation, visit `http://localhost:8000/docs` when the backend is running.

## Production Deployment

> 📖 **Detailed deployment instructions**: See [`DEPLOYMENT_RUNBOOK.md`](DEPLOYMENT_RUNBOOK.md) for step-by-step deployment guide.

The backend and Streamlit UI are deployed on Render using `render.yaml`. The mobile UI is deployed as a separate static site.

### Quick Reference: Environment Variables

#### Backend Service (Required)
- `APIFY_TOKEN` - Apify API token for scraping
- `PICNIC_USERNAME` - Picnic account email
- `PICNIC_PASSWORD` - Picnic account password
- `CORS_ALLOWED_ORIGINS` - Comma-separated frontend URLs (e.g., `https://frontend.onrender.com,https://mobile-ui.onrender.com`)

#### Backend Service (Optional)
- `DATABASE_URL` - Postgres connection string (for analytics persistence)

#### Streamlit Service (Required)
- `BACKEND_URL` - Backend API URL (e.g., `https://nl-grocery-aggregator.onrender.com`)

#### Mobile UI Static Site (Required, Build-time)
- `VITE_API_BASE_URL` - Backend API URL (e.g., `https://nl-grocery-aggregator.onrender.com`)

**CORS Configuration:**
- Backend reads `CORS_ALLOWED_ORIGINS` (or `CORS_ORIGINS` for backward compatibility)
- If not set, defaults to local development origins (`localhost:3000`, `localhost:5173`, etc.)
- **For production**: Set `CORS_ALLOWED_ORIGINS` to your actual frontend URLs (comma-separated, no trailing slashes)
- Backend logs allowed origins on startup (check logs after deployment)

**Important**: 
- Set all secrets in Render dashboard (never commit actual values to `render.yaml`)
- After deploying mobile UI, update backend `CORS_ALLOWED_ORIGINS` to include the mobile UI URL
- `.env` file is **not** used on Render; platform environment variables are used instead

For complete deployment instructions, troubleshooting, and verification steps, see [`DEPLOYMENT_RUNBOOK.md`](DEPLOYMENT_RUNBOOK.md).

### Render Configuration

A `render.yaml` file is included in the repository root for easy deployment. It contains the service configuration and placeholder environment variables. When deploying:

1. Connect your repository to Render
2. Render will automatically detect the `render.yaml` file
3. Set the required environment variables in the Render dashboard (mark secrets as `sync: false`)
4. Deploy!

### Build and Start Commands

**Backend Build Command:**
```bash
pip install -r requirements.txt
```

**Backend Start Command:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 10000
```

## Running Tests

Run the full test suite:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run specific test file:

```bash
pytest tests/test_search.py
```

## Architecture Notes

### Connectors

Each retailer has a dedicated connector that:
- Implements the `BaseConnector` interface
- Normalizes retailer-specific data into a unified format
- Handles authentication and API calls
- Provides error handling and retry logic

### Data Flow

1. **Search Request** → FastAPI endpoint receives query
2. **Connector Instantiation** → Connectors are created for requested retailers
3. **Parallel Search** → Each connector searches its retailer
4. **Normalization** → Results are normalized to unified format
5. **Health Tagging** → Products are tagged as healthy/unhealthy/neutral
6. **Grouping & Marking** → Products with same name are grouped, cheapest is marked
7. **Filtering & Sorting** → Results are filtered and sorted according to parameters
8. **Response** → Normalized products returned as JSON

## Limitations

- **Storage**: 
  - Cart data and templates use in-memory storage by default (lost on server restart)
  - Optional Postgres persistence available when `DATABASE_URL` is set
  - Event logging uses Postgres when available, falls back to file-based logging (`events.log`)
- **Session-based**: Templates and carts are tied to session IDs (no user accounts yet)
- **No Authentication**: API endpoints do not require authentication (development only)
- **Rate Limiting**: No rate limiting implemented (be respectful of retailer APIs)
- **Delivery Slots**: Only Picnic delivery slots are currently implemented
- **Analytics**: Analytics dashboard is for internal/demo use only; not production-grade

## Credits & Attributions

### Images

All hero images and recipe images used in this project are sourced from [Unsplash](https://unsplash.com/) and are provided under the [Unsplash License](https://unsplash.com/license), which allows free use for commercial and non-commercial purposes.

We are grateful to the Unsplash community for providing high-quality, freely usable images that enhance the visual appeal of this application.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Important Note**: While this project is open source, be aware that it interfaces with retailer APIs. Respect retailer terms of service and do not deploy to production without proper legal review.

## Contributing

This is a learning project. Contributions, suggestions, and improvements are welcome!
