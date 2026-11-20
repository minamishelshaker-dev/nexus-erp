# Nexus ERP - Technical Documentation
## Version 1.0.0

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Database Schema](#4-database-schema)
5. [API Reference](#5-api-reference)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Customization Guide](#7-customization-guide)
8. [Deployment](#8-deployment)
9. [Development Setup](#9-development-setup)

---

## 1. Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx (Reverse Proxy)                     │
│                         Port 80/443                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
┌───────────────────┐             ┌───────────────────┐
│    Frontend       │             │     Backend       │
│  (React + Vite)   │             │   (FastAPI)       │
│   Port 3000       │             │   Port 8000       │
└───────────────────┘             └─────────┬─────────┘
                                            │
            ┌───────────────────────────────┼───────────────────┐
            │                               │                   │
            ▼                               ▼                   ▼
┌───────────────────┐             ┌───────────────────┐ ┌────────────────┐
│    PostgreSQL     │             │      Redis        │ │ Celery Worker  │
│     Port 5432     │             │    Port 6379      │ │  (Background)  │
└───────────────────┘             └───────────────────┘ └────────────────┘
```

### Multi-Tenancy

The system implements a **shared database, shared schema** multi-tenancy approach:

- All tables have a `tenant_id` column (UUID)
- Row-level security via application-level filtering
- Automatic tenant context injection in all queries
- Tenant isolation in API responses

### Key Design Patterns

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| **Repository Pattern** | Service layer classes | Data access abstraction |
| **Dependency Injection** | FastAPI Depends() | Loose coupling, testability |
| **Unit of Work** | SQLAlchemy sessions | Transaction management |
| **Event-Driven** | Celery tasks | Async processing |
| **CQRS** | Separate read/write paths | Performance optimization |

---

## 2. Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | FastAPI | 0.109+ | REST API framework |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction |
| **Database** | PostgreSQL | 15+ | Primary data store |
| **Cache/Queue** | Redis | 7+ | Caching, message broker |
| **Task Queue** | Celery | 5.3+ | Background jobs |
| **Auth** | JWT + OAuth2 | - | Authentication |
| **Validation** | Pydantic | 2.6+ | Data validation |
| **Migrations** | Alembic | 1.13+ | DB versioning |

### Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | React | 19+ | UI library |
| **Build Tool** | Vite | 5+ | Build/bundle |
| **Styling** | Tailwind CSS | 3.4+ | CSS framework |
| **State** | Zustand | 4+ | State management |
| **HTTP Client** | Axios | 1.6+ | API requests |
| **Routing** | React Router | 6+ | Client routing |
| **Forms** | React Hook Form | 7+ | Form handling |
| **Icons** | Lucide React | 0.300+ | Icon library |

### AI/ML Services

| Service | Purpose | Integration |
|---------|---------|-------------|
| **Forecasting** | Demand prediction | z-ai-web-dev-sdk |
| **OCR** | Invoice parsing | z-ai-web-dev-sdk |
| **Chatbot** | Natural language queries | z-ai-web-dev-sdk |

---

## 3. Project Structure

```
nexus-erp/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/      # API route handlers
│   │   │       │   ├── auth.py
│   │   │       │   ├── accounts.py
│   │   │       │   ├── sales.py
│   │   │       │   ├── purchase.py
│   │   │       │   ├── manufacturing.py
│   │   │       │   └── ai.py
│   │   │       └── __init__.py    # Router configuration
│   │   ├── core/
│   │   │   ├── config.py          # Settings management
│   │   │   ├── database.py        # DB connection
│   │   │   └── security.py        # Auth utilities
│   │   ├── models/                # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── accounting.py
│   │   │   ├── inventory.py
│   │   │   ├── sales.py
│   │   │   ├── purchase.py
│   │   │   ├── manufacturing.py
│   │   │   └── ai.py
│   │   ├── schemas/               # Pydantic schemas
│   │   ├── services/              # Business logic
│   │   │   ├── accounting_service.py
│   │   │   ├── inventory_service.py
│   │   │   ├── sales_service.py
│   │   │   ├── purchase_service.py
│   │   │   ├── manufacturing_service.py
│   │   │   ├── integration_service.py
│   │   │   └── ai/
│   │   │       ├── forecasting_service.py
│   │   │       ├── ocr_service.py
│   │   │       └── chatbot_service.py
│   │   └── main.py                # FastAPI app
│   ├── tests/                     # Test suite
│   ├── alembic/                   # Migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/            # Reusable components
│   │   │   └── layout/
│   │   ├── pages/                 # Page components
│   │   │   ├── accounts/
│   │   │   ├── inventory/
│   │   │   ├── sales/
│   │   │   ├── purchase/
│   │   │   ├── manufacturing/
│   │   │   └── ai/
│   │   ├── services/              # API clients
│   │   ├── stores/                # State management
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker/
│   ├── nginx.conf
│   ├── demo_data.sql
│   └── init-db.sql
├── docs/
│   ├── USER_GUIDE.md
│   └── TECHNICAL.md
├── docker-compose.yml
├── .env.example
├── install.sh
├── install.bat
├── LICENSE
└── README.md
```

---

## 4. Database Schema

### Core Entities

```sql
-- Companies/Tenants
CREATE TABLE companies (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_superuser BOOLEAN DEFAULT false,
    status VARCHAR(20) DEFAULT 'active',
    tenant_id UUID REFERENCES companies(id)
);

-- Accounts (Chart of Accounts)
CREATE TABLE accounts (
    id UUID PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    account_type VARCHAR(20) NOT NULL,  -- asset, liability, equity, revenue, expense
    category VARCHAR(50),
    parent_id UUID REFERENCES accounts(id),
    balance DECIMAL(15,2) DEFAULT 0,
    tenant_id UUID NOT NULL,
    UNIQUE(code, tenant_id)
);

-- Products
CREATE TABLE products (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    cost_price DECIMAL(15,2),
    sale_price DECIMAL(15,2),
    quantity_on_hand DECIMAL(15,2) DEFAULT 0,
    quantity_available DECIMAL(15,2) DEFAULT 0,
    is_stockable BOOLEAN DEFAULT true,
    tenant_id UUID NOT NULL,
    UNIQUE(sku, tenant_id)
);
```

### Entity Relationships

```
Company (1) ──────── (*) User
     │
     └─── (*) Account
     │
     └─── (*) Product
              │
              ├─── (*) StockMove
              │
              ├─── (*) SaleOrderLine
              │
              └─── (*) PurchaseOrderLine
```

---

## 5. API Reference

### Base URL

```
Production: https://your-domain.com/api/v1
Development: http://localhost:8000/api/v1
```

### Authentication

All endpoints (except login) require JWT token:

```http
Authorization: Bearer <access_token>
```

### Core Endpoints

| Module | Endpoint | Method | Description |
|--------|----------|--------|-------------|
| **Auth** | `/auth/login` | POST | User login |
| | `/auth/refresh` | POST | Refresh token |
| | `/auth/logout` | POST | Logout |
| **Accounts** | `/accounts` | GET | List accounts |
| | `/accounts` | POST | Create account |
| | `/journal-entries` | GET | List journal entries |
| | `/journal-entries` | POST | Create journal entry |
| **Inventory** | `/inventory/products` | GET | List products |
| | `/inventory/products` | POST | Create product |
| | `/inventory/stock-moves` | GET | List stock moves |
| | `/inventory/stock-moves` | POST | Create stock move |
| **Sales** | `/sales/quotations` | GET/POST | Quotations |
| | `/sales/orders` | GET/POST | Sale orders |
| | `/sales/invoices` | GET/POST | Invoices |
| **Purchase** | `/purchase/orders` | GET/POST | Purchase orders |
| | `/purchase/receipts` | GET/POST | Receipts |
| **Manufacturing** | `/manufacturing/boms` | GET/POST | Bills of Material |
| | `/manufacturing/orders` | GET/POST | Manufacturing orders |
| **AI** | `/ai/forecast` | POST | Generate forecast |
| | `/ai/chat` | POST | Chatbot query |
| | `/ai/ocr/upload` | POST | Upload invoice |

### Request/Response Format

```json
// Standard Response
{
  "success": true,
  "data": { ... },
  "message": "Operation completed"
}

// Paginated Response
{
  "success": true,
  "data": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}

// Error Response
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [...]
  }
}
```

---

## 6. Authentication & Authorization

### JWT Token Structure

```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "tenant_id": "company_id",
  "roles": ["admin"],
  "permissions": ["read", "write"],
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Permission Format

Permissions follow the pattern: `module.resource.action`

Examples:
- `accounting.accounts.read`
- `accounting.accounts.write`
- `inventory.products.delete`
- `sales.orders.confirm`

### Role-Based Access Control

```python
# In endpoints
@router.post("/journal-entries")
@require_permission("accounting.journal_entries.write")
async def create_journal_entry(...):
    pass

# Permission check decorator
def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=Depends(get_current_user), **kwargs):
            if not current_user.has_permission(permission):
                raise HTTPException(403, "Permission denied")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 7. Customization Guide

### Adding a New Module

1. **Create Models** (`app/models/new_module.py`):

```python
from sqlalchemy import Column, String, ForeignKey
from app.models.base import BaseModel

class NewEntity(BaseModel):
    __tablename__ = "new_entities"
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    tenant_id = Column(UUID, ForeignKey("companies.id"))
```

2. **Create Schemas** (`app/schemas/new_module.py`):

```python
from pydantic import BaseModel
from datetime import datetime

class NewEntityCreate(BaseModel):
    name: str
    description: str | None = None

class NewEntityResponse(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
```

3. **Create Service** (`app/services/new_module_service.py`):

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.new_module import NewEntity

class NewModuleService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: NewEntityCreate, tenant_id: UUID):
        entity = NewEntity(**data.dict(), tenant_id=tenant_id)
        self.db.add(entity)
        await self.db.commit()
        return entity
```

4. **Create Endpoint** (`app/api/v1/endpoints/new_module.py`):

```python
from fastapi import APIRouter, Depends
from app.services.new_module_service import NewModuleService

router = APIRouter(prefix="/new-module", tags=["New Module"])

@router.post("/")
async def create(
    data: NewEntityCreate,
    service: NewModuleService = Depends(get_service)
):
    return await service.create(data)
```

5. **Register Router** (`app/api/v1/__init__.py`):

```python
from app.api.v1.endpoints import new_module

api_router.include_router(new_module.router)
```

6. **Create Migration**:

```bash
alembic revision --autogenerate -m "Add new_module"
alembic upgrade head
```

### Customizing Accounting Integration

Modify `app/services/integration_service.py` to add custom accounting logic:

```python
async def process_custom_transaction(self, transaction, tenant_id, user_id):
    """
    Custom accounting integration.
    """
    # Create journal entry
    entry = await self.accounting_service.create_journal_entry(
        date=transaction.date,
        description=f"Custom: {transaction.reference}",
        lines=[
            {"account_id": debit_account, "debit": amount, "credit": 0},
            {"account_id": credit_account, "debit": 0, "credit": amount},
        ],
        tenant_id=tenant_id
    )
    return entry
```

### Adding Custom Reports

1. Create report template in `app/services/reports/`
2. Add endpoint in `app/api/v1/endpoints/reports.py`
3. Implement report logic with appropriate aggregations

---

## 8. Deployment

### Production Checklist

- [ ] Change all default passwords
- [ ] Set `DEBUG=false` in `.env`
- [ ] Configure SSL certificates
- [ ] Set up database backups
- [ ] Configure monitoring (Prometheus/Grafana)
- [ ] Set up log aggregation
- [ ] Configure rate limiting
- [ ] Enable firewall rules

### Scaling

```yaml
# docker-compose.prod.yml
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
  
  celery-worker:
    deploy:
      replicas: 2
```

### Backup Strategy

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
docker compose exec -T postgres pg_dump -U nexus_user nexus_erp > backup_$DATE.sql
# Upload to S3 or backup server
aws s3 cp backup_$DATE.sql s3://backups/nexus-erp/
```

---

## 9. Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# With coverage report
pytest tests/ -v --cov=app --cov-report=html
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Support

For technical support:
- Email: support@nexus-erp.com
- Documentation: /docs folder
- API Docs: http://localhost:8000/docs

---

**© 2024 Nexus ERP. All rights reserved.**
