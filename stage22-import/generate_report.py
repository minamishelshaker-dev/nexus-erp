"""
Nexus ERP - Final Report Generation
====================================
Generates a comprehensive PDF report about the ERP system.
"""

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
import os

# Register fonts
pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Microsoft YaHei', '/usr/share/fonts/truetype/chinese/msyh.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))

# Register font families for bold text
registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman')

# Create styles
styles = getSampleStyleSheet()

# Cover styles
cover_title_style = ParagraphStyle(
    name='CoverTitle',
    fontName='Microsoft YaHei',
    fontSize=36,
    leading=44,
    alignment=TA_CENTER,
    spaceAfter=36,
    textColor=colors.HexColor('#1F4E79')
)

cover_subtitle_style = ParagraphStyle(
    name='CoverSubtitle',
    fontName='SimHei',
    fontSize=18,
    leading=24,
    alignment=TA_CENTER,
    spaceAfter=24,
    textColor=colors.HexColor('#4A5568')
)

# Heading styles
h1_style = ParagraphStyle(
    name='H1Style',
    fontName='Microsoft YaHei',
    fontSize=20,
    leading=28,
    alignment=TA_RIGHT,
    spaceBefore=24,
    spaceAfter=12,
    textColor=colors.HexColor('#1F4E79')
)

h2_style = ParagraphStyle(
    name='H2Style',
    fontName='Microsoft YaHei',
    fontSize=16,
    leading=22,
    alignment=TA_RIGHT,
    spaceBefore=18,
    spaceAfter=10,
    textColor=colors.HexColor('#2D3748')
)

h3_style = ParagraphStyle(
    name='H3Style',
    fontName='SimHei',
    fontSize=14,
    leading=20,
    alignment=TA_RIGHT,
    spaceBefore=12,
    spaceAfter=8,
    textColor=colors.HexColor('#4A5568')
)

# Body styles
body_style = ParagraphStyle(
    name='BodyStyle',
    fontName='SimHei',
    fontSize=11,
    leading=20,
    alignment=TA_RIGHT,
    spaceBefore=6,
    spaceAfter=6,
    wordWrap='CJK'
)

body_en_style = ParagraphStyle(
    name='BodyEnStyle',
    fontName='Times New Roman',
    fontSize=11,
    leading=18,
    alignment=TA_LEFT,
    spaceBefore=6,
    spaceAfter=6
)

# Table styles
table_header_style = ParagraphStyle(
    name='TableHeader',
    fontName='SimHei',
    fontSize=10,
    leading=14,
    alignment=TA_CENTER,
    textColor=colors.white
)

table_cell_style = ParagraphStyle(
    name='TableCell',
    fontName='SimHei',
    fontSize=10,
    leading=14,
    alignment=TA_CENTER,
    wordWrap='CJK'
)

def create_report():
    # Create document
    output_path = '/home/z/my-project/download/Nexus_ERP_Technical_Report.pdf'
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
        title='Nexus ERP Technical Report',
        author='Z.ai',
        creator='Z.ai',
        subject='Technical documentation for Nexus ERP system'
    )
    
    story = []
    
    # ========================================
    # Cover Page
    # ========================================
    story.append(Spacer(1, 100))
    story.append(Paragraph('Nexus ERP', cover_title_style))
    story.append(Spacer(1, 24))
    story.append(Paragraph('نظام تخطيط موارد المؤسسات المتكامل', cover_subtitle_style))
    story.append(Spacer(1, 48))
    story.append(Paragraph('Technical Report', ParagraphStyle(
        name='CoverEn',
        fontName='Times New Roman',
        fontSize=24,
        leading=32,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4A5568')
    )))
    story.append(Spacer(1, 100))
    story.append(Paragraph('التقرير التقني النهائي', ParagraphStyle(
        name='CoverAr',
        fontName='Microsoft YaHei',
        fontSize=16,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#718096')
    )))
    story.append(Spacer(1, 24))
    story.append(Paragraph('2024', ParagraphStyle(
        name='CoverDate',
        fontName='Times New Roman',
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#A0AEC0')
    )))
    story.append(PageBreak())
    
    # ========================================
    # Table of Contents
    # ========================================
    story.append(Paragraph('<b>فهرس المحتويات</b>', h1_style))
    story.append(Spacer(1, 18))
    
    toc_items = [
        ('1. نظرة عامة على المشروع', '3'),
        ('2. القرارات المعمارية', '4'),
        ('3. هيكل قاعدة البيانات', '7'),
        ('4. نظام المصادقة والصلاحيات', '9'),
        ('5. وحدات النظام', '11'),
        ('6. التحديات والحلول', '14'),
        ('7. أولويات التطوير', '16'),
        ('8. المقارنة مع المنافسين', '17'),
        ('9. الخلاصة', '19'),
    ]
    
    for item, page in toc_items:
        story.append(Paragraph(f'{item} ... {page}', body_style))
        story.append(Spacer(1, 6))
    
    story.append(PageBreak())
    
    # ========================================
    # Section 1: Overview
    # ========================================
    story.append(Paragraph('<b>1. نظرة عامة على المشروع</b>', h1_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph(
        'نظام Nexus ERP هو نظام متكامل لتخطيط موارد المؤسسات، صُمم ليكون بديلاً حديثاً ومتطوراً '
        'للأنظمة التقليدية مثل Odoo و SAP Business One. يوفر النظام حلاً شاملاً لإدارة جميع '
        'جوانب الأعمال التجارية من المبيعات والمشتريات إلى المحاسبة والموارد البشرية.',
        body_style
    ))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>1.1 الأهداف الرئيسية</b>', h2_style))
    story.append(Spacer(1, 8))
    
    objectives = [
        'بناء نظام ERP متكامل يدعم جميع العمليات الأساسية للمؤسسات',
        'توفير بنية تقنية حديثة قابلة للتوسع والتطوير المستمر',
        'دعم تعدد المستأجرين (Multi-tenancy) لخدمة عملاء متعددين',
        'تقديم واجهة مستخدم عصرية وسهلة الاستخدام',
        'ضمان الأمان العالي مع نظام صلاحيات دقيق ومرن',
    ]
    
    for obj in objectives:
        story.append(Paragraph(f'• {obj}', body_style))
        story.append(Spacer(1, 4))
    
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>1.2 التقنيات المستخدمة</b>', h2_style))
    story.append(Spacer(1, 8))
    
    tech_data = [
        [Paragraph('<b>المكون</b>', table_header_style), Paragraph('<b>التقنية</b>', table_header_style), Paragraph('<b>السبب</b>', table_header_style)],
        [Paragraph('Backend', table_cell_style), Paragraph('FastAPI + Python', table_cell_style), Paragraph('أداء عالي + توثيق تلقائي', table_cell_style)],
        [Paragraph('Frontend', table_cell_style), Paragraph('React 19 + TypeScript', table_cell_style), Paragraph('تجربة مستخدم متقدمة', table_cell_style)],
        [Paragraph('Database', table_cell_style), Paragraph('PostgreSQL', table_cell_style), Paragraph('موثوقية + دعم JSON', table_cell_style)],
        [Paragraph('ORM', table_cell_style), Paragraph('SQLAlchemy 2.0', table_cell_style), Paragraph('async + type safety', table_cell_style)],
        [Paragraph('Auth', table_cell_style), Paragraph('JWT + OAuth2', table_cell_style), Paragraph('أمان + مرونة', table_cell_style)],
        [Paragraph('Styling', table_cell_style), Paragraph('TailwindCSS', table_cell_style), Paragraph('سرعة تطوير + اتساق', table_cell_style)],
    ]
    
    tech_table = Table(tech_data, colWidths=[100, 140, 200])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'SimHei'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    story.append(tech_table)
    story.append(PageBreak())
    
    # ========================================
    # Section 2: Architectural Decisions
    # ========================================
    story.append(Paragraph('<b>2. القرارات المعمارية</b>', h1_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>2.1 البنية العامة</b>', h2_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph(
        'اعتمدنا بنية ثلاثية الطبقات (Three-tier Architecture) مع فصل واضح بين طبقة العرض '
        'وطبقة منطق الأعمال وطبقة البيانات. هذا الفصل يوفر مرونة عالية في التطوير والصيانة، '
        'ويمكّن من تطوير كل طبقة بشكل مستقل دون التأثير على الطبقات الأخرى.',
        body_style
    ))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>2.2 Multi-Tenancy (تعدد المستأجرين)</b>', h2_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph(
        'تم تصميم النظام لدعم تعدد المستأجرين من اليوم الأول، مما يسمح لكل مؤسسة بالعمل '
        'في بيئة معزولة تماماً مع بياناتها الخاصة. تم تنفيذ ذلك من خلال:',
        body_style
    ))
    story.append(Spacer(1, 8))
    
    multi_tenant_points = [
        'عزل البيانات على مستوى قاعدة البيانات (Schema-based isolation)',
        'تضمين tenant_id في جميع الجداول الأساسية',
        'فلترة تلقائية للطلبات بناءً على المستأجر الحالي',
        'إدارة مستقلة للمستخدمين والصلاحيات لكل مستأجر',
    ]
    
    for point in multi_tenant_points:
        story.append(Paragraph(f'• {point}', body_style))
        story.append(Spacer(1, 4))
    
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>2.3 API Design</b>', h2_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph(
        'تم تصميم API باتباع مبادئ RESTful مع الإصدار (Versioning) لضمان التوافق مع الإصدارات '
        'السابقة. جميع نقاط النهاية موثقة تلقائياً عبر OpenAPI (Swagger) المدمج في FastAPI.',
        body_style
    ))
    story.append(Spacer(1, 8))
    
    api_patterns = [
        ['GET /api/v1/customers', 'قائمة العملاء مع صفحات'],
        ['POST /api/v1/customers', 'إنشاء عميل جديد'],
        ['GET /api/v1/customers/{id}', 'تفاصيل عميل محدد'],
        ['PUT /api/v1/customers/{id}', 'تحديث بيانات عميل'],
        ['DELETE /api/v1/customers/{id}', 'حذف عميل (Soft Delete)'],
    ]
    
    api_data = [[Paragraph('<b>Endpoint</b>', table_header_style), Paragraph('<b>الوصف</b>', table_header_style)]]
    for endpoint, desc in api_patterns:
        api_data.append([Paragraph(endpoint, table_cell_style), Paragraph(desc, table_cell_style)])
    
    api_table = Table(api_data, colWidths=[200, 240])
    api_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'SimHei'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    story.append(api_table)
    story.append(PageBreak())
    
    # ========================================
    # Section 3: Database Schema
    # ========================================
    story.append(Paragraph('<b>3. هيكل قاعدة البيانات</b>', h1_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>3.1 الجداول الرئيسية</b>', h2_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph(
        'تم تصميم قاعدة البيانات وفق مبادئ التطبيع (Normalization) مع الحفاظ على الأداء. '
        'جميع الجداول ترث من BaseModel الذي يوفر حقولاً مشتركة مثل التواريخ والحذف الناعم.',
        body_style
    ))
    story.append(Spacer(1, 12))
    
    # Core tables
    story.append(Paragraph('<b>جداول المصادقة:</b>', h3_style))
    auth_tables = ['users', 'roles', 'permissions', 'user_roles', 'role_permissions', 'user_sessions']
    story.append(Paragraph(' • '.join(auth_tables), body_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph('<b>جداول CRM:</b>', h3_style))
    crm_tables = ['customers', 'contacts', 'customer_addresses', 'leads', 'opportunities', 'customer_interactions']
    story.append(Paragraph(' • '.join(crm_tables), body_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph('<b>جداول المخزون:</b>', h3_style))
    inv_tables = ['products', 'product_categories', 'warehouses', 'warehouse_locations', 'stock_quantities', 'stock_moves']
    story.append(Paragraph(' • '.join(inv_tables), body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>3.2 العلاقات الرئيسية</b>', h2_style))
    story.append(Spacer(1, 8))
    
    relationships = [
        ['User → Roles', 'Many-to-Many', 'صلاحيات المستخدم'],
        ['Role → Permissions', 'Many-to-Many', 'صلاحيات الدور'],
        ['Customer → Contacts', 'One-to-Many', 'جهات اتصال العميل'],
        ['Customer → Addresses', 'One-to-Many', 'عناوين العميل'],
        ['Product → Stock', 'One-to-Many', 'رصيد المنتج بكل مستودع'],
        ['Product → BOM', 'One-to-Many', 'قوائم المواد'],
    ]
    
    rel_data = [[Paragraph('<b>العلاقة</b>', table_header_style), Paragraph('<b>النوع</b>', table_header_style), Paragraph('<b>الوصف</b>', table_header_style)]]
    for rel in relationships:
        rel_data.append([Paragraph(rel[0], table_cell_style), Paragraph(rel[1], table_cell_style), Paragraph(rel[2], table_cell_style)])
    
    rel_table = Table(rel_data, colWidths=[150, 120, 170])
    rel_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'SimHei'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    story.append(rel_table)
    story.append(PageBreak())
    
    # ========================================
    # Section 4: Authentication & Authorization
    # ========================================
    story.append(Paragraph('<b>4. نظام المصادقة والصلاحيات</b>', h1_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>4.1 المصادقة (Authentication)</b>', h2_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph(
        'يعتمد النظام على JWT (JSON Web Tokens) للمصادقة مع دعم Refresh Tokens للجلسات '
        'الطويلة. يتم توليد Access Token بصلاحية محدودة (30 دقيقة افتراضياً) و Refresh Token '
        'بصلاحية أطول (7 أيام). هذا يوفر توازناً بين الأمان وتجربة المستخدم.',
        body_style
    ))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>4.2 نظام RBAC (Role-Based Access Control)</b>', h2_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph(
        'تم تصميم نظام صلاحيات متقدم يدعم التسلسل الهرمي للأدوار مع صلاحيات دقيقة على مستوى '
        'الإجراء. يتم تنظيم الصلاحيات وفق النمط: module.resource.action',
        body_style
    ))
    story.append(Spacer(1, 8))
    
    rbac_examples = [
        ['crm.customer.create', 'إنشاء عميل جديد'],
        ['sales.invoice.approve', 'اعتماد فاتورة'],
        ['inventory.stock.adjust', 'تعديل رصيد المخزون'],
        ['accounting.journal.post', 'ترحيل قيد'],
        ['hr.employee.view', 'عرض بيانات موظف'],
    ]
    
    rbac_data = [[Paragraph('<b>الصلاحية</b>', table_header_style), Paragraph('<b>الوصف</b>', table_header_style)]]
    for perm in rbac_examples:
        rbac_data.append([Paragraph(perm[0], table_cell_style), Paragraph(perm[1], table_cell_style)])
    
    rbac_table = Table(rbac_data, colWidths=[200, 240])
    rbac_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'SimHei'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    story.append(rbac_table)
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>4.3 ميزات الأمان</b>', h2_style))
    story.append(Spacer(1, 8))
    
    security_features = [
        'تشفير كلمات المرور بـ bcrypt مع cost factor = 12',
        'حماية من SQL Injection عبر SQLAlchemy ORM',
        'تتبع جلسات المستخدمين مع إمكانية الإلغاء',
        'قفل الحساب بعد محاولات فاشلة متتالية',
        'تسجيل جميع الأنشطة للمراجعة الأمنية',
        'دعم Two-Factor Authentication (اختياري)',
    ]
    
    for feature in security_features:
        story.append(Paragraph(f'• {feature}', body_style))
        story.append(Spacer(1, 4))
    
    story.append(PageBreak())
    
    # ========================================
    # Section 5: System Modules
    # ========================================
    story.append(Paragraph('<b>5. وحدات النظام</b>', h1_style))
    story.append(Spacer(1, 12))
    
    modules = [
        ('CRM', 'إدارة علاقات العملاء', 'العملاء، الفرص، العملاء المحتملين، التفاعلات'),
        ('المبيعات', 'Sales & Invoicing', 'عروض الأسعار، أوامر البيع، الفواتير الإلكترونية'),
        ('المخزون', 'Inventory Management', 'المنتجات، المستودعات، حركات المخزون'),
        ('المشتريات', 'Purchasing', 'أوامر الشراء، الموردين، الاستلام'),
        ('المحاسبة', 'Accounting', 'دفتر الأستاذ، القيود، التقارير المالية'),
        ('الموارد البشرية', 'HR Management', 'الموظفين، الحضور، الرواتب'),
        ('المشاريع', 'Project Management', 'المهام، الجداول الزمنية'),
        ('التصنيع', 'Manufacturing (MRP)', 'قوائم المواد، أوامر الإنتاج'),
        ('POS', 'Point of Sale', 'واجهة البيع بالتجزئة'),
        ('التقارير', 'Reports & Analytics', 'لوحات التحكم، التقارير المخصصة'),
    ]
    
    for code, name, features in modules:
        story.append(Paragraph(f'<b>{code} - {name}</b>', h3_style))
        story.append(Paragraph(features, body_style))
        story.append(Spacer(1, 8))
    
    story.append(PageBreak())
    
    # ========================================
    # Section 6: Challenges & Solutions
    # ========================================
    story.append(Paragraph('<b>6. التحديات والحلول</b>', h1_style))
    story.append(Spacer(1, 12))
    
    challenges = [
        ('تعدد المستأجرين', 
         'ضمان عزل البيانات الكامل بين المستأجرين',
         'اعتماد Schema-based isolation مع tenant_id في جميع الجداول'),
        ('الأداء', 
         'ضمان استجابة سريعة مع بيانات كبيرة',
         'استخدام Async/Await، الفهرسة الذكية، التخزين المؤقت بـ Redis'),
        ('الأمان', 
         'حماية البيانات الحساسة',
         'JWT مع Refresh Tokens، RBAC دقيق، تسجيل كامل للأنشطة'),
        ('التوسع', 
         'القدرة على إضافة وحدات جديدة',
         'بنية Modular، API versioning، Plugin architecture'),
    ]
    
    for title, challenge, solution in challenges:
        story.append(Paragraph(f'<b>{title}</b>', h3_style))
        story.append(Paragraph(f'التحدي: {challenge}', body_style))
        story.append(Paragraph(f'الحل: {solution}', body_style))
        story.append(Spacer(1, 12))
    
    story.append(PageBreak())
    
    # ========================================
    # Section 7: Development Priorities
    # ========================================
    story.append(Paragraph('<b>7. أولويات التطوير</b>', h1_style))
    story.append(Spacer(1, 12))
    
    priorities = [
        ('1', 'عالي', 'إكمال وحدة المبيعات', 'الفواتير، أوامر البيع'),
        ('2', 'عالي', 'تطوير وحدة المخزون', 'حركات المخزون، الجرد'),
        ('3', 'متوسط', 'وحدة المحاسبة', 'القيود، التقارير المالية'),
        ('4', 'متوسط', 'وحدة المشتريات', 'أوامر الشراء، الموردين'),
        ('5', 'منخفض', 'وحدة التصنيع', 'BOM، أوامر الإنتاج'),
    ]
    
    priority_data = [[Paragraph('<b>#</b>', table_header_style), Paragraph('<b>الأولوية</b>', table_header_style), 
                      Paragraph('<b>الوحدة</b>', table_header_style), Paragraph('<b>المكونات</b>', table_header_style)]]
    for p in priorities:
        priority_data.append([Paragraph(p[0], table_cell_style), Paragraph(p[1], table_cell_style),
                             Paragraph(p[2], table_cell_style), Paragraph(p[3], table_cell_style)])
    
    priority_table = Table(priority_data, colWidths=[40, 80, 160, 160])
    priority_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'SimHei'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    story.append(priority_table)
    story.append(PageBreak())
    
    # ========================================
    # Section 8: Comparison with Competitors
    # ========================================
    story.append(Paragraph('<b>8. المقارنة مع المنافسين</b>', h1_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph(
        'تم تصميم Nexus ERP لمعالجة نقاط الضعف في الأنظمة الحالية مع الحفاظ على نقاط القوة:',
        body_style
    ))
    story.append(Spacer(1, 12))
    
    comparison = [
        ['الميزة', 'Nexus ERP', 'Odoo', 'SAP B1'],
        ['التقنية', 'حديثة (FastAPI+React)', 'Python (Legacy)', 'Proprietary'],
        ['الأداء', 'Async عالي', 'متوسط', 'جيد'],
        ['Multi-tenancy', 'مدمج', 'إضافي', 'محدود'],
        ['التكلفة', 'مفتوح المصدر', 'Community/Edition', 'مرتفعة'],
        ['التخصيص', 'مرن جداً', 'معقد', 'محدود'],
        ['API', 'OpenAPI تلقائي', 'متوفر', 'متوفر'],
        ['تجربة المستخدم', 'عصرية', 'تقليدية', 'تقليدية'],
    ]
    
    comp_data = []
    for i, row in enumerate(comparison):
        if i == 0:
            comp_data.append([Paragraph(f'<b>{cell}</b>', table_header_style) for cell in row])
        else:
            comp_data.append([Paragraph(cell, table_cell_style) for cell in row])
    
    comp_table = Table(comp_data, colWidths=[120, 120, 100, 100])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'SimHei'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('<b>8.1 نقاط التفوق</b>', h2_style))
    story.append(Spacer(1, 8))
    
    advantages = [
        'بنية تقنية حديثة مع أداء أعلى بفضل Async/Await',
        'توثيق API تلقائي يسهل التكامل مع الأنظمة الأخرى',
        'دعم Multi-tenancy من البداية دون تعقيد',
        'واجهة مستخدم عصرية تعمل على جميع الأجهزة',
        'تكلفة منخفضة كمشروع مفتوح المصدر',
        'سهولة التخصيص والتطوير بفضل البنية Modular',
    ]
    
    for adv in advantages:
        story.append(Paragraph(f'✓ {adv}', body_style))
        story.append(Spacer(1, 4))
    
    story.append(PageBreak())
    
    # ========================================
    # Section 9: Conclusion
    # ========================================
    story.append(Paragraph('<b>9. الخلاصة</b>', h1_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph(
        'يمثل مشروع Nexus ERP خطوة مهمة نحو بناء نظام تخطيط موارد مؤسسات حديث ومتكامل. '
        'تم تصميم النظام بعناية لمعالجة التحديات التقنية والعملية التي تواجه المؤسسات، '
        'مع التركيز على الأداء والأمان وقابلية التوسع.',
        body_style
    ))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph(
        'تم خلال هذا المشروع إنشاء البنية الأساسية الكاملة بما يشمل نظام المصادقة المتقدم، '
        'وقاعدة البيانات المنظمة، وواجهات API الموثقة، والواجهة الأمامية العصرية. '
        'كما تم وضع خطة واضحة لتطوير الوحدات المتبقية وفق أولويات محددة.',
        body_style
    ))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph(
        'مع الاستمرار في التطوير، سيصبح Nexus ERP بديلاً قوياً ومجدياً economically للأنظمة '
        'التجارية الحالية، مع مرونة أكبر في التخصيص وتكلفة أقل في التشغيل.',
        body_style
    ))
    
    # Build PDF
    doc.build(story)
    print(f"PDF created successfully: {output_path}")
    return output_path

if __name__ == '__main__':
    create_report()
