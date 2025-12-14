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
- **Modern UI System**: Modular UI architecture with reusable components
  - `ui/layout.py`: Page headers, KPI rows, sections, and card containers
  - `ui/styles.py`: Global CSS styling with tightened spacing and consistent design
  - `ui/feedback.py`: Standardized error, empty state, and loading utilities
- **Search & Compare**: Interactive product search with filters, health tags, and price comparison
  - Modern minimalist header with basket quick access
  - Compact product comparison table with inline add buttons
  - Standardized error and empty states
  - Safe caching for search results
- **My Basket**: Comprehensive shopping cart management with:
  - Dashboard-style layout with KPI metrics row
  - **Primary Action Bar**: Health check, Find savings, Export list buttons
  - Quantity updates and item removal
  - **Smart Suggestions**: Automatic suggestions for cheaper or healthier alternatives (up to 3 shown)
  - **Savings Finder**: Find cheaper alternatives for items in your basket
  - **Export List**: Export shopping list as .txt or .csv with improved UX flow
  - **Saved Baskets/Templates**: Save current basket as a template and reuse it later
  - Retailer totals breakdown
  - Session persistence across pages
- **Health Insights**: Minimalist dashboard for basket health analytics
  - Modern header with basket quick access
  - KPI metrics row (Health score, % healthy, Items to improve, Variety)
  - Primary visual: Donut chart with percentage labels showing basket composition
  - Key takeaways card with 3 actionable insights
  - Top categories stacked bar chart (conditional)
  - Health-based swap suggestions in expander
  - Safe caching for health aggregates computation
- **Recipes**: Modern recipe collection with compact card grid
  - Modern header with basket quick access
  - Compact recipe cards with title, summary, tags, and action buttons
  - "Add ingredients" button for one-click basket addition
  - Expandable details (ingredients & steps) for each recipe
  - Filters on left, 3-column recipe grid on right
  - Safe caching for recipe filtering (5-minute TTL)
  - Standardized empty states
- **Analytics Dashboard** (Internal): Internal analytics dashboard for event visualization
  - Event counts visualization with bar charts
  - Summary metrics row (total events, searches, cart adds, swaps)
  - Recent events table with event type filtering
  - CSV download for recent events
  - Time window selection (6 hours to 7 days)
  - Gracefully handles database disabled state
  - Shows backend and database status
  - "Last updated" timestamp
- **System Status**: Backend health monitoring and API documentation links
  - Demo controls expander: Reset session, Load demo basket, Clear cache
  - Backend and database status monitoring
- **Consistent UX**: 
  - Basket quick access button in page headers (Search, Health Insights, Recipes)
  - Standardized button labels across all pages
  - Consistent error/empty/loading states
  - Tightened spacing for modern, compact feel
  - No decorative images (clean, focused design)

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
│   │   ├── styles.py        # Global CSS styling
│   │   ├── layout.py        # Page headers, KPI rows, sections, cards
│   │   ├── feedback.py      # Error, empty state, and loading utilities
│   │   └── style.py         # Legacy footer and helper functions
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
- **Modern Header**: Minimalist header with basket quick access button showing item count
- **Advanced Filters**: Filter by retailer, health category, and sort options
- **Compact Product Table**: Custom table layout with inline ➕ buttons for adding items
- **Action Bar**: Shows basket count and sort order above the table
- **Unified Comparison Table**: View all products in one table with comparison columns
- **Add to Basket**: Inline ➕ buttons for immediate item addition with toast feedback
- **Standardized Feedback**: Consistent error and empty states
- **Safe Caching**: Search results cached for performance
- **Form State Persistence**: Search filters persist when navigating between pages

### My Basket
- **Dashboard Layout**: Modern dashboard with KPI metrics row and primary action bar
- **KPI Metrics Row**: Items count, total cost, average per item, and savings at a glance
- **Primary Action Bar**: 
  - Health check button (navigates to Health Insights)
  - Find savings button (triggers savings analysis)
  - Export list button (with improved UX flow: spinner → toast → download buttons)
- **Export List**: Premium export experience
  - Click "Export list" → shows spinner → toast notification
  - Download buttons appear immediately (.txt and .csv formats)
  - CSV includes Quantity, Item, Price columns
- **Shopping Cart Management**: 
  - View, manage, and remove items from your basket
  - Edit quantities directly in the table
  - Remove items via checkboxes or by setting quantity to 0
  - Update basket button to apply all changes at once
- **Smart Suggestions**:
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
- **Secondary Actions**: Weekly essentials and delivery services demo in collapsed expanders
- **Session Persistence**: Basket persists across page navigations within the same browser session
- **Cart Summary**: Compact summary card with key metrics and "Continue shopping" button
- **Standardized Empty State**: Friendly empty basket card with action button

### Health Insights
- **Minimalist Dashboard**: Clean, modern dashboard design focused on key metrics
- **Modern Header**: Header with basket quick access button
- **KPI Metrics Row**: Health score, % healthy, Items to improve, Variety score
- **Navigation CTAs**: "Open basket" and "Find savings" buttons
- **Primary Visual**: Donut chart with percentage labels inside segments showing basket composition
- **Key Takeaways Card**: 3 bullet points summarizing:
  - Overall health assessment
  - Main driver category
  - One actionable improvement insight
- **Top Categories Chart**: Stacked bar chart showing category-level health breakdown (conditional)
- **Health-based Swap Suggestions**: Moved into "Improve this basket" expander (collapsed by default)
- **Safe Caching**: Health aggregates computation cached (60-second TTL)
- **Standardized Empty State**: Clean empty basket message with action button
- **Compact Disclaimer**: One-line health insights disclaimer

### Recipes
- **Modern Recipe Grid**: Compact 3-column card grid (up to 9 recipes)
- **Modern Header**: Header with basket quick access button
- **Compact Recipe Cards**: Each card shows:
  - Recipe title (bold)
  - 1-line summary (description, truncated if > 100 chars)
  - Tags as pills (limit 5 tags)
  - "Add ingredients" button
  - Expandable "View ingredients & steps" section
- **Filters & Search**: Left sidebar with text search, meal type, and tag filters
- **Category Chip Bar**: Quick filter buttons at the top
- **Smart Product Selection**: Automatically finds healthiest products for recipe ingredients
  - Prioritizes products tagged as "healthy"
  - Falls back to cheapest option if health scores are tied
  - Best-effort matching: adds what can be found, reports missing ingredients
- **Safe Caching**: Recipe filtering cached (5-minute TTL, includes filter params)
- **Standardized Empty State**: Clean "No recipes found" message
- **Short Caption + Expander**: Concise page description with "How recipes work" expander

### Analytics Dashboard
- **Summary Metrics Row**: Total events, searches, cart adds, swaps at a glance
- **Event Counts Visualization**: Bar chart showing event types and counts
  - Time window selection (6, 12, 24, 48, 72, or 168 hours)
  - Sorted by count (most frequent events first)
  - Table view for detailed counts
- **Recent Events Table**: View most recent analytics events
  - Event type filtering dropdown
  - Limit selection (50, 100, 200, or 500 events)
  - Displays timestamp, event type, session ID, and payload
  - Improved payload formatting (readable, truncated to 200 chars)
  - CSV download button for recent events
- **Last Updated Timestamp**: Dynamic timestamp showing when page data was last refreshed
- **Database Status**: Shows backend and database connection status
  - Clear indication when database persistence is enabled or disabled
  - Graceful degradation with informative messages
- **Internal Use Only**: Clearly marked as demo/experimental feature

### System Status
- **Backend Health**: Monitor backend API status and connectivity via `/health` endpoint
  - Shows real-time backend status (online/offline)
  - Displays API metadata, version, and uptime information
  - Gracefully handles connection errors and timeouts
- **API Documentation**: Quick access to API documentation
- **System Diagnostics**: View system details and planned diagnostic features
- **Demo Controls** (new): Collapsible expander with demo utilities
  - **Reset session**: Clears all search results, basket, swaps, export flags, and session state
  - **Load demo basket**: Populates basket with 4 example items (milk, bread, eggs, fruit)
  - **Clear cache**: Clears all Streamlit cache data
  - All actions show toast feedback

### UI/UX System
- **Modular Architecture**: Reusable UI components (`ui/layout.py`, `ui/styles.py`, `ui/feedback.py`)
- **Consistent Styling**: 
  - Global CSS with Nunito font and tightened spacing
  - Consistent button styling (padding, radius, font weight)
  - Consistent card padding across all pages
- **Standardized Feedback**: 
  - `show_error()` for error messages with optional hints
  - `show_empty_state()` for empty states with action buttons
  - `working_spinner()` context manager for loading states
- **Basket Quick Access**: Basket button in page headers (Search, Health Insights, Recipes)
  - Shows item count when basket has items
  - One-click navigation to basket page
- **Responsive Design**: Optimized layouts that work well on different screen sizes
- **No Decorative Images**: Clean, focused design without unnecessary images

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

## Credits & Attributions

### Images

All hero images and recipe images used in this project are sourced from [Unsplash](https://unsplash.com/) and are provided under the [Unsplash License](https://unsplash.com/license), which allows free use for commercial and non-commercial purposes.

The following photographers' work is featured in the `streamlit_app/assets/` directory:
- [Anh Nguyen](https://unsplash.com/@pwign)
- [Anna Pelzer](https://unsplash.com/@annapelzer)
- [Brooke Lark](https://unsplash.com/@brookelark)
- [Dan Gold](https://unsplash.com/@danielcgold)
- [Davey Gravy](https://unsplash.com/@daveygravy)
- [Ella Olsson](https://unsplash.com/@ellaolsson)
- [Jannis Brandt](https://unsplash.com/@jannisbrandt)
- [Nadine Primeau](https://unsplash.com/@nadineprimeau)
- [Olena Bohovyk](https://unsplash.com/@olenkasanka)
- [Taylor Kiser](https://unsplash.com/@taypaigey)

We are grateful to these photographers and the Unsplash community for providing high-quality, freely usable images that enhance the visual appeal of this application.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Important Note**: While this project is open source, be aware that it interfaces with retailer APIs. Respect retailer terms of service and do not deploy to production without proper legal review.

## Contributing

This is a learning project. Contributions, suggestions, and improvements are welcome!
