from django.urls import path
from . import views

urlpatterns = [
    # Dashboard (Main Overview)
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Customers & Profiles
    path('customers/', views.customers_view, name='customers'),
    path('customers/create-company/', views.create_company_view, name='create_company'),
    path('customers/create-profile/', views.create_profile_view, name='create_profile'),

    # Pricing Tiers Matrix
    path('pricing/', views.pricing_view, name='pricing'),
    path('pricing/create/', views.create_pocket_view, name='create_pocket'),

    # Monthly Invoices
    path('invoices/', views.invoices_view, name='invoices'),
    path('invoices/generate/', views.generate_invoice_view, name='generate_invoice'),
    path('invoices/<int:invoice_id>/update-status/', views.update_invoice_status_view, name='update_invoice_status'),
]
