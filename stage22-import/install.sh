#!/bin/bash

# ========================================
# Nexus ERP - Installation Script
# ========================================
# Platform: Linux / macOS
# Usage: ./install.sh
# ========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logo
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║                    NEXUS ERP v1.0.0                       ║"
echo "║              نظام إدارة موارد المؤسسات                     ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ========================================
# Functions
# ========================================

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 غير مثبت. يرجى تثبيته أولاً."
        exit 1
    fi
}

# ========================================
# System Checks
# ========================================

print_info "جاري التحقق من متطلبات النظام..."

# Check Docker
print_info "التحقق من Docker..."
check_command docker
DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
print_success "Docker مثبت: $DOCKER_VERSION"

# Check Docker Compose
print_info "التحقق من Docker Compose..."
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    print_error "Docker Compose غير مثبت. يرجى تثبيته أولاً."
    exit 1
fi
COMPOSE_VERSION=$($COMPOSE_CMD version --short 2>/dev/null || echo "unknown")
print_success "Docker Compose مثبت: $COMPOSE_VERSION"

# Check if Docker daemon is running
print_info "التحقق من تشغيل Docker daemon..."
if ! docker info &> /dev/null; then
    print_error "Docker daemon غير مشغل. يرجى تشغيل Docker أولاً."
    print_info "على Linux: sudo systemctl start docker"
    print_info "على macOS/Windows: افتح Docker Desktop"
    exit 1
fi
print_success "Docker daemon يعمل"

# ========================================
# Environment Setup
# ========================================

print_info "إعداد ملفات التكوين..."

# Check for .env file
if [ -f ".env" ]; then
    print_warning "ملف .env موجود مسبقاً."
    read -p "هل تريد استخدامه؟ (y/n): " USE_EXISTING
    if [[ $USE_EXISTING =~ ^[Yy]$ ]]; then
        print_info "استخدام ملف .env الحالي..."
    else
        # Backup existing and create new
        cp .env .env.backup.$(date +%Y%m%d%H%M%S)
        print_info "تم حفظ نسخة احتياطية من .env"
        cp .env.example .env
    fi
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "تم إنشاء ملف .env من .env.example"
    else
        print_error "ملف .env.example غير موجود!"
        exit 1
    fi
fi

# Generate secure keys
print_info "توليد مفاتيح الأمان..."

# Generate SECRET_KEY
SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
if [ -n "$SECRET_KEY" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" .env
    else
        sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" .env
    fi
    print_success "تم توليد SECRET_KEY"
fi

# Generate JWT_SECRET_KEY
JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
if [ -n "$JWT_SECRET" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|g" .env
    else
        sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|g" .env
    fi
    print_success "تم توليد JWT_SECRET_KEY"
fi

# ========================================
# Docker Build and Start
# ========================================

print_info "جاري بناء وتشغيل الحاويات..."
print_info "قد يستغرق هذا بضع دقائق في أول مرة..."

# Pull base images first
$COMPOSE_CMD pull 2>/dev/null || true

# Build and start services
$COMPOSE_CMD up -d --build

print_success "تم بناء وتشغيل الحاويات"

# ========================================
# Wait for Services
# ========================================

print_info "جاري انتظار بدء الخدمات..."

# Wait for PostgreSQL
print_info "الانتظار لقاعدة البيانات..."
MAX_WAIT=60
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if $COMPOSE_CMD exec -T postgres pg_isready -U nexus_user -d nexus_erp &> /dev/null; then
        break
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    printf "."
done
echo ""

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    print_error "قاعدة البيانات لم تبدأ في الوقت المتوقع"
    print_info "تحقق من السجلات: $COMPOSE_CMD logs postgres"
    exit 1
fi
print_success "قاعدة البيانات جاهزة"

# Wait for Backend
print_info "الانتظار للـ API..."
WAIT_COUNT=0
MAX_WAIT=90
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/health &> /dev/null; then
        break
    fi
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
    printf "."
done
echo ""

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    print_warning "الـ API لم يستجب، لكن قد يكون قيد التشغيل"
    print_info "تحقق من السجلات: $COMPOSE_CMD logs backend"
fi

# ========================================
# Database Migrations
# ========================================

print_info "جاري تشغيل ترحيلات قاعدة البيانات..."

# Check if alembic is available
sleep 5  # Give backend time to fully initialize

$COMPOSE_CMD exec -T backend alembic upgrade head 2>/dev/null || {
    print_warning "تعذرت ترحيلات Alembic، قد تكون قاعدة البيانات جاهزة مسبقاً"
}

print_success "تم تشغيل الترحيلات"

# ========================================
# Load Demo Data
# ========================================

print_info "جاري تحميل البيانات التجريبية..."

if [ -f "docker/demo_data.sql" ]; then
    $COMPOSE_CMD exec -T postgres psql -U nexus_user -d nexus_erp < docker/demo_data.sql 2>/dev/null || {
        print_warning "تعذر تحميل بعض البيانات التجريبية"
    }
    print_success "تم تحميل البيانات التجريبية"
else
    print_warning "ملف البيانات التجريبية غير موجود"
fi

# ========================================
# Final Status
# ========================================

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                 تم التثبيت بنجاح! 🎉                       ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}معلومات الوصول:${NC}"
echo ""
echo -e "  🌐 ${YELLOW}الواجهة الأمامية:${NC}     http://localhost"
echo -e "  📚 ${YELLOW}توثيق API:${NC}         http://localhost:8000/docs"
echo -e "  🔧 ${YELLOW}ReDoc:${NC}             http://localhost:8000/redoc"
echo ""
echo -e "${BLUE}بيانات الدخول الافتراضية:${NC}"
echo ""
echo -e "  👤 ${YELLOW}المدير:${NC}"
echo -e "     البريد: ${GREEN}admin@nexus.com${NC}"
echo -e "     كلمة المرور: ${GREEN}Admin123!${NC}"
echo ""
echo -e "  👤 ${YELLOW}مستخدم تجريبي:${NC}"
echo -e "     البريد: ${GREEN}demo@nexus.com${NC}"
echo -e "     كلمة المرور: ${GREEN}Demo123!${NC}"
echo ""
echo -e "${YELLOW}⚠️  تنبيه أمني:${NC} قم بتغيير كلمات المرور فوراً بعد الدخول!"
echo ""
echo -e "${BLUE}أوامر مفيدة:${NC}"
echo ""
echo -e "  عرض السجلات:           $COMPOSE_CMD logs -f"
echo -e "  إيقاف النظام:          $COMPOSE_CMD down"
echo -e "  إعادة التشغيل:         $COMPOSE_CMD restart"
echo -e "  حالة الخدمات:          $COMPOSE_CMD ps"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}       شكراً لاختيار Nexus ERP - نتمنى لكم التوفيق!         ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
