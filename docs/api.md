# API Documentation

## Base URL
- Development: `http://localhost:8000/api/v1`
- Production: `https://api.redteam.example.com/api/v1`

## Authentication

All endpoints (except `/health`, `/ready`, `/auth/login`, `/auth/register`) require a valid JWT Bearer token.

```
Authorization: Bearer <access_token>
```

### Token Endpoints

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

#### Get Current User
```http
GET /auth/me
Authorization: Bearer <access_token>
```

## Core Endpoints

### Health & Monitoring
- `GET /health` - Basic health check
- `GET /ready` - Readiness check (DB, Redis, etc.)
- `GET /metrics` - Prometheus metrics

### Target Agents
- `GET /agents` - List agents
- `POST /agents` - Create agent
- `GET /agents/{id}` - Get agent
- `PATCH /agents/{id}` - Update agent
- `POST /agents/{id}/test` - Test agent connectivity
- `DELETE /agents/{id}` - Delete agent

### Test Suites
- `GET /suites` - List suites
- `POST /suites` - Create suite
- `POST /suites/validate` - Validate suite schema
- `POST /suites/import/yaml` - Import from YAML
- `POST /suites/import/json` - Import from JSON
- `GET /suites/{id}` - Get suite with test cases
- `POST /suites/{id}/versions` - Create new version

### Test Cases
- `GET /test-cases/suite/{suite_id}` - List test cases
- `POST /test-cases/suite/{suite_id}` - Create test case
- `GET /test-cases/{id}` - Get test case
- `PATCH /test-cases/{id}` - Update test case
- `DELETE /test-cases/{id}` - Delete test case

### Runs
- `GET /runs` - List runs (with filters)
- `POST /runs` - Create and start run
- `GET /runs/{id}` - Get run details
- `POST /runs/{id}/cancel` - Cancel running run
- `GET /runs/{id}/executions` - List executions
- `GET /runs/{id}/results` - List results

### Results
- `GET /results/run/{run_id}` - List results for run
- `GET /results/{id}` - Get result details

### Regressions
- `GET /regressions/run/{run_id}` - List regressions
- `GET /regressions/baseline/{baseline_id}` - List by baseline
- `GET /regressions/{id}` - Get regression details
- `POST /regressions/{id}/acknowledge` - Acknowledge regression

### Baselines
- `GET /baselines` - List baselines
- `POST /baselines` - Create baseline
- `GET /baselines/suite/{suite_id}/active` - Get active baseline
- `GET /baselines/{id}` - Get baseline
- `GET /baselines/{id}/items` - List baseline items
- `POST /baselines/{id}/approve` - Approve baseline
- `POST /baselines/{id}/deactivate` - Deactivate baseline

### Reviews
- `GET /reviews` - List review queue
- `GET /reviews/{id}` - Get review
- `POST /reviews/{id}/assign` - Assign reviewer
- `POST /reviews/{id}/label` - Label review
- `GET /reviews/{id}/labels` - List review labels
- `POST /reviews/{id}/escalate` - Escalate review

### Reports
- `GET /reports/run/{run_id}` - Get run report (JSON)
- `GET /reports/run/{run_id}/markdown` - Get run report (Markdown)

### Settings
- `GET /settings/config` - Get system configuration
- `GET /settings/models` - List model configurations
- `POST /settings/models` - Create model config
- `GET /settings/prompts` - List prompt versions
- `POST /settings/prompts/promote` - Promote prompt version
- `GET /settings/feature-flags` - List feature flags
- `PATCH /settings/feature-flags/{id}` - Update feature flag

## Users & Roles
- `GET /users` - List users
- `GET /users/{id}` - Get user
- `PATCH /users/{id}` - Update user
- `POST /users/{id}/roles/{role_id}` - Assign role
- `DELETE /users/{id}/roles/{role_id}` - Remove role
- `GET /roles` - List roles
- `POST /roles` - Create role
- `GET /permissions` - List permissions

## Error Responses

All errors follow a consistent format:

```json
{
  "code": "ERROR_CODE",
  "message": "Human readable message",
  "details": {}
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Validation Error
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `422` - Unprocessable Entity
- `429` - Rate Limited
- `500` - Internal Server Error
- `503` - Service Unavailable

## Rate Limiting

Default limits:
- 100 requests per minute per IP
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- 429 response includes `Retry-After` header

## Pagination

List endpoints support:
- `skip` - Number of items to skip (default: 0)
- `limit` - Maximum items to return (default: 100, max: 1000)

Response includes:
- `items` - Array of items
- `total` - Total count
- `skip` - Skip value used
- `limit` - Limit value used

## Filtering & Sorting

Common filter parameters:
- `status` - Filter by status
- `severity` - Filter by severity
- `category` - Filter by category
- `target_agent_id` - Filter by agent
- `suite_id` - Filter by suite
- `created_after` - Filter by date
- `created_before` - Filter by date

Sort parameters:
- `sort_by` - Field to sort by
- `sort_order` - `asc` or `desc` (default: `desc`)

## Webhooks

Configure webhook URLs in settings for:
- Critical findings
- Gate failures
- Review SLA breaches
- Cost threshold exceeded
- Provider outages

Webhook payload includes event type, timestamp, and relevant resource data.