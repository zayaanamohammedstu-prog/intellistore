# Warehouse Schema

This directory contains versioned SQL schema files for the IntelliStore
PostgreSQL data warehouse.

## Files

| File | Description |
|------|-------------|
| `001_init.sql` | Core operational tables: `users`, `etl_jobs`, `staging_sales_raw` |
| `002_dim_fact.sql` | Retail DWH: `dim_date`, `dim_product`, `dim_store`, `fact_sales` |

## Applying schemas

```bash
# Local (docker-compose)
psql $DATABASE_URL -f warehouse/schema/001_init.sql
psql $DATABASE_URL -f warehouse/schema/002_dim_fact.sql
```

## TODO (production)

- Migrate to Alembic or Flyway for proper versioned migrations.
- Add `dim_customer` and `dim_promotion` tables.
- Populate `dim_date` with a pre-generated date spine.
