# Nexus ERP - نظام تخطيط موارد المؤسسات

<div align="center">
  <img src="docs/logo.png" alt="Nexus ERP Logo" width="200">
  
  **نظام ERP متكامل وحديث مبني بأحدث التقنيات**
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
  [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
  [![React 19](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
</div>

---

## 📋 نظرة عامة

**Nexus ERP** هو نظام تخطيط موارد مؤسسات متكامل مبني من الصفر باستخدام أحدث التقنيات. يوفر النظام حلاً شاملاً لإدارة جميع جوانب الأعمال التجارية مع التركيز على:

- **الأداء العالي**: بنية asynchronous مع FastAPI
- **التوسعية**: دعم تعدد المستأجرين (Multi-tenancy)
- **الأمان**: JWT + RBAC مع صلاحيات دقيقة
- **تجربة المستخدم**: واجهة عصرية وسريعة مع React

---

## 🏗️ هيكل المشروع

```
nexus-erp/
├── backend/                    # الواجهة الخلفية (FastAPI)
│   ├── app/
│   │   ├── api/               # نقاط نهاية API
│   │   │   └── v1/
│   │   │       └── endpoints/ # مسارات API
│   │   ├── core/              # الإعدادات الأساسية
│   │   │   ├── config.py      # إعدادات التطبيق
│   │   │   ├── database.py    # اتصال قاعدة البيانات
│   │   │   └── security.py    # المصادقة والأمان
│   │   ├── models/            # نماذج SQLAlchemy
│   │   ├── schemas/           # مخططات Pydantic
│   │   ├── services/          # منطق الأعمال
│   │   └── main.py            # نقطة الدخول
│   ├── tests/                 # اختبارات pytest
│   ├── requirements.txt       # المكتبات المطلوبة
│   └── Dockerfile
│
├── frontend/                   # الواجهة الأمامية (React)
│   ├── src/
│   │   ├── components/        # مكونات React
│   │   ├── pages/             # صفحات التطبيق
│   │   ├── services/          # خدمات API
│   │   ├── stores/            # حالة التطبيق (Zustand)
│   │   └── main.tsx           # نقطة الدخول
│   ├── package.json
│   └── Dockerfile
│
├── docker/                     # ملفات Docker
├── docs/                       # التوثيق
├── docker-compose.yml          # تكوين Docker Compose
└── README.md
```

---

## 🚀 التشغيل السريع

### المتطلبات الأساسية

- Docker و Docker Compose
- Node.js 18+ (للتطوير المحلي)
- Python 3.11+ (للتطوير المحلي)
- PostgreSQL 15+
- Redis 7+

### التشغيل باستخدام Docker

```bash
# استنساخ المشروع
git clone https://github.com/your-org/nexus-erp.git
cd nexus-erp

# تشغيل جميع الخدمات
docker-compose up -d

# الوصول إلى التطبيق
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

### التشغيل المحلي للتطوير

```bash
# 1. إعداد قاعدة البيانات
createdb nexus_erp

# 2. تشغيل Redis
redis-server

# 3. تشغيل Backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
# أو venv\Scripts\activate على Windows
pip install -r requirements.txt
cp .env.example .env
# عدّل ملف .env بالإعدادات المناسبة
uvicorn app.main:app --reload

# 4. تشغيل Frontend (في طرفية جديدة)
cd frontend
npm install
npm run dev
```

---

## 📊 مخطط قاعدة البيانات (ERD)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          NEXUS ERP DATABASE SCHEMA                       │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│      users       │     │    user_roles    │     │      roles       │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ id (PK)          │────<│ user_id (FK)     │>────│ id (PK)          │
│ tenant_id (FK)   │     │ role_id (FK)     │     │ tenant_id (FK)   │
│ email            │     │ assigned_by_id   │     │ code             │
│ username         │     │ assigned_at      │     │ name             │
│ password_hash    │     │ expires_at       │     │ description      │
│ first_name       │     └──────────────────┘     │ parent_id (FK)   │
│ last_name        │                              │ is_system        │
│ status           │     ┌──────────────────┐     └────────┬─────────┘
│ is_superuser     │     │role_permissions  │              │
│ created_at       │     ├──────────────────┤              │
└──────────────────┘     │ role_id (FK)     │>─────────────┘
                         │ permission_id(FK)│     ┌──────────────────┐
                         └──────────────────┘     │   permissions    │
                                                  ├──────────────────┤
┌──────────────────┐     ┌──────────────────┐     │ id (PK)          │
│    customers     │     │    contacts      │     │ code             │
├──────────────────┤     ├──────────────────┤     │ name             │
│ id (PK)          │────<│ id (PK)          │     │ module           │
│ tenant_id (FK)   │     │ customer_id (FK) │     │ action           │
│ code             │     │ first_name       │     │ resource         │
│ name             │     │ last_name        │     │ scope            │
│ customer_type    │     │ email            │     └──────────────────┘
│ status           │     │ phone            │
│ email            │     │ is_primary       │
│ phone            │     └──────────────────┘
│ credit_limit     │
│ total_revenue    │     ┌──────────────────┐     ┌──────────────────┐
│ sales_rep_id(FK) │────<│customer_addresses│     │    products      │
└────────┬─────────┘     ├──────────────────┤     ├──────────────────┤
         │               │ id (PK)          │     │ id (PK)          │
         │               │ customer_id (FK) │     │ tenant_id (FK)   │
         │               │ address_line1    │     │ sku              │
         │               │ city             │     │ name             │
         │               │ country          │     │ product_type     │
         │               │ is_billing       │     │ status           │
         │               │ is_shipping      │     │ category_id (FK) │
         │               └──────────────────┘     │ cost_price       │
         │                                        │ sale_price       │
         │               ┌──────────────────┐     │ quantity_on_hand │
         │               │       leads      │     └────────┬─────────┘
         │               ├──────────────────┤              │
         └──────────────>│ id (PK)          │              │
                         │ customer_id (FK) │              │
                         │ name             │              │
                         │ status           │              │
                         │ source           │              │
                         │ estimated_value  │              │
                         └──────────────────┘              │
                                                          │
                         ┌──────────────────┐              │
                         │  stock_quantities│<─────────────┘
                         ├──────────────────┤
                         │ id (PK)          │
                         │ product_id (FK)  │
                         │ warehouse_id(FK) │
                         │ quantity         │
                         └──────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   warehouses     │     │   stock_moves    │     │ bill_of_materials│
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ id (PK)          │────<│ id (PK)          │     │ id (PK)          │
│ tenant_id (FK)   │     │ product_id (FK)  │     │ product_id (FK)  │
│ code             │     │ warehouse_from   │     │ name             │
│ name             │     │ warehouse_to     │     │ product_qty      │
│ is_default       │     │ quantity         │     │ material_cost    │
│ address_line1    │     │ move_type        │     │ total_cost       │
└──────────────────┘     │ unit_cost        │     └──────────────────┘
                         └──────────────────┘

LEGEND:
PK  = Primary Key
FK  = Foreign Key
───< = One-to-Many Relationship
>─── = Many-to-One Relationship
```

---

## 🔐 نظام الصلاحيات (RBAC)

### هيكل الصلاحيات

```
Permission Hierarchy:
─────────────────────

Superuser (is_superuser=True)
    └── All permissions granted automatically

Role Hierarchy:
───────────────
    Admin
    ├── Manager
    │   ├── Team Lead
    │   │   └── User
    │   └── Senior User
    └── Accountant

Permission Format:
─────────────────
{module}.{resource}.{action}

Examples:
- crm.customer.create
- crm.customer.read
- crm.customer.update
- crm.customer.delete
- sales.invoice.approve
- inventory.stock.adjust
- accounting.journal.post
```

### الصلاحيات الافتراضية

| الدور | الوصف | الصلاحيات |
|-------|-------|-----------|
| `admin` | مدير النظام | جميع الصلاحيات |
| `sales_manager` | مدير المبيعات | CRM + Sales كاملة |
| `sales_rep` | مندوب مبيعات | CRM قراءة + إنشاء أوامر |
| `accountant` | محاسب | Accounting كاملة |
| `warehouse_manager` | مدير مخزن | Inventory كاملة |
| `hr_manager` | مدير موارد بشرية | HR كاملة |

---

## 📚 واجهة برمجة التطبيقات (API)

### المصادقة

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password123"
}

Response:
{
  "success": true,
  "token": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

### العملاء

```http
# قائمة العملاء
GET /api/v1/customers?page=1&page_size=20

# إنشاء عميل
POST /api/v1/customers
{
  "name": "شركة النجاح",
  "customer_type": "company",
  "email": "info@success.com",
  "phone": "+966501234567"
}

# تفاصيل عميل
GET /api/v1/customers/{id}

# تحديث عميل
PUT /api/v1/customers/{id}

# حذف عميل
DELETE /api/v1/customers/{id}
```

---

## 🧪 الاختبارات

```bash
# تشغيل جميع الاختبارات
cd backend
pytest

# تشغيل مع تغطية الكود
pytest --cov=app --cov-report=html

# تشغيل اختبارات محددة
pytest tests/test_auth.py -v

# تشغيل اختبارات async
pytest -v --asyncio-mode=auto
```

---

## 📦 الوحدات المتاحة

| الوحدة | الحالة | الوصف |
|--------|--------|-------|
| 🔐 المصادقة | ✅ مكتمل | JWT + RBAC + Multi-tenancy |
| 👥 CRM | ✅ مكتمل | العملاء، الموردين، الشركاء |
| 🛒 المبيعات | ✅ مكتمل | عروض الأسعار، أوامر البيع، الفواتير |
| 📦 المخزون | ✅ مكتمل | المنتجات، المستودعات، حركات المخزون |
| 🛍️ المشتريات | ✅ مكتمل | أوامر الشراء، الاستلام، فواتير الموردين |
| 💰 المحاسبة | ✅ مكتمل | شجرة الحسابات، القيود اليومية، التقارير المالية |
| 🏭 التصنيع | ✅ مكتمل | قوائم المواد (BOM)، أوامر الإنتاج، مراكز العمل |
| 🤖 الذكاء الاصطناعي | ✅ مكتمل | التنبؤ بالطلب، OCR، المساعد الذكي |
| 📈 التقارير | ✅ مكتمل | ميزان المراجعة، قائمة الدخل، الميزانية العمومية |

---

## 🤝 المساهمة

نرحب بمساهماتكم! يرجى اتباع الخطوات التالية:

1. Fork المشروع
2. إنشاء فرع للميزة (`git checkout -b feature/amazing-feature`)
3. Commit التغييرات (`git commit -m 'Add amazing feature'`)
4. Push إلى الفرع (`git push origin feature/amazing-feature`)
5. فتح Pull Request

---

## 📄 الترخيص

هذا المشروع مرخص تحت **رخصة تجارية** - راجع ملف [LICENSE](LICENSE) للتفاصيل.

**الاستخدام المسموح:**
- الاستخدام الداخلي للشركات والمؤسسات
- التعديل والتخصيص للاحتياجات الخاصة

**غير مسموح:**
- إعادة بيع البرنامج
- توزيع الكود المصدري لأطراف خارجية
- استخدام البرنامج لتقديم خدمات SaaS

---

## 📞 الدعم والتواصل

- 📧 البريد الإلكتروني: support@nexus-erp.com
- 📚 التوثيق: https://docs.nexus-erp.com
- 🐛 الإبلاغ عن مشاكل: GitHub Issues

---

<div align="center">
  <p>صُنع بـ ❤️ بواسطة فريق Nexus ERP</p>
</div>
