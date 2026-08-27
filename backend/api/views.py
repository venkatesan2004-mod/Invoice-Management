# backend/invoice_app/views.py
import traceback

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import ProductMaster, Invoice, CompanySettings
from .serializers import *
# backend/invoice_app/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.http import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import pandas as pd
import io
import json
from .models import ProductMaster, Invoice, CompanySettings
from .serializers import ProductMasterSerializer, InvoiceSerializer, InvoiceCreateUpdateSerializer, CompanySettingsSerializer
# backend/invoice_app/views.py - Updated ProductMasterViewSet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.http import HttpResponse, FileResponse
import pandas as pd
import io
import json
import traceback
from .models import ProductMaster, Invoice, CompanySettings
from .serializers import ProductMasterSerializer, InvoiceSerializer, InvoiceCreateUpdateSerializer, CompanySettingsSerializer
# backend/invoice_app/views.py - Complete working version
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.http import HttpResponse, FileResponse
import pandas as pd
import io
import json
import traceback
from django.db import transaction
from .models import ProductMaster, Invoice, CompanySettings
from .serializers import ProductMasterSerializer, InvoiceSerializer, InvoiceCreateUpdateSerializer, CompanySettingsSerializer
from rest_framework.pagination import PageNumberPagination

# Add pagination class
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductMasterViewSet(viewsets.ModelViewSet):
    queryset = ProductMaster.objects.filter(is_active=True)[:10]
    serializer_class = ProductMasterSerializer
     
    @action(detail=True, methods=['put'], url_path='update-product')
    def update_product(self, request, pk=None):
        try:
            # Get product manually (no slicing issue)
            product = ProductMaster.objects.get(pk=pk, is_active=True)

            serializer = self.get_serializer(product, data=request.data, partial=False)

            if serializer.is_valid():
                serializer.save()
                return Response({
                    "success": True,
                    "message": "Product updated successfully",
                    "data": serializer.data
                })

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except ProductMaster.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '').strip()
        
        products = ProductMaster.objects.filter(is_active=True)
        
        if query:
            words = query.split()

            for word in words:
                products = products.filter(
                    Q(description__icontains=word) |
                    Q(hsn_sac_code__icontains=word)
                )

            products = products[:20]
        else:
            products = products[:10]

        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    # 📤 UPLOAD EXCEL
    @action(detail=False, methods=['post'])
    def upload_excel(self, request):
        try:
            file = request.FILES.get('file')
            
            if not file:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel with limited rows
            df = pd.read_excel(file, nrows=1000)  # Limit to 1000 rows to avoid memory issues
            
            required_columns = [
                'description',
                'hsn_sac_code',
                'gst_percentage',
                'unit',
                'default_rate'
            ]
            
            # Validate columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return Response({
                    'error': 'Missing required columns',
                    'missing_columns': missing_columns,
                    'available_columns': list(df.columns)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            successful = 0
            created_count = 0
            updated_count = 0
            errors = []
            
            # Process in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                for index, row in batch.iterrows():
                    try:
                        # Safe extraction (NaN handling)
                        description = str(row['description']).strip() if pd.notna(row['description']) else ''
                        hsn_sac_code = str(row['hsn_sac_code']).strip() if pd.notna(row['hsn_sac_code']) else ''
                        unit = str(row['unit']).strip() if pd.notna(row['unit']) else ''
                        
                        gst_percentage = float(row['gst_percentage']) if pd.notna(row['gst_percentage']) else 0
                        default_rate = float(row['default_rate']) if pd.notna(row['default_rate']) else 0
                        
                        if not description:
                            continue
                        
                        product, created = ProductMaster.objects.update_or_create(
                            description=description,
                            defaults={
                                'hsn_sac_code': hsn_sac_code,
                                'gst_percentage': gst_percentage,
                                'unit': unit,
                                'default_rate': default_rate,
                                'is_active': True
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                        
                        successful += 1
                        
                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'success': True,
                'total_processed': successful,
                'created': created_count,
                'updated': updated_count,
                'errors': errors
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # 📥 DOWNLOAD TEMPLATE
    @action(detail=False, methods=['get'])
    def download_template(self, request):
        try:
            data = {
                'description': ['Product A', 'Product B'],
                'hsn_sac_code': ['1001', '1002'],
                'gst_percentage': [12, 18],
                'unit': ['NOS', 'NOS'],
                'default_rate': [100, 200]
            }
            
            df = pd.DataFrame(data)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Template')
            
            output.seek(0)
            
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="product_template.xlsx"'
            
            return response
            
        except Exception as e:
            return HttpResponse(json.dumps({'error': str(e)}), status=400)
    
    # 📤 EXPORT EXCEL - Optimized
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        try:
            # Use iterator to avoid loading all at once
            products = ProductMaster.objects.filter(is_active=True).only(
                'description', 'hsn_sac_code', 'gst_percentage', 
                'unit', 'default_rate', 'created_at', 'updated_at'
            ).order_by('id').iterator()
            
            data = []
            for p in products:
                data.append({
                    'description': p.description,
                    'hsn_sac_code': p.hsn_sac_code,
                    'gst_percentage': float(p.gst_percentage),
                    'unit': p.unit,
                    'default_rate': float(p.default_rate),
                    'created_at': p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else '',
                    'updated_at': p.updated_at.strftime('%Y-%m-%d %H:%M:%S') if p.updated_at else ''
                })
                
                # Flush data every 1000 records to avoid memory issues
                if len(data) >= 1000:
                    # Process in chunks if needed
                    pass
            
            df = pd.DataFrame(data)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Products')
            
            output.seek(0)
            
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="products.xlsx"'
            
            return response
            
        except Exception as e:
            return HttpResponse(json.dumps({'error': str(e)}), status=400)
    
    # ➕ CREATE
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # ✏ UPDATE
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # 🗑 DELETE - Soft delete (optional)
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class ProductMasterViewSet1(viewsets.ModelViewSet):
    queryset = ProductMaster.objects.filter(is_active=True)
    serializer_class = ProductMasterSerializer

    # 🚀 Separate Update API
    @action(detail=False, methods=['put'], url_path='update-product')
    def update_product(self, request):
        try:
            product_id = request.data.get('id')

            if not product_id:
                return Response(
                    {"error": "Product ID is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            product = ProductMaster.objects.get(pk=product_id, is_active=True)

            serializer = self.get_serializer(product, data=request.data, partial=False)

            if serializer.is_valid():
                serializer.save()
                return Response({
                    "success": True,
                    "message": "Product updated successfully",
                    "data": serializer.data
                })

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except ProductMaster.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )    
class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all().order_by('-created_at')
    lookup_field = 'pk'
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return InvoiceCreateUpdateSerializer
        return InvoiceSerializer
    
    def get_queryset(self):
        """Optional: Filter queryset"""
        queryset = super().get_queryset()
        
        # Filter by date range if provided
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        
        if from_date:
            queryset = queryset.filter(invoice_date__gte=from_date)
        if to_date:
            queryset = queryset.filter(invoice_date__lte=to_date)
        
        # Filter by invoice number
        invoice_number = self.request.query_params.get('invoice_number')
        if invoice_number:
            queryset = queryset.filter(invoice_number__icontains=invoice_number)
        
        return queryset
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                invoice = serializer.save()
                response_serializer = InvoiceSerializer(invoice)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        
        if serializer.is_valid():
            try:
                invoice = serializer.save()
                response_serializer = InvoiceSerializer(invoice)
                return Response(response_serializer.data)
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def print_view(self, request, pk=None):
        """Get invoice data formatted for printing"""
        invoice = self.get_object()
        serializer = InvoiceSerializer(invoice)
        
        # Add additional print-specific data if needed
        data = serializer.data
        data['print_date'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def mark_printed(self, request, pk=None):
        """Mark invoice as printed"""
        invoice = self.get_object()
        invoice.is_printed = True
        invoice.save()
        
        return Response({'status': 'marked as printed', 'is_printed': True})
    
    @action(detail=False, methods=['get'])
    def next_number(self, request):
        """Get next available invoice number"""
        last_invoice = Invoice.objects.order_by('-id').first()
        if last_invoice:
            # Extract number from invoice number (assuming format like INV-001)
            try:
                last_number = int(last_invoice.invoice_number.split('-')[-1])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1
        
        # Format invoice number (adjust format as needed)
        next_invoice_number = f"INV-{next_number:04d}"
        
        return Response({'next_invoice_number': next_invoice_number})


class CompanySettingsViewSet(viewsets.ModelViewSet):
    queryset = CompanySettings.objects.all().last()
    serializer_class = CompanySettingsSerializer
    
    def get_queryset(self):
        return CompanySettings.objects.all()

import logging
import re
import requests

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

GSTIN_API_URL = "https://tallysolutions.com/wp-content/themes/tally/api/gstin-serach-api.php"


class GSTINDetailsView(APIView):
    """
    GET Endpoint:
    /api/gstin/?gstin=33AAACI1607G2Z5
    """

    def validate_gstin(self, gstin):
        """Validate GSTIN format"""
        if not gstin:
            return False

        pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'
        return bool(re.match(pattern, gstin.upper()))

    def get(self, request):
        gstin = request.query_params.get("gstin", "").strip().upper()

        # Validate GSTIN
        if not gstin:
            return Response(
                {
                    "success": False,
                    "message": "GSTIN is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not self.validate_gstin(gstin):
            return Response(
                {
                    "success": False,
                    "message": f"Invalid GSTIN format: {gstin}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cache
        cache_key = f"gstin_{gstin}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            response = requests.post(
                GSTIN_API_URL,
                data={
                    "gstin": gstin
                },
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                timeout=15
            )

            response.raise_for_status()
            api_data = response.json()

            if api_data.get("status") == 1:

                response_data = {
                    "success": True,
                    "data": {
                        "businessName": api_data.get("trade_name", ""),
                        "legalName": api_data.get("legal_name", ""),
                        "address": api_data.get("address", ""),
                        "state": api_data.get("state", ""),
                        "stateCode": gstin[:2],
                        "gstin": api_data.get("gstin", gstin),
                        "registrationDate": api_data.get("registration_date", ""),
                        "status": api_data.get("gstin_status", ""),
                        "businessType": api_data.get("registration_type", ""),
                        "jurisdiction": "",
                        "natureOfBusiness": api_data.get("business_activity", ""),
                        "city": api_data.get("city", ""),
                        "pincode": api_data.get("pincode", ""),
                        "geolocation": api_data.get("geolocation", "")
                    }
                }

                # Cache for 24 Hours
                cache.set(cache_key, response_data, 86400)

                return Response(response_data, status=status.HTTP_200_OK)

            return Response(
                {
                    "success": False,
                    "message": api_data.get("message", "GSTIN not found")
                },
                status=status.HTTP_404_NOT_FOUND
            )

        except requests.exceptions.Timeout:
            return Response(
                {
                    "success": False,
                    "message": "Request timed out."
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )

        except requests.exceptions.ConnectionError:
            return Response(
                {
                    "success": False,
                    "message": "Unable to connect to GSTIN service."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        except Exception as e:
            logger.exception(e)
            return Response(
                {
                    "success": False,
                    "message": "Unable to fetch GSTIN details."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
