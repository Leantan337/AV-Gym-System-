from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from authentication.permissions import IsStaffOrAdmin, IsTrainerOrHigher, IsOwnerOrStaff
from authentication.decorators import role_required
from django.db.models import Sum, Count
from django.utils import timezone
from django.http import FileResponse
import os
import tempfile
import zipfile
from datetime import timedelta

# PDF generation with ReportLab instead of WeasyPrint
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from .models import Invoice, InvoiceTemplate
from .serializers import (
    InvoiceTemplateSerializer,
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    CreateInvoiceSerializer,
    UpdateInvoiceSerializer,
)


class InvoiceTemplateViewSet(viewsets.ModelViewSet):
    queryset = InvoiceTemplate.objects.all()
    serializer_class = InvoiceTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTrainerOrHigher]  # Base permission

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'mark_paid']:
            self.permission_classes = [IsStaffOrAdmin]  # Only staff and admin can modify
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [IsTrainerOrHigher]  # Trainers can view
        elif self.action == 'my_invoices':
            self.permission_classes = [IsOwnerOrStaff]  # Members can view their own
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        # Members can only see their own invoices
        if request.user.is_member_role():
            queryset = self.get_queryset().filter(member__user=request.user)
        else:
            queryset = self.get_queryset()

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Members can only retrieve their own invoices
        if request.user.is_member_role() and instance.member.user != request.user:
            return Response(
                {"detail": "You do not have permission to view this invoice."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_invoices(self, request):
        """Endpoint for members to get their own invoices"""
        invoices = self.get_queryset().filter(member__user=request.user)
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @role_required(['staff', 'admin'])
    def mark_paid(self, request, pk=None):
        """Mark invoice as paid - only staff and admin"""
        invoice = self.get_object()
        invoice.status = 'paid'
        invoice.save()
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)

    queryset = Invoice.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['number', 'member__full_name', 'member__email']

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateInvoiceSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateInvoiceSerializer
        elif self.action == 'retrieve':
            return InvoiceDetailSerializer
        return InvoiceListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Status filter
        status = self.request.query_params.get('status')
        if status and status != 'all':
            queryset = queryset.filter(status=status)

        # Date range filter
        date_range = self.request.query_params.get('dateRange')
        if date_range:
            today = timezone.now().date()
            if date_range == 'today':
                queryset = queryset.filter(created_at__date=today)
            elif date_range == 'week':
                week_ago = today - timedelta(days=7)
                queryset = queryset.filter(created_at__date__gte=week_ago)
            elif date_range == 'month':
                month_ago = today - timedelta(days=30)
                queryset = queryset.filter(created_at__date__gte=month_ago)
            elif date_range == 'custom':
                start_date = self.request.query_params.get('startDate')
                end_date = self.request.query_params.get('endDate')
                if start_date:
                    queryset = queryset.filter(created_at__date__gte=start_date)
                if end_date:
                    queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset.select_related('member', 'template')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        # Calculate statistics
        stats = queryset.aggregate(
            total_amount=Sum('total'),
            paid_amount=Sum('total', filter={'status': 'paid'}),
            pending_amount=Sum('total', filter={'status': 'pending'}),
        )

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {
                    'invoices': serializer.data,
                    'totalAmount': float(stats['total_amount'] or 0),
                    'paidAmount': float(stats['paid_amount'] or 0),
                    'pendingAmount': float(stats['pending_amount'] or 0),
                }
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'invoices': serializer.data,
                'totalAmount': float(stats['total_amount'] or 0),
                'paidAmount': float(stats['paid_amount'] or 0),
                'pendingAmount': float(stats['pending_amount'] or 0),
            }
        )

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        invoice = self.get_object()

        # Generate PDF if it doesn't exist
        if not hasattr(invoice, 'pdf_path') or not os.path.exists(invoice.pdf_path):
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                # Get data for invoice
                items = invoice.items.all()
                member = invoice.member

                # Set up the PDF document
                doc = SimpleDocTemplate(tmp.name, pagesize=letter)
                styles = getSampleStyleSheet()
                elements = []

                # Add title
                title_style = ParagraphStyle(
                    'Title', parent=styles['Heading1'], alignment=1, spaceAfter=12  # Center
                )
                elements.append(Paragraph(f"INVOICE #{invoice.number}", title_style))
                elements.append(Spacer(1, 20))

                # Add invoice information
                elements.append(
                    Paragraph(f"Date: {invoice.created_at.strftime('%Y-%m-%d')}", styles['Normal'])
                )
                elements.append(
                    Paragraph(
                        f"Due Date: {invoice.due_date.strftime('%Y-%m-%d')}", styles['Normal']
                    )
                )
                elements.append(
                    Paragraph(f"Status: {invoice.get_status_display()}", styles['Normal'])
                )
                elements.append(Spacer(1, 10))

                # Add member information
                elements.append(Paragraph("Bill To:", styles['Heading3']))
                elements.append(Paragraph(f"Name: {member.full_name}", styles['Normal']))
                elements.append(Paragraph(f"Email: {member.email}", styles['Normal']))
                if hasattr(member, 'phone') and member.phone:
                    elements.append(Paragraph(f"Phone: {member.phone}", styles['Normal']))
                if hasattr(member, 'address') and member.address:
                    elements.append(Paragraph(f"Address: {member.address}", styles['Normal']))
                elements.append(Spacer(1, 20))

                # Add items table
                table_data = [['Description', 'Quantity', 'Unit Price', 'Total']]
                for item in items:
                    table_data.append(
                        [
                            item.description,
                            str(item.quantity),
                            f"${float(item.unit_price):.2f}",
                            f"${float(item.total):.2f}",
                        ]
                    )

                # Add totals to table
                table_data.append(['', '', 'Subtotal:', f"${float(invoice.subtotal):.2f}"])
                table_data.append(['', '', 'Tax:', f"${float(invoice.tax):.2f}"])
                table_data.append(['', '', 'Total:', f"${float(invoice.total):.2f}"])

                # Create table and set styles
                items_table = Table(table_data, colWidths=[250, 75, 100, 100])
                items_table.setStyle(
                    TableStyle(
                        [
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 12),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -4), colors.white),
                            ('GRID', (0, 0), (-1, -4), 1, colors.black),
                            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
                        ]
                    )
                )

                elements.append(items_table)
                elements.append(Spacer(1, 30))

                # Add note
                if hasattr(invoice, 'notes') and invoice.notes:
                    elements.append(Paragraph(f"Notes: {invoice.notes}", styles['Normal']))

                # Build PDF
                doc.build(elements)
                invoice.pdf_path = tmp.name
                invoice.save()

        # Return PDF file
        return FileResponse(
            open(invoice.pdf_path, 'rb'),
            content_type='application/pdf',
            filename=f'invoice_{invoice.number}.pdf',
        )

    @action(detail=False, methods=['post'])
    def bulk_pdf(self, request):
        invoice_ids = request.data.get('invoiceIds', [])
        invoices = self.get_queryset().filter(id__in=invoice_ids)

        # Create temporary zip file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, 'w') as archive:
                for invoice in invoices:
                    # Generate PDF for each invoice
                    response = self.pdf(request, pk=invoice.id)
                    archive.write(invoice.pdf_path, f'invoice_{invoice.number}.pdf')

            return FileResponse(
                open(tmp.name, 'rb'), content_type='application/zip', filename='invoices.zip'
            )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.get_queryset()
        date_range = request.query_params.get('dateRange')

        if date_range:
            today = timezone.now().date()
            if date_range == 'today':
                queryset = queryset.filter(created_at__date=today)
            elif date_range == 'week':
                week_ago = today - timedelta(days=7)
                queryset = queryset.filter(created_at__date__gte=week_ago)
            elif date_range == 'month':
                month_ago = today - timedelta(days=30)
                queryset = queryset.filter(created_at__date__gte=month_ago)

        stats = queryset.aggregate(
            total_count=Count('id'),
            total_amount=Sum('total'),
            paid_amount=Sum('total', filter={'status': 'paid'}),
            pending_amount=Sum('total', filter={'status': 'pending'}),
        )

        return Response(
            {
                'totalCount': stats['total_count'] or 0,
                'totalAmount': float(stats['total_amount'] or 0),
                'paidAmount': float(stats['paid_amount'] or 0),
                'pendingAmount': float(stats['pending_amount'] or 0),
                'averageAmount': (
                    float(stats['total_amount'] or 0) / stats['total_count']
                    if stats['total_count']
                    else 0
                ),
                'paymentRate': (
                    float(stats['paid_amount'] or 0) / float(stats['total_amount'] or 1) * 100
                    if stats['total_amount']
                    else 0
                ),
            }
        )
