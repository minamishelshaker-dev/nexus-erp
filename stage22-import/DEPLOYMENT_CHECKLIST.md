# Nexus ERP - قائمة مرجعية للنشر
## Deployment Checklist

---

## 1. المتطلبات المسبقة (Pre-requisites)

### 1.1 البنية التحتية

- [ ] **الخادم (Server)**
  - CPU: 4 cores minimum (8 cores recommended)
  - RAM: 8GB minimum (16GB recommended)
  - Storage: 100GB SSD minimum
  - OS: Ubuntu 22.04 LTS أو CentOS 8+

- [ ] **الشبكة (Network)**
  - منفذ 80 مفتوح (HTTP)
  - منفذ 443 مفتوح (HTTPS)
  - منفذ 5432 للاتصال بقاعدة البيانات (داخلي فقط)
  - منفذ 6379 لـ Redis (داخلي فقط)

- [ ] **الدومين (Domain)**
  - تسجيل الدومين (مثال: erp.company.com)
  - إعداد DNS records

---

### 1.2 البرمجيات المطلوبة

- [ ] **Docker**
  ```bash
  # تثبيت Docker
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  
  # التحقق من التثبيت
  docker --version
  # Expected: Docker version 24.x or higher
  ```

- [ ] **Docker Compose**
  ```bash
  # تثبيت Docker Compose
  sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
  
  # التحقق
  docker-compose --version
  # Expected: Docker Compose version v2.x
  ```

- [ ] **Git**
  ```bash
  sudo apt install git -y
  git --version
  ```

- [ ] **PostgreSQL Client** (اختياري للإدارة)
  ```bash
  sudo apt install postgresql-client -y
  ```

---

## 2. إعداد متغيرات البيئة

### 2.1 إنشاء ملف .env

```bash
# نسخ الملف النموذجي
cp .env.example .env

# تحرير الملف
nano .env
```

### 2.2 المتغيرات المطلوبة

```bash
# ==========================================
# Application Settings
# ==========================================
APP_NAME=Nexus ERP
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# ==========================================
# Security Settings
# ==========================================
SECRET_KEY=<generate-secure-key>
# توليد مفتاح سري:
# python -c "import secrets; print(secrets.token_urlsafe(64))"

JWT_SECRET_KEY=<generate-jwt-key>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ==========================================
# Database Settings
# ==========================================
DATABASE_URL=postgresql+asyncpg://nexus_user:SECURE_PASSWORD@db:5432/nexus_erp
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

POSTGRES_USER=nexus_user
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=nexus_erp

# ==========================================
# Redis Settings
# ==========================================
REDIS_URL=redis://redis:6379/0

# ==========================================
# CORS Settings
# ==========================================
CORS_ORIGINS=["https://erp.company.com"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET","POST","PUT","DELETE","PATCH"]
CORS_ALLOW_HEADERS=["*"]

# ==========================================
# AI Services (Optional)
# ==========================================
AI_API_KEY=<your-ai-api-key>
AI_API_ENDPOINT=https://api.openai.com/v1

# ==========================================
# Email Settings (Optional)
# ==========================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notifications@company.com
SMTP_PASSWORD=<app-password>
SMTP_FROM=noreply@company.com

# ==========================================
# File Storage
# ==========================================
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE=10485760  # 10MB
```

### 2.3 التحقق من المتغيرات

```bash
# التحقق من وجود جميع المتغيرات المطلوبة
python -c "
import os
required = ['SECRET_KEY', 'JWT_SECRET_KEY', 'DATABASE_URL', 'POSTGRES_PASSWORD']
for var in required:
    if not os.getenv(var):
        print(f'MISSING: {var}')
    else:
        print(f'OK: {var}')
"
```

---

## 3. تشغيل النظام

### 3.1 بناء وتشغيل Docker Containers

```bash
# الانتقال لمجلد المشروع
cd nexus-erp

# بناء الصور
docker-compose build

# تشغيل الخدمات
docker-compose up -d

# التحقق من حالة الخدمات
docker-compose ps
```

**النتيجة المتوقعة:**
```
NAME                COMMAND                  STATUS              PORTS
nexus-backend       "uvicorn app.main:ap…"   Up 2 minutes        0.0.0.0:8000->8000/tcp
nexus-frontend      "nginx -g 'daemon of…"   Up 2 minutes        0.0.0.0:3000->80/tcp
nexus-db            "docker-entrypoint.s…"   Up 2 minutes        5432/tcp
nexus-redis         "docker-entrypoint.s…"   Up 2 minutes        6379/tcp
```

### 3.2 مراقبة السجلات (Logs)

```bash
# عرض سجلات جميع الخدمات
docker-compose logs -f

# عرض سجلات خدمة محددة
docker-compose logs -f backend
docker-compose logs -f db
```

---

## 4. ترحيلات قاعدة البيانات (Database Migrations)

### 4.1 تشغيل الترحيلات

```bash
# التحقق من حالة الترحيلات
docker-compose exec backend alembic current

# تشغيل الترحيلات
docker-compose exec backend alembic upgrade head

# التحقق من نجاح الترحيل
docker-compose exec backend alembic history
```

### 4.2 إنشاء مستخدم مدير (Admin User)

```bash
# الدخول لبيئة Python
docker-compose exec backend python

# إنشاء المستخدم
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User, Role, Permission
import asyncio

async def create_admin():
    async for db in get_db():
        admin = User(
            email="admin@company.com",
            username="admin",
            password_hash=get_password_hash("Admin@123456"),
            first_name="System",
            last_name="Admin",
            is_superuser=True,
            status="active"
        )
        db.add(admin)
        await db.commit()
        print("Admin user created successfully!")
        break

asyncio.run(create_admin())
```

---

## 5. البيانات الأولية (Initial Data)

### 5.1 الحسابات المحاسبية الافتراضية

```bash
# تشغيل سكريبت البيانات الأولية
docker-compose exec backend python -m app.scripts.init_data
```

**الحسابات المُنشأة:**
| الكود | الاسم | النوع |
|-------|-------|-------|
| 1000 | الصندوق | أصل |
| 1100 | البنك | أصل |
| 1200 | المخزون | أصل |
| 1300 | العملاء | أصل |
| 1400 | العمل تحت التنفيذ | أصل |
| 1900 | GR/IR | أصل |
| 2000 | الموردون | خصم |
| 2100 | الذمم المختلفة | خصم |
| 2300 | ضريبة المبيعات المستحقة | خصم |
| 3000 | رأس المال | حقوق ملكية |
| 4000 | المبيعات | إيراد |
| 5000 | تكلفة البضاعة المباعة | مصروف |
| 6000 | مصاريف قوة العمل | مصروف |

### 5.2 فئات المنتجات

```bash
# إنشاء فئات افتراضية
docker-compose exec backend python -m app.scripts.init_categories
```

### 5.3 أدوار وصلاحيات افتراضية

```bash
# إنشاء الأدوار
docker-compose exec backend python -m app.scripts.init_roles
```

---

## 6. التحقق بعد التشغيل

### 6.1 فحص الصحة (Health Check)

```bash
# فحص صحة الخدمات
curl http://localhost:8000/health
# Expected: {"status": "healthy", ...}

curl http://localhost:8000/health/ready
# Expected: {"status": "ready", ...}
```

### 6.2 التحقق من Swagger

- [ ] فتح `/api/docs` في المتصفح
- [ ] ظهور جميع الـ endpoints
- [ ] اختبار endpoint `/api/v1/auth/login`

### 6.3 التحقق من الواجهة الأمامية

- [ ] فتح `http://localhost:3000` في المتصفح
- [ ] ظهور صفحة تسجيل الدخول
- [ ] تسجيل الدخول بالمستخدم المدير

### 6.4 إنشاء بيانات تجريبية

```bash
# إنشاء منتج تجريبي
curl -X POST http://localhost:8000/api/v1/inventory/products \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "منتج تجريبي",
    "sku": "TEST-001",
    "cost_price": 100.00,
    "sale_price": 150.00
  }'
```

### 6.5 تنفيذ سيناريو بيع كامل

1. [ ] إنشاء منتج
2. [ ] إنشاء أمر شراء واستلام
3. [ ] إنشاء أمر بيع وتسليم
4. [ ] إنشاء فاتورة
5. [ ] التحقق من القيود المحاسبية

```bash
# التحقق من القيود
docker-compose exec db psql -U nexus_user -d nexus_erp -c "
SELECT j.number, j.date, j.state, 
       SUM(l.debit) as total_debit, 
       SUM(l.credit) as total_credit
FROM journal_entries j
JOIN journal_entry_lines l ON j.id = l.journal_entry_id
GROUP BY j.id
ORDER BY j.date DESC
LIMIT 10;
"
```

### 6.6 التحقق من السجلات (Logs)

```bash
# التحقق من عدم وجود أخطاء
docker-compose exec backend grep -i "error" /app/logs/*.log | tail -20
docker-compose exec backend grep -i "exception" /app/logs/*.log | tail -20
```

---

## 7. إعدادات الإنتاج المتقدمة

### 7.1 HTTPS/SSL

```bash
# استخدام Certbot للحصول على شهادة SSL
sudo apt install certbot python3-certbot-nginx

# الحصول على الشهادة
sudo certbot --nginx -d erp.company.com

# التجديد التلقائي
sudo certbot renew --dry-run
```

### 7.2 Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/nexus-erp
server {
    listen 80;
    server_name erp.company.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name erp.company.com;

    ssl_certificate /etc/letsencrypt/live/erp.company.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/erp.company.com/privkey.pem;

    client_max_body_size 20M;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 7.3 النسخ الاحتياطي التلقائي

```bash
# إنشاء سكريبت النسخ الاحتياطي
cat > /opt/backup-nexus.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/backups
mkdir -p $BACKUP_DIR

# نسخ احتياطي لقاعدة البيانات
docker-compose exec -T db pg_dump -U nexus_user nexus_erp > $BACKUP_DIR/db_$DATE.sql

# ضغط الملفات
gzip $BACKUP_DIR/db_$DATE.sql

# حذف النسخ القديمة (أكثر من 30 يوم)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/backup-nexus.sh

# إضافة للـ cron
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/backup-nexus.sh >> /var/log/nexus-backup.log 2>&1") | crontab -
```

### 7.4 المراقبة (Monitoring)

```bash
# تثبيت Prometheus و Grafana (اختياري)
docker-compose -f docker-compose.monitoring.yml up -d
```

---

## 8. استكشاف الأخطاء وإصلاحها

### 8.1 مشاكل شائعة

| المشكلة | السبب | الحل |
|---------|-------|------|
| Backend لا يبدأ | خطأ في الاتصال بقاعدة البيانات | التحقق من DATABASE_URL |
| 502 Bad Gateway | Backend معطل | `docker-compose restart backend` |
| أخطاء الترحيل | تعارض في الترحيلات | `alembic downgrade` ثم `upgrade` |
| بطء الاستجابة | موارد غير كافية | زيادة resources |

### 8.2 أوامر مفيدة

```bash
# إعادة تشغيل جميع الخدمات
docker-compose restart

# إعادة بناء الخدمات
docker-compose up -d --build

# حذف جميع البيانات وإعادة البدء
docker-compose down -v
docker-compose up -d --build

# فحص استخدام الموارد
docker stats

# الدخول لقاعدة البيانات
docker-compose exec db psql -U nexus_user -d nexus_erp
```

---

## 9. قائمة المراجعة النهائية

### قبل التشغيل
- [ ] تثبيت Docker و Docker Compose
- [ ] إعداد ملف .env بجميع المتغيرات
- [ ] تشغيل `docker-compose up -d`
- [ ] تشغيل الترحيلات `alembic upgrade head`
- [ ] إنشاء مستخدم مدير
- [ ] إضافة البيانات الأولية

### بعد التشغيل
- [ ] فتح Swagger على `/api/docs`
- [ ] فتح الواجهة الأمامية على المنفذ 3000
- [ ] تسجيل الدخول وإنشاء منتج تجريبي
- [ ] تنفيذ سيناريو بيع كامل
- [ ] التحقق من سجلات الأخطاء
- [ ] إعداد النسخ الاحتياطي

### للإنتاج
- [ ] إعداد HTTPS/SSL
- [ ] إعداد Nginx Reverse Proxy
- [ ] إعداد النسخ الاحتياطي التلقائي
- [ ] إعداد المراقبة
- [ ] تأمين قاعدة البيانات (عدم عرض المنفذ 5432)
- [ ] إعداد جدار ناري

---

## 10. جهات الاتصال للدعم

- **الدعم الفني:** support@company.com
- **المطورون:** dev@company.com
- **الطوارئ:** +966-XX-XXX-XXXX

---

*آخر تحديث: 2024*
