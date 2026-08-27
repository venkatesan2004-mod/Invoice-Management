# backend/invoice_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'products', views.ProductMasterViewSet, basename='product')
router.register(r'products1', views.ProductMasterViewSet1, basename='product1')

router.register(r'invoices', views.InvoiceViewSet, basename='invoice')
router.register(r'settings', views.CompanySettingsViewSet, basename='setting')

urlpatterns = [
    path('', include(router.urls)),
        path('gstin/', views.GSTINDetailsView.as_view(), name='gstin_details'),

]