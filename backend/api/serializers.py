# backend/invoice_app/serializers.py
from rest_framework import serializers
from .models import ProductMaster, Invoice, InvoiceItem, CompanySettings
class ProductMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMaster
        fields = '__all__'
        
class InvoiceItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    product_details = ProductMasterSerializer(source='product', read_only=True)
    
    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'part_no', 'hsn_sac_code', 'quantity', 'rate', 'unit', 
                  'gst_percentage', 'cgst_percentage', 'sgst_percentage', 
                  'total_amount', 'cgst_amount', 'sgst_amount', 'igst_amount', 'use_igst',  # ADD ALL THESE
                  'product_id', 'product_details']
                
class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, required=False)
    
    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ['created_at', 'created_by']  # REMOVE totals from read_only_fields

class InvoiceCreateUpdateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)
    
    class Meta:
        model = Invoice
        fields = [
            'invoice_number', 'invoice_date', 'delivery_note', 'reference_no',
            'reference_date', 'buyer_order_no', 'buyer_order_date', 
            'dispatch_doc_no', 'dispatch_date', 'payment_terms', 'destination',
            'buyer_name', 'buyer_address', 'buyer_gstin', 'buyer_state', 'buyer_state_code',
            'delivery_name', 'delivery_address', 'delivery_gstin', 'delivery_state', 'delivery_state_code',
            'items', 'dispatch_through', 'terms_of_delivery', 'mode_of_transport',
            'subtotal', 'cgst_total', 'sgst_total', 'igst_total', 'total_tax','sprife_amount','sprife_label',
            'grand_total','final_total', 'rounded_off', 'use_igst'
        ]
        extra_kwargs = {
            'subtotal': {'required': False, 'allow_null': True},
            'cgst_total': {'required': False, 'allow_null': True},
            'sgst_total': {'required': False, 'allow_null': True},
            'igst_total': {'required': False, 'allow_null': True},
            'total_tax': {'required': False, 'allow_null': True},
            'grand_total': {'required': False, 'allow_null': True},
            'rounded_off': {'required': False, 'allow_null': True},
        }
    
    def validate_invoice_number(self, value):
        """Validate unique invoice number on create"""
        if self.instance is None and Invoice.objects.filter(invoice_number=value).exists():
            raise serializers.ValidationError("Invoice number already exists")
        return value
    
    def validate_items(self, value):
        """Ensure at least one item is present"""
        if not value:
            raise serializers.ValidationError("At least one item is required")
        return value
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Set created_by from request if available
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        
        # Set default values for totals if not provided
        validated_data.setdefault('subtotal', 0)
        validated_data.setdefault('cgst_total', 0)
        validated_data.setdefault('sgst_total', 0)
        validated_data.setdefault('igst_total', 0)
        validated_data.setdefault('total_tax', 0)
        validated_data.setdefault('grand_total', 0)
        validated_data.setdefault('rounded_off', 0)
        
        # Create invoice with values from frontend
        invoice = Invoice.objects.create(**validated_data)
        
        # Create items with values from frontend
        for item_data in items_data:
            # Set default values for amounts if not provided
            item_data.setdefault('total_amount', item_data.get('quantity', 0) * item_data.get('rate', 0))
            item_data.setdefault('cgst_amount', 0)
            item_data.setdefault('sgst_amount', 0)
            item_data.setdefault('igst_amount', 0)
            
            # Handle product relationship
            product = None
            product_id = item_data.pop('product_id', None)
            if product_id:
                try:
                    product = ProductMaster.objects.get(id=product_id)
                    item_data['product'] = product
                except ProductMaster.DoesNotExist:
                    pass
            
            # Create the item
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        
        return invoice
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        
        # Update invoice fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle items if provided
        if items_data is not None:
            # Delete old items
            instance.items.all().delete()
            
            # Create new items
            for item_data in items_data:
                # Set default values for amounts if not provided
                item_data.setdefault('total_amount', item_data.get('quantity', 0) * item_data.get('rate', 0))
                item_data.setdefault('cgst_amount', 0)
                item_data.setdefault('sgst_amount', 0)
                item_data.setdefault('igst_amount', 0)
                
                # Handle product relationship
                product = None
                product_id = item_data.pop('product_id', None)
                if product_id:
                    try:
                        product = ProductMaster.objects.get(id=product_id)
                        item_data['product'] = product
                    except ProductMaster.DoesNotExist:
                        pass
                
                InvoiceItem.objects.create(invoice=instance, **item_data)
        
        return instance
    
import base64

class CompanySettingsSerializer(serializers.ModelSerializer):
    seal_signature = serializers.CharField(required=False)

    class Meta:
        model = CompanySettings
        fields = '__all__'

    def create(self, validated_data):
        image = validated_data.pop('seal_signature', None)
        instance = CompanySettings.objects.create(**validated_data)

        if image:
            instance.seal_signature = base64.b64decode(image.split(',')[-1])
            instance.save()

        return instance

    def update(self, instance, validated_data):
        image = validated_data.pop('seal_signature', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if image:
            instance.seal_signature = base64.b64decode(image.split(',')[-1])

        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.seal_signature:
            data['seal_signature'] = base64.b64encode(instance.seal_signature).decode()

        return data