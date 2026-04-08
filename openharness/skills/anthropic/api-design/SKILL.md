---
name: api-design
description: Design RESTful and GraphQL APIs with proper patterns. TRIGGER when the user asks to design an API, create endpoints, define a REST API, build a GraphQL schema, or plan API architecture.
---
# API Design

Design well-structured, consistent, and maintainable APIs following REST or GraphQL best practices.

## Steps

1. **Understand the domain** - Identify the resources, relationships, and operations the API needs to support.
2. **Choose the API style** - REST for resource-oriented CRUD, GraphQL for flexible queries with complex relationships, or RPC for action-oriented operations.
3. **Design the resource model** - Define resources, their attributes, and relationships.
4. **Define endpoints/operations** - Specify URLs, methods, request/response formats.
5. **Handle cross-cutting concerns** - Authentication, pagination, error handling, versioning.
6. **Document the API** - Create an OpenAPI spec or GraphQL schema with descriptions.

## REST API Design

### URL Structure
```
# Resources are nouns, plural
GET    /api/v1/users          # List users
POST   /api/v1/users          # Create user
GET    /api/v1/users/:id      # Get user
PUT    /api/v1/users/:id      # Replace user
PATCH  /api/v1/users/:id      # Partial update user
DELETE /api/v1/users/:id      # Delete user

# Nested resources for relationships
GET    /api/v1/users/:id/orders          # List user's orders
POST   /api/v1/users/:id/orders          # Create order for user

# Actions that don't fit CRUD (use verbs sparingly)
POST   /api/v1/users/:id/activate
POST   /api/v1/orders/:id/cancel
```

### Response Format
```json
{
  "data": {
    "id": "usr_123",
    "type": "user",
    "attributes": {
      "name": "Alice Smith",
      "email": "alice@example.com",
      "created_at": "2025-01-15T09:30:00Z"
    }
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

### Pagination
```json
GET /api/v1/users?page=2&per_page=20

{
  "data": [...],
  "pagination": {
    "page": 2,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

### Error Responses
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "email",
        "message": "must be a valid email address"
      }
    ]
  }
}
```

### HTTP Status Codes
| Code | Usage |
|------|-------|
| 200 | Success (GET, PUT, PATCH) |
| 201 | Created (POST) |
| 204 | No Content (DELETE) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (no/invalid auth) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 409 | Conflict (duplicate resource) |
| 422 | Unprocessable Entity (semantic error) |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |

## GraphQL API Design

### Schema
```graphql
type User {
  id: ID!
  name: String!
  email: String!
  orders(first: Int, after: String): OrderConnection!
  createdAt: DateTime!
}

type Order {
  id: ID!
  total: Float!
  status: OrderStatus!
  items: [OrderItem!]!
}

enum OrderStatus {
  PENDING
  CONFIRMED
  SHIPPED
  DELIVERED
  CANCELLED
}

type Query {
  user(id: ID!): User
  users(first: Int, after: String, filter: UserFilter): UserConnection!
}

type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
  updateUser(id: ID!, input: UpdateUserInput!): UpdateUserPayload!
  cancelOrder(id: ID!): CancelOrderPayload!
}

input CreateUserInput {
  name: String!
  email: String!
}

type CreateUserPayload {
  user: User
  errors: [UserError!]!
}
```

## OpenAPI Spec Example
```yaml
openapi: 3.0.3
info:
  title: User API
  version: 1.0.0
paths:
  /api/v1/users:
    get:
      summary: List users
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: per_page
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserList'
```

## Rules

- Use consistent naming conventions (camelCase or snake_case -- pick one and stick with it)
- Always version your API (`/api/v1/`) from the start
- Use proper HTTP status codes, not 200 for everything
- Include pagination for all list endpoints
- Design for idempotency (repeated PUT/DELETE should be safe)
- Validate all input on the server side
- Return only necessary data -- avoid over-fetching
- Use ISO 8601 for dates and UTC timezone
- Include rate limiting headers in responses
- Document every endpoint with request/response examples
