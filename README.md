# NL Grocery Aggregator

A full-stack application that aggregates grocery product search results from multiple Dutch supermarkets (Albert Heijn, Jumbo, Picnic, and Dirk). The project includes a FastAPI backend service and a modern Streamlit web frontend with card-based layouts, hero images, and a consistent brand design, providing a unified interface to search, compare, and manage shopping carts across retailers.

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

### Frontend (Streamlit)
- **Modern UI Design**: Card-based layouts, hero images, and consistent styling inspired by freasy.nl
- **Search & Compare**: Interactive product search with filters, health tags, and price comparison
  - Two-column layout with side image cards
  - Results summary with retailer highlights
- **My Basket**: Comprehensive shopping cart management with:
  - Dashboard-style two-column layout (basket table + side summaries)
  - **Top Metrics Band**: Items count, total cost, retailers, healthy items, and weekly budget usage
  - **Weekly Budget Projection**: See how much of your typical weekly budget you're using (household-aware)
  - Quantity updates and item removal
  - **Smart Suggestions**: Automatic suggestions for cheaper or healthier alternatives (up to 3 shown)
  - **Savings Finder**: Find cheaper alternatives for items in your basket
  - **Saved Baskets/Templates**: Save current basket as a template and reuse it later
  - Retailer totals breakdown
  - Session persistence across pages
- **Health Insights**: Basket health analytics showing health tag distribution and spending by category
  - Two-column layout with charts on left, summary and swaps on right
  - Visual health breakdown with metrics
- **Recipes & Ideas**: Recipe collection with one-click ingredient addition to basket
  - Filters on left, recipe cards grid on right
  - Recipe cards with images, tags, and expandable details
  - Automatically finds the healthiest available products for each ingredient
  - Falls back to cheapest option if health scores are tied
  - Best-effort matching: adds what it can find, reports missing ingredients
- **Analytics Dashboard** (Internal): Internal analytics dashboard for event visualization
  - Event counts visualization with bar charts
  - Recent events table with timestamp, event type, session ID, and payload
  - Time window selection (6 hours to 7 days)
  - Gracefully handles database disabled state
  - Shows backend and database status
- **System Status**: Backend health monitoring and API documentation links
- **Brand Footer**: Consistent footer across all pages with brand colors and information

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
│   ├── db.py               # Database layer (Postgres persistence for carts, price history, events)
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
├── streamlit_app/          # Streamlit frontend application
│   ├── app.py              # Main Streamlit entrypoint
│   ├── pages/              # Multi-page Streamlit app pages
│   │   ├── 01_🏠_Home.py
│   │   ├── 02_🛒_Search_and_Compare.py
│   │   ├── 03_🧺_My_Basket.py
│   │   ├── 04_📊_Health_Insights.py
│   │   ├── 05_🍳_Recipes.py
│   │   ├── 06_📈_Analytics.py
│   │   └── 99_🔧_System_Status.py
│   ├── assets/             # Hero images and marketing assets
│   │   └── *.jpg           # Healthy food images (Unsplash)
│   ├── ui/                 # UI styling and components
│   │   └── style.py         # Global CSS, hero banners, image cards, footer
│   ├── utils/              # Frontend utilities
│   │   ├── api_client.py   # Backend API client
│   │   ├── session.py      # Session management
│   │   ├── recipes_data.py # Recipe data module
│   │   ├── retailers.py    # Retailer configuration and mappings
│   │   ├── profile.py      # Household profile management
│   │   ├── sponsored_data.py # Sponsored deals data
│   │   ├── state.py        # Session state helpers
│   │   └── ui_components.py # Reusable UI components
│   └── theme/              # Streamlit theme configuration
├── sandbox/                # Manual testing scripts
├── tests/                  # Test suite
└── requirements.txt        # Python dependencies
```

## Local Development

This guide covers running both the backend (FastAPI) and frontend (Streamlit) locally for development.

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
# Note: On Render, set BACKEND_URL to your backend service URL (e.g., https://nl-grocery-aggregator.onrender.com)
# Trailing slashes are automatically handled

# OpenAI API Key (optional - for AI Health Coach feature in Health Insights page)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration (optional - enables Postgres persistence for carts, price history, and events)
# When set, cart data, price history, and event analytics are persisted to Postgres
# When not set, falls back to in-memory storage (carts), JSONL files (price history, events)
DATABASE_URL=postgresql://user:password@localhost:5432/nl_grocery_aggregator
# Example for Render: DATABASE_URL=postgresql://user:pass@dpg-xxx.oregon-postgres.render.com/dbname
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
| `BACKEND_URL` | No | `http://localhost:8000` | Backend API URL (used by Streamlit frontend for all API calls, including `/health` endpoint) |
| `OPENAI_API_KEY` | No | - | OpenAI API key for AI Health Coach feature (optional) |
| `DATABASE_URL` | No | - | PostgreSQL connection string for persistent storage (carts, price history, events). When not set, uses in-memory/file-based fallback |

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

### 5. Running the Frontend (Streamlit)

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

2. **Start the frontend** in another terminal:
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
   - Select some products using the checkboxes and click "Add Selected Item(s) to Basket"

4. **Test the basket flow:**
   - Navigate to "My Basket" page
   - Verify your selected items appear in the basket
   - Try editing quantities or removing items
   - The basket persists across page navigations (same session)
   
5. **Test Savings Finder:**
   - With items in your basket, click "🔎 Check for savings opportunities"
   - Review any cheaper alternatives found
   - Apply a swap to replace an item with a cheaper alternative
   
6. **Test Saved Baskets/Templates:**
   - With items in your basket, save it as a template (e.g., "Weekly groceries")
   - Clear or modify your basket
   - Apply the saved template to restore your original basket

7. **Test Health Insights:**
   - Navigate to "Health Insights" page
   - View health metrics based on items in your basket
   - See health tag distribution and spending by category

8. **Test Recipes & Ideas:**
   - Navigate to "Recipes & Ideas" page
   - Expand a recipe to see ingredients
   - Click "🛒 Add Ingredients to Basket"
   - The app will automatically find the healthiest products for each ingredient
   - Check "My Basket" to see the added items

9. **Check backend logs** in the terminal where uvicorn is running:
   - You should see structured logging output showing:
     - Search request parameters
     - Connector results counts (raw products from each retailer)
     - Aggregated response size
   
10. **Check event logs** (optional):
    - Events are logged to `events.log` in the project root
    - Each line is a JSON object with event type, session_id, and payload
    - Events include: search_performed, cart_items_added, savings_analysis_run, template_saved, etc.

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

## Running the API Only

If you only want to run the backend API without the Streamlit frontend:

```bash
uvicorn api.main:app --reload
```

The API will be available at http://127.0.0.1:8000

## Frontend Features

### Search & Compare
- **Product Search**: Search across multiple retailers with a single query
- **Advanced Filters**: Filter by retailer, health category, and sort options
- **Two-Column Layout**: Main results on left, side image card on right
- **Results Summary**: Product count, retailers used, and highlight columns
- **Unified Comparison Table**: View all products in one table with comparison columns
- **Add to Basket**: Select multiple products and add them to your basket with one click
- **Form State Persistence**: Search filters persist when navigating between pages

### My Basket
- **Dashboard Layout**: Two-column layout with basket table centered and side summaries
- **Top Metrics Band**: Quick overview of items, total cost, retailers, healthy items count, and weekly budget usage
  - **Weekly Budget Projection**: Shows percentage of typical weekly budget used based on household profile
  - Budget hint displayed below metrics when household profile is set
- **Shopping Cart Management**: 
  - View, manage, and remove items from your basket
  - Edit quantities directly in the table
  - Remove items via checkboxes or by setting quantity to 0
  - Update basket button to apply all changes at once
- **Smart Suggestions** (new):
  - Automatically analyzes basket items to find cheaper or healthier alternatives
  - Shows up to 3 suggestions in the side column
  - Each suggestion displays:
    - Icon (💶 for cheaper alternatives, 🥦 for healthier alternatives)
    - Current item → Alternative item swap
    - Estimated savings amount
    - Health improvement delta (if applicable)
  - Suggestions are computed in real-time using the same savings logic as Savings Finder
  - Gracefully handles errors (suggestions are a nice-to-have feature)
- **Savings Finder**:
  - Analyze current basket items to find cheaper alternatives
  - See potential savings amount
  - Apply swaps with one click (replaces current item with cheaper alternative)
  - Uses same product comparison logic as search
- **Saved Baskets/Templates**:
  - Save current basket as a named template (e.g., "Weekly groceries")
  - List all saved templates with creation date and item count
  - Apply a template to replace current basket contents
  - Delete templates you no longer need
  - Templates are session-based (tied to your browser session)
- **Session Persistence**: Basket persists across page navigations within the same browser session
- **Cart Summary**: See total items, total price, and retailer breakdown
- **Side Column**: Smart suggestions, retailer totals, savings finder, templates, health summary, and NLGA Plus info

### Health Insights
- **Basket Health Score (0-100)**: Color-coded health rating displayed at the top
  - Excellent (80-100): 🟢 Green
  - Good (60-79): 🟡 Yellow
  - Needs improvement (40-59): 🟠 Orange
  - Unhealthy (0-39): 🔴 Red
  - Personalized tips based on score
- **Two-Column Layout**: Charts and tables on left, summary and swaps on right
- **Top Metrics Band**: Quick overview of healthy, neutral, and less healthy items
- **Visual Breakdown**: 
  - Bar chart showing health tag distribution
  - **Donut chart** with percentage labels showing healthy/neutral/less healthy proportions
  - **Basket health insights** panel with personalized recommendations based on proportions
- **Health Tag Distribution**: Detailed breakdown of healthy vs. less healthy items
- **Spending by Category**: See how much you're spending on healthy vs. unhealthy items
- **Health-based Swap Suggestions**: 
  - Automatically identifies items that could be swapped for healthier alternatives
  - Shows health score improvement and price impact for each suggestion
  - Displays top 5 suggestions sorted by health improvement
  - Uses existing savings logic to find better alternatives
- **AI Health Coach** (optional): Get AI-generated insights about your basket (requires `OPENAI_API_KEY`)

### Recipes & Ideas
- **Meal Planning Hub**: Transform recipes into a weekly meal plan with integrated shopping and health tracking
- **Modern 3-Column Grid Layout**: Beautiful image-based recipe cards in a 3-column grid (up to 9 recipes per view)
- **Recipe Images**: Each recipe displays a curated image from the assets directory
- **Category Chip Bar**: Quick filter buttons at the top (All, Quick, High protein, Vegetarian, Budget-friendly, Family, Healthy)
  - Chips override the dropdown tag filter when selected
  - Active chip shows visual indicator (● prefix)
- **Recipe Cards**: Rich card display with:
  - Recipe image at the top
  - Title and description
  - Meta information (meal type, difficulty, prep time) and tags
  - **Estimated price** in euros (€X.XX format) displayed alongside planned badge in a commerce-style row
  - **Health claim badges** (beige pills showing claims like "High protein", "200g+ vegetables")
    - Limited to 3 claims per card for clean display
    - Hover tooltips show full claim text
  - Household-aware serving tips
  - Expandable ingredients & instructions section
  - "Plan this recipe" button for meal planning
- **Planned Recipes Summary Panel**: Right-side panel showing your weekly meal plan
  - Displays count and list of all planned recipes
  - Shows recipe title, price, prep time, and meal type for each planned recipe
  - Hints linking to **My Basket** (for assembling ingredients) and **Health Insights** (for analyzing grocery health)
  - "Clear all planned recipes" button to reset your meal plan (session-scoped)
- **Planned Badge**: Visual indicator (green badge) on recipes you've planned for the week
  - Displayed in bottom row alongside price (commerce-style layout)
  - Persists across page navigations within the same session
  - Track which recipes you've already planned
- **Filters & Search**: Left sidebar with:
  - Text search input
  - Meal type dropdown filter
  - Dietary preference/tag dropdown filter
  - All filters work together seamlessly
- **Recipe Collection**: Browse healthy recipes organized by meal type and tags
- **One-Click Ingredient Addition**: Add all recipe ingredients to basket with a single click
- **Smart Product Selection**: Automatically selects the healthiest available product for each ingredient
  - Prioritizes products tagged as "healthy"
  - Falls back to cheapest option if health scores are tied
  - Best-effort matching: adds what can be found, reports missing ingredients
- **Recipe Analytics**: 
  - Tracks recipe views for analytics (logged when recipe details are expanded)
  - Tracks recipe planning events (logged when "Plan this recipe" is clicked)
  - All analytics events integrate with the Analytics Dashboard
- **Household-Aware**: Serving suggestions based on your household profile (single, couple, family, student)

### Analytics Dashboard
- **Event Counts Visualization**: Bar chart showing event types and counts
  - Time window selection (6, 12, 24, 48, 72, or 168 hours)
  - Sorted by count (most frequent events first)
  - Table view for detailed counts
- **Recent Events Table**: View most recent analytics events
  - Limit selection (50, 100, 200, or 500 events)
  - Displays timestamp, event type, session ID, and payload
  - Payload truncated for readability
- **Database Status**: Shows backend and database connection status
  - Clear indication when database persistence is enabled or disabled
  - Graceful degradation with informative messages
- **Internal Use Only**: Clearly marked as demo/experimental feature

### System Status
- **Backend Health**: Monitor backend API status and connectivity via `/health` endpoint
  - Shows real-time backend status (online/offline) in sidebar and System Status page
  - Displays API metadata, version, and uptime information
  - Gracefully handles connection errors and timeouts
- **API Documentation**: Quick access to API documentation
- **System Diagnostics**: View system details and planned diagnostic features
- **Footer Image**: Small marketing image at the bottom

### UI/UX Features
- **Hero Images**: Healthy food images from `streamlit_app/assets/` displayed across pages
- **Image Cards**: Smaller marketing-style images in side columns and cards
- **Brand Footer**: Consistent footer across all pages with brand colors and information
- **Card-Based Layouts**: Modern card-based design with rounded corners and shadows
- **Responsive Design**: Optimized layouts that work well on different screen sizes
- **Consistent Styling**: Global CSS with Nunito font, brand colors, and consistent spacing

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

This endpoint is used by the frontend System Status page to monitor backend availability. Always returns `200 OK` if the endpoint is reachable.

### Search Products

Search for products across multiple retailers:

```bash
# Basic search
curl "http://127.0.0.1:8000/search?q=milk&retailers=ah,jumbo,picnic,dirk"

# Filter by specific retailer
curl "http://127.0.0.1:8000/search?q=cola&retailers=ah"

# Sort by price and filter healthy products
curl "http://127.0.0.1:8000/search?q=banana&retailers=ah,jumbo,dirk&sort_by=price&health_filter=healthy"

# Pagination
curl "http://127.0.0.1:8000/search?q=bread&retailers=ah&size=10&page=1"
```

**Query Parameters:**
- `q` (required): Search query string
- `retailers` (optional): Comma-separated list of retailers (`ah`, `jumbo`, `picnic`, `dirk`). Default: `picnic,ah,jumbo,dirk`
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

Returns potential savings and suggestions for cheaper alternatives.

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

**Apply a template:**
```bash
curl -X POST "http://127.0.0.1:8000/api/basket/templates/{template_id}/apply" \
  -H "X-Session-ID: user123"
```

**Delete a template:**
```bash
curl -X DELETE "http://127.0.0.1:8000/api/basket/templates/{template_id}" \
  -H "X-Session-ID: user123"
```

### Delivery Slots

Get available delivery slots for a retailer:

```bash
curl "http://127.0.0.1:8000/delivery/slots?retailer=picnic"
```

### Analytics Endpoints

**Get recent events:**
```bash
curl "http://127.0.0.1:8000/analytics/events/recent?limit=100"
```

**Response:**
```json
{
  "db_enabled": true,
  "events": [
    {
      "ts": "2024-01-15T10:30:00.123456",
      "event_type": "search_performed",
      "session_id": "abc123",
      "payload": {
        "query": "melk",
        "retailers": ["ah", "jumbo"],
        "result_count": 10
      }
    }
  ]
}
```

**Get event type counts:**
```bash
curl "http://127.0.0.1:8000/analytics/events/counts?since_hours=24"
```

**Response:**
```json
{
  "db_enabled": true,
  "since_hours": 24,
  "counts": {
    "search_performed": 120,
    "cart_item_added": 40,
    "cart_item_removed": 5,
    "swap_clicked": 3,
    "recipe_viewed": 8
  }
}
```

**Query Parameters:**
- `/analytics/events/recent`:
  - `limit` (optional): Maximum number of events to return (1-1000). Default: `100`
- `/analytics/events/counts`:
  - `since_hours` (optional): Number of hours to look back (1-168). Default: `24`

**Note:** These endpoints always return a valid response, even when the database is disabled. The `db_enabled` field indicates whether database persistence is active.

## Production Deployment

For production/staging, the backend is deployed on Render using `render.yaml`. 

**Environment Variables on Render:**
- Set all required environment variables in the Render dashboard (APIFY_TOKEN, PICNIC_USERNAME, PICNIC_PASSWORD, etc.)
- For the Streamlit frontend service, set `BACKEND_URL` to your backend service URL (e.g., `https://nl-grocery-aggregator.onrender.com`)
  - This allows the frontend to connect to the backend API and use the `/health` endpoint for status checks
  - Trailing slashes are automatically removed, so both formats work
- The `.env` file is **not** used on Render; platform environment variables are used instead.

See the [Deployment](#deployment) section below for detailed Render setup instructions.

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

## Deployment

This app is designed to be deployed on Render as a Python Web Service.

### Build and Start Commands

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 10000
```

Note: The backend service uses port 10000 as configured in `render.yaml`. Render will automatically route traffic to this port.

### Required Environment Variables

The following environment variables must be configured in your Render service settings:

**Apify Configuration** (required for AH, Jumbo, and Dirk connectors):
- `APIFY_TOKEN` - Apify API token (required)
- `APIFY_AH_ACTOR_ID` - Apify actor ID for Albert Heijn (default: `harvestedge/my-actor`)
- `APIFY_JUMBO_ACTOR_ID` - Apify actor ID for Jumbo (default: `harvestedge/jumbo-supermarket-scraper`)
- `APIFY_DIRK_ACTOR_ID` - Apify actor ID for Dirk (default: `harvestedge/dirk-supermarket-scraper`)

**Picnic Configuration** (required for Picnic connector):
- `PICNIC_USERNAME` - Picnic account email/username (required)
- `PICNIC_PASSWORD` - Picnic account password (required)
- `PICNIC_COUNTRY_CODE` - Picnic country code (default: `NL`)

**Python Version:**
- `PYTHON_VERSION` - Python version (default: `3.10.19`)

### Render Configuration

A `render.yaml` file is included in the repository root for easy deployment. It contains the service configuration and placeholder environment variables. When deploying:

1. Connect your repository to Render
2. Render will automatically detect the `render.yaml` file
3. Set the required environment variables in the Render dashboard (mark secrets as `sync: false`)
4. Deploy!

### Local Testing

Before deploying, verify the production start command works locally:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 10000
```

The API should be accessible at `http://localhost:10000`.

## Development

### Sandbox Scripts

Test individual connectors manually:

```bash
# Test Picnic connector
python -m sandbox.sandbox_picnic

# Test AH connector
python -m sandbox.sandbox_ah_connector

# Test Jumbo connector
python -m sandbox.sandbox_jumbo

# Test Dirk connector (if sandbox script exists)
# python -m sandbox.sandbox_dirk

# Test aggregated search
python -m sandbox.sandbox_search
```

### Code Quality

The project follows these conventions:
- Type hints on all functions
- Pydantic models for data validation
- Comprehensive docstrings
- Error handling with clear messages
- Test coverage for core functionality

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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Important Note**: While this project is open source, be aware that it interfaces with retailer APIs. Respect retailer terms of service and do not deploy to production without proper legal review.

## Contributing

This is a learning project. Contributions, suggestions, and improvements are welcome!
