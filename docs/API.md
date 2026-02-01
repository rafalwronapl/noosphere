# Noosphere Observatory API

REST API for accessing observatory data programmatically.

## Base URL

```
http://localhost:5000/api/v1
```

## Running the API Server

```bash
# Install dependencies
pip install flask flask-cors

# Start server
python scripts/api_server.py

# With options
python scripts/api_server.py --port 8080 --debug
```

## Endpoints

### GET /api/v1

API documentation and available endpoints.

**Response:**
```json
{
  "name": "Noosphere Observatory API",
  "version": "1.0.0",
  "endpoints": {...}
}
```

---

### GET /api/v1/discoveries

List all discoveries with optional filtering.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `significance` | string | Filter by HIGH, MEDIUM, or LOW |
| `category` | string | Filter by category name |
| `q` | string | Search in title and description |
| `limit` | int | Max results (default: 50, max: 100) |
| `offset` | int | Pagination offset (default: 0) |

**Example:**
```bash
curl "http://localhost:5000/api/v1/discoveries?significance=HIGH&limit=10"
```

**Response:**
```json
{
  "total": 14,
  "limit": 10,
  "offset": 0,
  "count": 10,
  "discoveries": [
    {
      "id": "d001",
      "title": "Collective Immunity Against Prompt Injection",
      "description": "...",
      "significance": "HIGH",
      "category": "behavioral",
      "date": "2026-01-31"
    }
  ]
}
```

---

### GET /api/v1/discoveries/{id}

Get a single discovery by ID.

**Example:**
```bash
curl "http://localhost:5000/api/v1/discoveries/d001"
```

---

### GET /api/v1/discoveries/categories

List all categories with counts.

**Response:**
```json
{
  "categories": [
    {"name": "behavioral", "count": 5},
    {"name": "linguistic", "count": 3}
  ]
}
```

---

### GET /api/v1/stats

Get observatory statistics.

**Response:**
```json
{
  "discoveries": {
    "total": 14,
    "by_significance": {"high": 3, "medium": 7, "low": 4}
  },
  "observatory": {
    "total_posts": 4535,
    "total_actors": 3202,
    "posts_today": 127,
    "active_submolts": 15
  },
  "generated_at": "2026-02-01T18:00:00"
}
```

---

### GET /api/v1/featured-agent

Get the featured agent of the week.

**Response:**
```json
{
  "agent": {
    "name": "eudaemon_0",
    "total_posts": 5,
    "first_seen": "2026-01-30T16:59:28",
    "last_seen": "2026-02-01T14:30:00",
    "total_upvotes": 4513,
    "total_comments": 199,
    "notable_post": {
      "title": "The supply chain attack nobody is talking about...",
      "content": "...",
      "upvotes": 4513,
      "comments": 199
    },
    "selected_at": "2026-02-01T18:00:00"
  },
  "featured_period": "weekly"
}
```

---

### GET /api/v1/health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "Noosphere Observatory API",
  "version": "1.0.0",
  "timestamp": "2026-02-01T18:00:00"
}
```

---

## Feeds

In addition to the API, data is available as feeds:

| Format | URL |
|--------|-----|
| RSS 2.0 | `/feeds/discoveries.xml` |
| Atom 1.0 | `/feeds/discoveries.atom` |
| JSON Feed | `/feeds/discoveries.json` |

---

## Rate Limits

Currently no rate limits are enforced. Please be respectful.

## Error Responses

```json
{
  "error": "Resource not found"
}
```

HTTP status codes:
- `200` - Success
- `404` - Resource not found
- `500` - Server error
