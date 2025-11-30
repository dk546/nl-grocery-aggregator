# NL Grocery Aggregator

A full-stack application that aggregates grocery product search results from multiple Dutch supermarkets (Albert Heijn, Jumbo, and Picnic). The project includes a FastAPI backend service and a Streamlit web frontend, providing a unified interface to search, compare, and manage shopping carts across retailers.

## Features

### Backend (FastAPI)
- **Unified Product Search**: Search for products across Albert Heijn, Jumbo, and Picnic in a single API call
- **Normalized Product Schema**: All products are normalized into a consistent format regardless of retailer
- **Health Tagging**: Automatic classification of products as "healthy", "unhealthy", or "neutral"
- **Price Comparison**: Automatically marks the cheapest option for products with the same name
- **Shopping Cart**: In-memory cart management with session-based isolation
- **Delivery Slots**: Retrieve available delivery time slots (currently Picnic only)
- **RESTful API**: Clean FastAPI endpoints with automatic OpenAPI documentation

### Frontend (Streamlit)
- **Search & Compare**: Interactive product search with filters, health tags, and price comparison
- **My Basket**: Shopping cart management with session persistence across pages
- **Health Insights**: Basket health analytics showing health tag distribution and spending by category
- **Recipes & Ideas**: Recipe collection with one-click ingredient addition to basket
  - Automatically finds the healthiest available products for each ingredient
  - Falls back to cheapest option if health scores are tied
  - Best-effort matching: adds what it can find, reports missing ingredients
- **System Status**: Backend health monitoring and API documentation links

## Project Structure

```
nl-grocery-aggregator/
├── aggregator/              # Core aggregator logic
│   ├── connectors/         # Retailer-specific connectors
│   │   ├── base.py         # Base connector abstract class
│   │   ├── ah_connector.py # Albert Heijn connector (Apify-based)
│   │   ├── jumbo_connector.py # Jumbo connector (Apify-based)
│   │   └── picnic_connector.py # Picnic connector (python-picnic-api)
│   ├── cart.py             # Shopping cart management
│   ├── health.py           # Health tagging logic
│   ├── models.py           # Pydantic models for cart
│   └── search.py           # Aggregated search logic
├── api/                    # FastAPI application
│   ├── main.py             # FastAPI app and endpoints
│   ├── schemas.py          # Pydantic request/response schemas
│   └── config.py           # Configuration management
├── streamlit_app/          # Streamlit frontend application
│   ├── app.py              # Main Streamlit entrypoint
│   ├── pages/              # Multi-page Streamlit app pages
│   │   ├── 00_🔧_System_Status.py
│   │   ├── 01_🏠_Home.py
│   │   ├── 02_🛒_Search_and_Compare.py
│   │   ├── 03_🧺_My_Basket.py
│   │   ├── 04_📊_Health_Insights.py
│   │   └── 05_🍳_Recipes.py
│   ├── utils/              # Frontend utilities
│   │   ├── api_client.py   # Backend API client
│   │   ├── session.py      # Session management
│   │   ├── recipes_data.py # Recipe data module
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
# Apify Configuration (required for AH and Jumbo connectors)
APIFY_TOKEN=your_apify_token_here
APIFY_AH_ACTOR_ID=harvestedge/my-actor
APIFY_JUMBO_ACTOR_ID=harvestedge/jumbo-supermarket-scraper

# Picnic Configuration (required for Picnic connector)
PICNIC_USERNAME=your_email@example.com
PICNIC_PASSWORD=your_password_here
PICNIC_COUNTRY_CODE=NL

# Backend URL (for Streamlit frontend - points to local backend by default)
BACKEND_URL=http://localhost:8000

# OpenAI API Key (optional - for AI Health Coach feature in Health Insights page)
OPENAI_API_KEY=your_openai_api_key_here
```

**Important:** 
- The `.env` file is automatically loaded by `api.config` when importing `api.main` or `streamlit_app.app`.
- Never commit `.env` to version control (it contains secrets).
- For production on Render, environment variables are set in the Render dashboard (not via .env file).

#### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APIFY_TOKEN` | Yes* | - | Apify API token for AH and Jumbo connectors |
| `APIFY_AH_ACTOR_ID` | No | `harvestedge/my-actor` | Apify actor ID for Albert Heijn |
| `APIFY_JUMBO_ACTOR_ID` | No | `harvestedge/jumbo-supermarket-scraper` | Apify actor ID for Jumbo |
| `PICNIC_USERNAME` | Yes* | - | Picnic account email/username |
| `PICNIC_PASSWORD` | Yes* | - | Picnic account password |
| `PICNIC_COUNTRY_CODE` | No | `NL` | Picnic country code |
| `BACKEND_URL` | No | `http://localhost:8000` | Backend API URL (used by Streamlit frontend) |
| `OPENAI_API_KEY` | No | - | OpenAI API key for AI Health Coach feature (optional) |

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
   - Select all retailers (Albert Heijn, Jumbo, Picnic)
   - Click "Search"
   - You should see product results with prices, health tags, and retailer information
   - Select some products using the checkboxes and click "Add Selected Item(s) to Basket"

4. **Test the basket flow:**
   - Navigate to "My Basket" page
   - Verify your selected items appear in the basket
   - The basket persists across page navigations (same session)

5. **Test Health Insights:**
   - Navigate to "Health Insights" page
   - View health metrics based on items in your basket
   - See health tag distribution and spending by category

6. **Test Recipes & Ideas:**
   - Navigate to "Recipes & Ideas" page
   - Expand a recipe to see ingredients
   - Click "🛒 Add Ingredients to Basket"
   - The app will automatically find the healthiest products for each ingredient
   - Check "My Basket" to see the added items

4. **Check backend logs** in the terminal where uvicorn is running:
   - You should see structured logging output showing:
     - Search request parameters
     - Connector results counts (raw products from each retailer)
     - Aggregated response size

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
- Verify API tokens are valid (Apify token, Picnic credentials)
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
- **Unified Comparison Table**: View all products in one table with comparison columns
- **Add to Basket**: Select multiple products and add them to your basket with one click
- **Form State Persistence**: Search filters persist when navigating between pages

### My Basket
- **Shopping Cart Management**: View, manage, and remove items from your basket
- **Session Persistence**: Basket persists across page navigations within the same browser session
- **Cart Summary**: See total items, total price, and retailer breakdown

### Health Insights
- **Basket Health Profile**: Analytics dashboard showing health metrics for your basket
- **Health Tag Distribution**: Visual breakdown of healthy vs. less healthy items
- **Spending by Category**: See how much you're spending on healthy vs. unhealthy items
- **AI Health Coach** (optional): Get AI-generated insights about your basket (requires `OPENAI_API_KEY`)

### Recipes & Ideas
- **Recipe Collection**: Browse healthy recipes organized by meal type and tags
- **One-Click Ingredient Addition**: Add all recipe ingredients to basket with a single click
- **Smart Product Selection**: Automatically selects the healthiest available product for each ingredient
  - Prioritizes products tagged as "healthy"
  - Falls back to cheapest option if health scores are tied
  - Best-effort matching: adds what can be found, reports missing ingredients
- **Recipe Details**: View ingredients, instructions, prep time, and difficulty for each recipe

### System Status
- **Backend Health**: Monitor backend API status and connectivity
- **API Documentation**: Quick access to API documentation
- **System Diagnostics**: View system details and planned diagnostic features

## API Endpoints

### Search Products

Search for products across multiple retailers:

```bash
# Basic search
curl "http://127.0.0.1:8000/search?q=milk&retailers=ah,jumbo,picnic"

# Filter by specific retailer
curl "http://127.0.0.1:8000/search?q=cola&retailers=ah"

# Sort by price and filter healthy products
curl "http://127.0.0.1:8000/search?q=banana&retailers=ah,jumbo&sort_by=price&health_filter=healthy"

# Pagination
curl "http://127.0.0.1:8000/search?q=bread&retailers=ah&size=10&page=1"
```

**Query Parameters:**
- `q` (required): Search query string
- `retailers` (optional): Comma-separated list of retailers (`ah`, `jumbo`, `picnic`). Default: `picnic,ah,jumbo`
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

### Delivery Slots

Get available delivery slots for a retailer:

```bash
curl "http://127.0.0.1:8000/delivery/slots?retailer=picnic"
```

## Production Deployment

For production/staging, the backend is deployed on Render using `render.yaml`. 

**Environment Variables on Render:**
- Set all required environment variables in the Render dashboard (APIFY_TOKEN, PICNIC_USERNAME, PICNIC_PASSWORD, etc.)
- For the Streamlit frontend service, set `BACKEND_URL` to your backend service URL (e.g., `https://nl-grocery-aggregator.onrender.com`)
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

**Apify Configuration** (required for AH and Jumbo connectors):
- `APIFY_TOKEN` - Apify API token (required)
- `APIFY_AH_ACTOR_ID` - Apify actor ID for Albert Heijn (default: `harvestedge/my-actor`)
- `APIFY_JUMBO_ACTOR_ID` - Apify actor ID for Jumbo (default: `harvestedge/jumbo-supermarket-scraper`)

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

- **In-memory Cart**: Cart data is stored in memory and will be lost on server restart
- **No Authentication**: API endpoints do not require authentication (development only)
- **Rate Limiting**: No rate limiting implemented (be respectful of retailer APIs)
- **Delivery Slots**: Only Picnic delivery slots are currently implemented

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Important Note**: While this project is open source, be aware that it interfaces with retailer APIs. Respect retailer terms of service and do not deploy to production without proper legal review.

## Contributing

This is a learning project. Contributions, suggestions, and improvements are welcome!
