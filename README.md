# NL Grocery Aggregator

A FastAPI backend service that aggregates grocery product search results from multiple Dutch supermarkets (Albert Heijn, Jumbo, and Picnic). This service provides a unified API to search, compare, and manage shopping carts across retailers.

## Features

- **Unified Product Search**: Search for products across Albert Heijn, Jumbo, and Picnic in a single API call
- **Normalized Product Schema**: All products are normalized into a consistent format regardless of retailer
- **Health Tagging**: Automatic classification of products as "healthy", "unhealthy", or "neutral"
- **Price Comparison**: Automatically marks the cheapest option for products with the same name
- **Shopping Cart**: In-memory cart management with session-based isolation
- **Delivery Slots**: Retrieve available delivery time slots (currently Picnic only)
- **RESTful API**: Clean FastAPI endpoints with automatic OpenAPI documentation

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
├── sandbox/                # Manual testing scripts
├── tests/                  # Test suite
└── requirements.txt        # Python dependencies
```

## Setup

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

Create a `.env` file in the project root with the following variables:

```env
# Apify Configuration (required for AH and Jumbo)
APIFY_TOKEN=your_apify_token_here
APIFY_AH_ACTOR_ID=harvestedge/my-actor
APIFY_JUMBO_ACTOR_ID=harvestedge/jumbo-supermarket-scraper

# Picnic Configuration (required for Picnic)
PICNIC_USERNAME=your_email@example.com
PICNIC_PASSWORD=your_password_here
PICNIC_COUNTRY_CODE=NL
```

#### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APIFY_TOKEN` | Yes* | - | Apify API token for AH and Jumbo connectors |
| `APIFY_AH_ACTOR_ID` | No | `harvestedge/my-actor` | Apify actor ID for Albert Heijn |
| `APIFY_JUMBO_ACTOR_ID` | No | `harvestedge/jumbo-supermarket-scraper` | Apify actor ID for Jumbo |
| `PICNIC_USERNAME` | Yes* | - | Picnic account email/username |
| `PICNIC_PASSWORD` | Yes* | - | Picnic account password |
| `PICNIC_COUNTRY_CODE` | No | `NL` | Picnic country code |

*Required only if you want to use the corresponding retailer. You can use the API with just one retailer if desired.

## Running the API

Start the FastAPI server:

```bash
uvicorn api.main:app --reload
```

The API will be available at:
- **API**: http://127.0.0.1:8000
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

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
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

Note: Render automatically provides the `$PORT` environment variable. For local testing with a specific port, use:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 10000
```

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
