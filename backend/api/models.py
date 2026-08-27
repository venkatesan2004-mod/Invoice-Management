from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, DecimalValidator
from decimal import Decimal

class ProductMaster(models.Model):
    """Master table for products/services"""
    description = models.TextField()
    hsn_sac_code = models.CharField(max_length=20, db_index=True)
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, editable=False)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, editable=False)
    igst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False)
    unit = models.CharField(max_length=20, default='NOS')
    default_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Split GST into CGST and SGST (assuming 50-50 split for intra-state)
        gst = self.gst_percentage
        self.cgst_percentage = gst / 2
        self.sgst_percentage = gst / 2
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.description} - {self.hsn_sac_code}"
    
    class Meta:
        ordering = ['description']

class Invoice(models.Model):
    """Main invoice header"""
    PAYMENT_TERMS = [
        ('CASH', 'Cash'),
        ('CREDIT', 'Credit'),
        ('ONLINE', 'Online Transfer'),
        ('CONTRACT', 'As Per Contract Terms & Conditions'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    delivery_note = models.CharField(max_length=50, blank=True,null=True)
    reference_no = models.CharField(max_length=100, blank=True)
    reference_date = models.DateField(null=True, blank=True)
    buyer_order_no = models.CharField(max_length=100, blank=True)
    buyer_order_date = models.DateField(null=True, blank=True)
    dispatch_doc_no = models.CharField(max_length=50, blank=True)
    dispatch_through = models.CharField(max_length=150, blank=True)
    terms_of_delivery = models.CharField(max_length=255,default='',blank=True,null=True)
    dispatch_date = models.DateField(null=True, blank=True)
    payment_terms = models.CharField(max_length=50, default='')
    mode_of_transport=models.CharField(max_length=150,default='')
    destination = models.CharField(max_length=255, default='Kalpakkam, Tamil Nadu-603102')
    
    # Buyer details
    buyer_name = models.CharField(max_length=255)
    buyer_address = models.TextField()
    buyer_gstin = models.CharField(max_length=20, blank=True)
    buyer_state = models.CharField(max_length=100, default='Tamil Nadu')
    buyer_state_code = models.CharField(max_length=5, default='33')

    delivery_name = models.CharField(max_length=255)
    delivery_address = models.TextField()
    delivery_gstin = models.CharField(max_length=20, blank=True)
    delivery_state = models.CharField(max_length=100, default='Tamil Nadu')
    delivery_state_code = models.CharField(max_length=5, default='33')
    
    # Totals
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sprife_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sprife_label = models.CharField(max_length=100, default='')


    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    rounded_off = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # NEW FIELD - Flag for IGST mode
    use_igst = models.BooleanField(default=False)
    
    # Status
    is_printed = models.BooleanField(default=False)
    created_by = models.CharField(max_length=100, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Invoice {self.invoice_number}"

class InvoiceItem(models.Model):
    """Invoice line items"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ProductMaster, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    part_no = models.CharField(max_length=100, blank=True, default='')
    hsn_sac_code = models.CharField(max_length=50, blank=True, default='')  # Changed from TextField
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default='NOS')
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    use_igst = models.BooleanField(default=False)
    
    # NO save() method - let frontend values be stored as-is
    def __str__(self):
        return f"{self.description} - {self.quantity} {self.unit}"
    
class CompanySettings(models.Model):
    """Company master settings"""
    company_name = models.CharField(max_length=255, default='JRC WORKMATE TRADING')
    address = models.TextField(default='No.22, MMS Complex, Pudupattinam, Kalpakkam - 603102')
    seal_signature = models.BinaryField(blank=True, null=True)
    state = models.CharField(max_length=100, default='Tamil Nadu')
    state_code = models.CharField(max_length=5, default='33')
    gstin = models.CharField(max_length=20, default='33AHOPY8219N1ZE')
    mobile = models.CharField(max_length=15, default='9655246269')
    email = models.EmailField(default='tbsenterprises2019@gmail.com')
    bank_holder_name = models.CharField(max_length=255, default='M/S JRC WORKMATE TRADING')
    bank_name = models.CharField(max_length=100, default='UNION BANK')
    bank_account_no = models.CharField(max_length=50, default='510101006884868')
    bank_ifsc = models.CharField(max_length=20, default='UBIN0935051')
    bank_branch = models.CharField(max_length=100, default='Kadalur Village')
    footer_note = models.TextField(default='* This is a computer generated invoice')
    
    def __str__(self):
        return self.company_name