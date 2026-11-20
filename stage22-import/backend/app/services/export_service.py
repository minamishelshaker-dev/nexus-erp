"""
Nexus ERP - Export Service
==========================

Comprehensive export service including:
- PDF generation with reportlab
- Excel generation with openpyxl
- CSV export
- Custom templates
- Scheduled exports
- Multi-format support
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union, BinaryIO
from uuid import UUID, uuid4
from io import BytesIO, StringIO
import logging
import asyncio
import json
import csv

# PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak, Image, Flowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Excel generation
from openpyxl import Workbook
from openpyxl.styles import (
    Font, Fill, PatternFill, Border, Side, 
    Alignment, NamedStyle
)
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList

from dataclasses import dataclass, field
from enum import Enum
import os

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Export format types."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"


class PageOrientation(str, Enum):
    """Page orientation for PDF."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


@dataclass
class ExportColumn:
    """Column definition for export."""
    field: str
    title: str
    width: Optional[int] = None
    format: Optional[str] = None  # number, currency, date, percent
    align: str = "left"
    total: bool = False


@dataclass
class ExportConfig:
    """Export configuration."""
    title: str
    subtitle: Optional[str] = None
    columns: List[ExportColumn] = field(default_factory=list)
    orientation: PageOrientation = PageOrientation.PORTRAIT
    page_size: str = "A4"
    include_header: bool = True
    include_totals: bool = True
    include_timestamp: bool = True
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    show_grid: bool = True
    header_color: str = "#4A90D9"
    alternate_row_colors: bool = True


class ExportService:
    """
    Export Service
    
    Provides comprehensive export capabilities:
    - PDF generation
    - Excel workbooks
    - CSV files
    - Custom templates
    - Scheduled exports
    """
    
    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
        self._styles = self._init_styles()
        self._excel_styles = self._init_excel_styles()
    
    def _init_styles(self) -> Dict[str, ParagraphStyle]:
        """Initialize PDF styles."""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor('#333333')
        ))
        
        # Subtitle style
        styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            textColor=colors.HexColor('#666666')
        ))
        
        # Header style
        styles.add(ParagraphStyle(
            name='CustomHeader',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.white,
            alignment=TA_CENTER
        ))
        
        # Cell style
        styles.add(ParagraphStyle(
            name='CustomCell',
            parent=styles['Normal'],
            fontSize=9,
            leading=12
        ))
        
        # Footer style
        styles.add(ParagraphStyle(
            name='CustomFooter',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#999999'),
            alignment=TA_CENTER
        ))
        
        return styles
    
    def _init_excel_styles(self) -> Dict[str, NamedStyle]:
        """Initialize Excel styles."""
        styles = {}
        
        # Header style
        header_style = NamedStyle(name="header_style")
        header_style.font = Font(bold=True, color="FFFFFF", size=11)
        header_style.fill = PatternFill(start_color="4A90D9", end_color="4A90D9", fill_type="solid")
        header_style.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        header_style.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        styles['header'] = header_style
        
        # Data style
        data_style = NamedStyle(name="data_style")
        data_style.alignment = Alignment(horizontal="left", vertical="center")
        data_style.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        styles['data'] = data_style
        
        # Number style
        number_style = NamedStyle(name="number_style")
        number_style.alignment = Alignment(horizontal="right", vertical="center")
        number_style.number_format = '#,##0.00'
        styles['number'] = number_style
        
        # Currency style
        currency_style = NamedStyle(name="currency_style")
        currency_style.alignment = Alignment(horizontal="right", vertical="center")
        currency_style.number_format = '#,##0.00 "SAR"'
        styles['currency'] = currency_style
        
        # Date style
        date_style = NamedStyle(name="date_style")
        date_style.alignment = Alignment(horizontal="center", vertical="center")
        date_style.number_format = 'YYYY-MM-DD'
        styles['date'] = date_style
        
        # Total style
        total_style = NamedStyle(name="total_style")
        total_style.font = Font(bold=True)
        total_style.fill = PatternFill(start_color="E8E8E8", end_color="E8E8E8", fill_type="solid")
        styles['total'] = total_style
        
        return styles
    
    # ========================================
    # Main Export Method
    # ========================================
    
    async def export_data(
        self,
        data: List[Dict[str, Any]],
        config: ExportConfig,
        format: ExportFormat
    ) -> BinaryIO:
        """
        Export data in specified format.
        
        Args:
            data: Data to export
            config: Export configuration
            format: Export format
            
        Returns:
            Binary file-like object
        """
        if format == ExportFormat.PDF:
            return await self.export_pdf(data, config)
        elif format == ExportFormat.EXCEL:
            return await self.export_excel(data, config)
        elif format == ExportFormat.CSV:
            return await self.export_csv(data, config)
        elif format == ExportFormat.JSON:
            return await self.export_json(data, config)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    # ========================================
    # PDF Export
    # ========================================
    
    async def export_pdf(
        self,
        data: List[Dict[str, Any]],
        config: ExportConfig
    ) -> BinaryIO:
        """Generate PDF export."""
        buffer = BytesIO()
        
        # Determine page size and orientation
        if config.page_size == "A4":
            page_size = A4
        else:
            page_size = letter
        
        if config.orientation == PageOrientation.LANDSCAPE:
            page_size = landscape(page_size)
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )
        
        # Build content
        elements = []
        
        # Title
        elements.append(Paragraph(config.title, self._styles['CustomTitle']))
        
        # Subtitle
        if config.subtitle:
            elements.append(Paragraph(config.subtitle, self._styles['CustomSubtitle']))
        
        # Company and timestamp
        header_info = []
        if config.company_name:
            header_info.append(config.company_name)
        if config.include_timestamp:
            header_info.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        if header_info:
            elements.append(Paragraph(" | ".join(header_info), self._styles['CustomFooter']))
            elements.append(Spacer(1, 0.3*inch))
        
        # Build table
        table_data = []
        
        # Header row
        if config.include_header:
            header_row = [Paragraph(col.title, self._styles['CustomHeader']) for col in config.columns]
            table_data.append(header_row)
        
        # Data rows
        totals = {col.field: Decimal("0") for col in config.columns if col.total}
        
        for row in data:
            data_row = []
            for col in config.columns:
                value = row.get(col.field)
                formatted_value = self._format_value(value, col.format)
                data_row.append(Paragraph(str(formatted_value), self._styles['CustomCell']))
                
                if col.total and isinstance(value, (int, float, Decimal)):
                    totals[col.field] += Decimal(str(value))
            
            table_data.append(data_row)
        
        # Totals row
        if config.include_totals and totals:
            total_row = []
            for col in config.columns:
                if col.total:
                    value = totals[col.field]
                    formatted = self._format_value(value, col.format)
                    total_row.append(Paragraph(f"<b>{formatted}</b>", self._styles['CustomCell']))
                elif col == config.columns[0]:
                    total_row.append(Paragraph("<b>Total</b>", self._styles['CustomCell']))
                else:
                    total_row.append(Paragraph("", self._styles['CustomCell']))
            table_data.append(total_row)
        
        # Calculate column widths
        available_width = doc.width
        col_widths = self._calculate_column_widths(config.columns, available_width)
        
        # Create table
        table = Table(table_data, colWidths=col_widths)
        
        # Apply styles
        style_commands = [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        # Header background
        if config.header_color:
            style_commands.append(
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(config.header_color))
            )
            style_commands.append(
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white)
            )
        
        # Grid
        if config.show_grid:
            style_commands.extend([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor(config.header_color)),
            ])
        
        # Alternate row colors
        if config.alternate_row_colors and len(table_data) > 1:
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    style_commands.append(
                        ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F5F5F5'))
                    )
        
        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        
        # Build PDF
        doc.build(elements, onFirstPage=self._add_page_footer, onLaterPages=self._add_page_footer)
        
        buffer.seek(0)
        return buffer
    
    def _add_page_footer(self, canvas, doc):
        """Add page footer to PDF."""
        canvas.saveState()
        footer = f"Page {doc.page} | Nexus ERP | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#999999'))
        canvas.drawCentredString(doc.width / 2 + doc.leftMargin, 0.5 * inch, footer)
        canvas.restoreState()
    
    def _calculate_column_widths(
        self,
        columns: List[ExportColumn],
        available_width: float
    ) -> List[float]:
        """Calculate column widths for PDF table."""
        total_weight = 0
        weights = []
        
        for col in columns:
            if col.width:
                weights.append(col.width)
            else:
                # Default weight based on format
                if col.format == "currency" or col.format == "number":
                    weights.append(15)
                elif col.format == "date":
                    weights.append(12)
                else:
                    weights.append(20)
        
        total_weight = sum(weights)
        return [w / total_weight * available_width for w in weights]
    
    # ========================================
    # Excel Export
    # ========================================
    
    async def export_excel(
        self,
        data: List[Dict[str, Any]],
        config: ExportConfig
    ) -> BinaryIO:
        """Generate Excel export."""
        buffer = BytesIO()
        wb = Workbook()
        ws = wb.active
        ws.title = config.title[:31]  # Excel sheet name limit
        
        current_row = 1
        
        # Title
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=len(config.columns))
        ws.cell(row=current_row, column=1, value=config.title)
        ws.cell(row=current_row, column=1).font = Font(bold=True, size=16)
        ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="center")
        current_row += 1
        
        # Subtitle
        if config.subtitle:
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=len(config.columns))
            ws.cell(row=current_row, column=1, value=config.subtitle)
            ws.cell(row=current_row, column=1).font = Font(italic=True, size=11)
            ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="center")
            current_row += 1
        
        # Company and timestamp
        header_info = []
        if config.company_name:
            header_info.append(config.company_name)
        if config.include_timestamp:
            header_info.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        if header_info:
            ws.cell(row=current_row, column=1, value=" | ".join(header_info))
            ws.cell(row=current_row, column=1).font = Font(size=9, italic=True)
            current_row += 1
        
        current_row += 1  # Empty row
        
        # Header row
        if config.include_header:
            for col_idx, col in enumerate(config.columns, start=1):
                cell = ws.cell(row=current_row, column=col_idx, value=col.title)
                cell.style = self._excel_styles['header']
                
                # Set column width
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = col.width or 15
            
            current_row += 1
        
        # Data rows
        totals = {col.field: Decimal("0") for col in config.columns if col.total}
        
        for row_idx, row in enumerate(data):
            for col_idx, col in enumerate(config.columns, start=1):
                value = row.get(col.field)
                cell = ws.cell(row=current_row, column=col_idx)
                
                # Set value
                cell.value = value
                
                # Apply style based on format
                if col.format == "currency":
                    cell.style = self._excel_styles['currency']
                elif col.format == "number":
                    cell.style = self._excel_styles['number']
                elif col.format == "date":
                    cell.style = self._excel_styles['date']
                else:
                    cell.style = self._excel_styles['data']
                
                # Alignment
                if col.align == "right":
                    cell.alignment = Alignment(horizontal="right")
                elif col.align == "center":
                    cell.alignment = Alignment(horizontal="center")
                
                # Accumulate totals
                if col.total and isinstance(value, (int, float, Decimal)):
                    totals[col.field] += Decimal(str(value))
            
            # Alternate row colors
            if config.alternate_row_colors and row_idx % 2 == 1:
                for col_idx in range(1, len(config.columns) + 1):
                    ws.cell(row=current_row, column=col_idx).fill = PatternFill(
                        start_color="F5F5F5", end_color="F5F5F5", fill_type="solid"
                    )
            
            current_row += 1
        
        # Totals row
        if config.include_totals and totals:
            for col_idx, col in enumerate(config.columns, start=1):
                cell = ws.cell(row=current_row, column=col_idx)
                
                if col.total:
                    cell.value = float(totals[col.field])
                    cell.style = self._excel_styles['total']
                    if col.format == "currency":
                        cell.number_format = '#,##0.00 "SAR"'
                elif col == config.columns[0]:
                    cell.value = "Total"
                    cell.style = self._excel_styles['total']
                else:
                    cell.style = self._excel_styles['total']
            
            current_row += 1
        
        # Freeze header row
        header_row = 4 if config.subtitle else 3
        ws.freeze_panes = f"A{header_row}"
        
        wb.save(buffer)
        buffer.seek(0)
        return buffer
    
    # ========================================
    # CSV Export
    # ========================================
    
    async def export_csv(
        self,
        data: List[Dict[str, Any]],
        config: ExportConfig
    ) -> BinaryIO:
        """Generate CSV export."""
        buffer = BytesIO()
        
        # Use StringIO for text, then encode
        text_buffer = StringIO()
        
        # Configure CSV writer
        writer = csv.writer(text_buffer, quoting=csv.QUOTE_NONNUMERIC)
        
        # Header row
        if config.include_header:
            writer.writerow([col.title for col in config.columns])
        
        # Data rows
        totals = {col.field: Decimal("0") for col in config.columns if col.total}
        
        for row in data:
            csv_row = []
            for col in config.columns:
                value = row.get(col.field)
                formatted = self._format_value(value, col.format)
                csv_row.append(formatted)
                
                if col.total and isinstance(value, (int, float, Decimal)):
                    totals[col.field] += Decimal(str(value))
            
            writer.writerow(csv_row)
        
        # Totals row
        if config.include_totals and totals:
            total_row = []
            for col in config.columns:
                if col.total:
                    total_row.append(self._format_value(totals[col.field], col.format))
                elif col == config.columns[0]:
                    total_row.append("Total")
                else:
                    total_row.append("")
            writer.writerow(total_row)
        
        # Encode and write to buffer
        buffer.write(text_buffer.getvalue().encode('utf-8-sig'))  # BOM for Excel compatibility
        buffer.seek(0)
        return buffer
    
    # ========================================
    # JSON Export
    # ========================================
    
    async def export_json(
        self,
        data: List[Dict[str, Any]],
        config: ExportConfig
    ) -> BinaryIO:
        """Generate JSON export."""
        buffer = BytesIO()
        
        export_data = {
            "title": config.title,
            "subtitle": config.subtitle,
            "exported_at": datetime.now().isoformat(),
            "tenant_id": str(self.tenant_id),
            "columns": [
                {
                    "field": col.field,
                    "title": col.title,
                    "format": col.format
                }
                for col in config.columns
            ],
            "row_count": len(data),
            "data": data
        }
        
        # Calculate totals
        totals = {}
        for col in config.columns:
            if col.total:
                totals[col.field] = sum(
                    Decimal(str(row.get(col.field, 0)))
                    for row in data
                    if isinstance(row.get(col.field), (int, float, Decimal))
                )
        
        if totals:
            export_data["totals"] = {k: float(v) for k, v in totals.items()}
        
        buffer.write(json.dumps(export_data, indent=2, default=str).encode('utf-8'))
        buffer.seek(0)
        return buffer
    
    # ========================================
    # Report-specific Exports
    # ========================================
    
    async def export_balance_sheet(
        self,
        data: Dict[str, Any],
        format: ExportFormat,
        company_name: Optional[str] = None
    ) -> BinaryIO:
        """Export balance sheet report."""
        # Flatten data for export
        rows = []
        
        # Assets
        rows.append({"section": "ASSETS", "account": "", "amount": ""})
        for account in data.get("assets", {}).get("accounts", []):
            rows.append({
                "section": "",
                "account": f"{account['code']} - {account['name']}",
                "amount": account["balance"]
            })
        rows.append({
            "section": "",
            "account": "Total Assets",
            "amount": data.get("total_assets", 0)
        })
        
        # Liabilities
        rows.append({"section": "LIABILITIES", "account": "", "amount": ""})
        for account in data.get("liabilities", {}).get("accounts", []):
            rows.append({
                "section": "",
                "account": f"{account['code']} - {account['name']}",
                "amount": account["balance"]
            })
        rows.append({
            "section": "",
            "account": "Total Liabilities",
            "amount": data.get("total_liabilities", 0)
        })
        
        # Equity
        rows.append({"section": "EQUITY", "account": "", "amount": ""})
        for account in data.get("equity", {}).get("accounts", []):
            rows.append({
                "section": "",
                "account": f"{account['code']} - {account['name']}",
                "amount": account["balance"]
            })
        rows.append({
            "section": "",
            "account": "Total Equity",
            "amount": data.get("total_equity", 0)
        })
        
        config = ExportConfig(
            title="Balance Sheet",
            subtitle=f"As of {data.get('date', date.today())}",
            columns=[
                ExportColumn(field="section", title="Section", width=15),
                ExportColumn(field="account", title="Account", width=40),
                ExportColumn(field="amount", title="Amount", width=20, format="currency", align="right")
            ],
            company_name=company_name,
            include_totals=False
        )
        
        return await self.export_data(rows, config, format)
    
    async def export_profit_loss(
        self,
        data: Dict[str, Any],
        format: ExportFormat,
        company_name: Optional[str] = None
    ) -> BinaryIO:
        """Export profit & loss statement."""
        rows = []
        
        # Revenue
        rows.append({"section": "REVENUE", "account": "", "amount": ""})
        for account in data.get("revenue", {}).get("lines", []):
            rows.append({
                "section": "",
                "account": f"{account['account_code']} - {account['account_name']}",
                "amount": account["amount"]
            })
        rows.append({
            "section": "",
            "account": "Total Revenue",
            "amount": data.get("revenue", {}).get("total", 0)
        })
        
        # Expenses
        rows.append({"section": "EXPENSES", "account": "", "amount": ""})
        for account in data.get("expenses", {}).get("lines", []):
            rows.append({
                "section": "",
                "account": f"{account['account_code']} - {account['account_name']}",
                "amount": account["amount"]
            })
        rows.append({
            "section": "",
            "account": "Total Expenses",
            "amount": data.get("expenses", {}).get("total", 0)
        })
        
        # Net Income
        rows.append({"section": "", "account": "", "amount": ""})
        rows.append({
            "section": "",
            "account": "NET INCOME",
            "amount": data.get("net_income", 0)
        })
        
        period = data.get("period", {})
        subtitle = f"Period: {period.get('date_from')} to {period.get('date_to')}"
        
        config = ExportConfig(
            title="Profit & Loss Statement",
            subtitle=subtitle,
            columns=[
                ExportColumn(field="section", title="Section", width=15),
                ExportColumn(field="account", title="Account", width=40),
                ExportColumn(field="amount", title="Amount", width=20, format="currency", align="right")
            ],
            company_name=company_name,
            include_totals=False
        )
        
        return await self.export_data(rows, config, format)
    
    async def export_sales_analysis(
        self,
        data: Dict[str, Any],
        format: ExportFormat,
        company_name: Optional[str] = None
    ) -> BinaryIO:
        """Export sales analysis report."""
        rows = []
        
        # Summary
        summary = data.get("summary", {})
        rows.append({"metric": "Total Sales", "value": summary.get("total_sales", 0)})
        rows.append({"metric": "Total Returns", "value": summary.get("total_returns", 0)})
        rows.append({"metric": "Net Sales", "value": summary.get("net_sales", 0)})
        rows.append({"metric": "Invoice Count", "value": summary.get("invoice_count", 0)})
        rows.append({"metric": "Average Order Value", "value": summary.get("average_order_value", 0)})
        
        rows.append({"metric": "", "value": ""})  # Empty row
        
        # Breakdown
        rows.append({"metric": "BREAKDOWN", "value": ""})
        for item in data.get("breakdown", [])[:50]:  # Limit to 50 items
            rows.append({
                "metric": item.get("key", "Unknown"),
                "value": item.get("net_sales", 0)
            })
        
        period = data.get("period", {})
        subtitle = f"Period: {period.get('date_from')} to {period.get('date_to')}"
        
        config = ExportConfig(
            title="Sales Analysis Report",
            subtitle=subtitle,
            columns=[
                ExportColumn(field="metric", title="Metric", width=30),
                ExportColumn(field="value", title="Value", width=20, format="currency", align="right")
            ],
            company_name=company_name,
            include_totals=False
        )
        
        return await self.export_data(rows, config, format)
    
    async def export_inventory_valuation(
        self,
        data: Dict[str, Any],
        format: ExportFormat,
        company_name: Optional[str] = None
    ) -> BinaryIO:
        """Export inventory valuation report."""
        rows = []
        
        for item in data.get("valuation", []):
            rows.append({
                "sku": item.get("sku", ""),
                "name": item.get("name", ""),
                "category": item.get("category", ""),
                "quantity": item.get("quantity", 0),
                "unit_cost": item.get("unit_cost", 0),
                "total_value": item.get("total_value", 0)
            })
        
        config = ExportConfig(
            title="Inventory Valuation Report",
            subtitle=f"As of {data.get('as_of_date')} - Method: {data.get('valuation_method')}",
            columns=[
                ExportColumn(field="sku", title="SKU", width=15),
                ExportColumn(field="name", title="Product Name", width=30),
                ExportColumn(field="category", title="Category", width=15),
                ExportColumn(field="quantity", title="Quantity", width=12, format="number", align="right"),
                ExportColumn(field="unit_cost", title="Unit Cost", width=15, format="currency", align="right"),
                ExportColumn(field="total_value", title="Total Value", width=15, format="currency", align="right", total=True)
            ],
            company_name=company_name,
            include_totals=True
        )
        
        return await self.export_data(rows, config, format)
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _format_value(
        self,
        value: Any,
        format: Optional[str]
    ) -> str:
        """Format a value for display."""
        if value is None:
            return ""
        
        if format == "currency":
            if isinstance(value, (int, float, Decimal)):
                return f"SAR {float(value):,.2f}"
            return str(value)
        elif format == "number":
            if isinstance(value, (int, float, Decimal)):
                return f"{float(value):,.2f}"
            return str(value)
        elif format == "percent":
            if isinstance(value, (int, float, Decimal)):
                return f"{float(value):.1f}%"
            return str(value)
        elif format == "date":
            if isinstance(value, (date, datetime)):
                return value.strftime("%Y-%m-%d")
            return str(value)
        elif format == "datetime":
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d %H:%M")
            return str(value)
        else:
            return str(value)
    
    # ========================================
    # Scheduled Exports
    # ========================================
    
    async def schedule_export(
        self,
        report_type: str,
        format: ExportFormat,
        schedule: str,  # cron expression
        recipients: List[str],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Schedule a recurring export."""
        # Would create a scheduled task record
        return {
            "id": str(uuid4()),
            "report_type": report_type,
            "format": format.value,
            "schedule": schedule,
            "recipients": recipients,
            "parameters": parameters,
            "is_active": True
        }
    
    async def execute_scheduled_export(
        self,
        export_id: UUID
    ) -> Dict[str, Any]:
        """Execute a scheduled export."""
        # Would run the export and send to recipients
        return {
            "export_id": str(export_id),
            "executed_at": datetime.utcnow().isoformat(),
            "status": "completed"
        }
