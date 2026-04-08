---
name: database-migration
description: Create and manage database schema migrations. TRIGGER when the user asks to create a migration, modify a database schema, add/alter/drop tables or columns, or manage database versioning.
---
# Database Migration

Create and manage database schema migrations safely and reversibly.

## Steps

1. **Identify the migration tool** - Detect the project's ORM and migration framework:
   - Python: Alembic (SQLAlchemy), Django migrations, Prisma
   - Node.js: Knex, TypeORM, Prisma, Drizzle, Sequelize
   - Go: golang-migrate, goose, atlas
   - Ruby: ActiveRecord migrations
2. **Understand the current schema** - Review existing migrations and models to understand the current database state.
3. **Design the migration** - Plan what schema changes are needed: new tables, new columns, altered types, indexes, constraints.
4. **Write the migration** - Create both the "up" (apply) and "down" (rollback) operations.
5. **Test the migration** - Run it against a development database. Verify the rollback works.
6. **Review for safety** - Check for data loss, locking issues, and backward compatibility.

## Migration Examples

### Alembic (Python / SQLAlchemy)
```bash
# Generate a new migration
alembic revision --autogenerate -m "add_users_table"

# Run migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

```python
# migrations/versions/001_add_users_table.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('ix_users_email', 'users')
    op.drop_table('users')
```

### Prisma (Node.js / TypeScript)
```prisma
// prisma/schema.prisma
model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  name      String
  orders    Order[]
  createdAt DateTime @default(now())
}

model Order {
  id     Int    @id @default(autoincrement())
  total  Float
  userId Int
  user   User   @relation(fields: [userId], references: [id])
}
```

```bash
# Generate and apply migration
npx prisma migrate dev --name add_users_and_orders

# Apply in production
npx prisma migrate deploy

# Reset database (development only)
npx prisma migrate reset
```

### Knex (Node.js)
```javascript
// migrations/20250115_create_users.js
exports.up = function(knex) {
  return knex.schema.createTable('users', (table) => {
    table.increments('id').primary();
    table.string('email', 255).notNullable().unique();
    table.string('name', 255).notNullable();
    table.timestamps(true, true);
    table.index(['email']);
  });
};

exports.down = function(knex) {
  return knex.schema.dropTable('users');
};
```

### Django (Python)
```python
# models.py
from django.db import models

class User(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['email']),
        ]
```

```bash
# Generate migration from model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration SQL without applying
python manage.py sqlmigrate app_name 0001
```

### Raw SQL (golang-migrate)
```sql
-- migrations/000001_create_users.up.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users (email);

-- migrations/000001_create_users.down.sql
DROP TABLE IF EXISTS users;
```

## Safe Migration Practices

### Adding a column (safe)
```sql
-- Adding a nullable column is always safe
ALTER TABLE users ADD COLUMN phone VARCHAR(50);

-- Adding with a default requires care on large tables (can lock)
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active';
```

### Renaming a column (risky)
```sql
-- Step 1: Add new column
ALTER TABLE users ADD COLUMN full_name VARCHAR(255);
-- Step 2: Backfill data
UPDATE users SET full_name = name;
-- Step 3: Update application code to use new column
-- Step 4: Drop old column (after deployment is stable)
ALTER TABLE users DROP COLUMN name;
```

### Adding an index (potentially slow)
```sql
-- Use CONCURRENTLY on PostgreSQL to avoid table locks
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);
```

## Rules

- ALWAYS write both up and down migrations (make migrations reversible)
- NEVER modify a migration that has already been applied to production
- Test migrations on a copy of production data when possible
- For large tables, consider the impact of locks (use concurrent index creation, batched updates)
- Add NOT NULL constraints in stages: add column nullable, backfill, then add constraint
- Back up the database before running migrations in production
- Review generated migrations before applying (auto-generated migrations can be wrong)
- Keep migrations small and focused -- one logical change per migration
