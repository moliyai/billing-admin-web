import requests
from decimal import Decimal
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required, login_not_required
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count, Q
from django.db import IntegrityError
from .models import Pocket, Company, Invoice, Profile


# Helper to fetch month API request count directly from company credentials
def fetch_company_month_usage(company, start_date_str, end_date_str):
    """
    Fetches the total_requests count for a company from its upstream API
    for the specified start and end date range.
    """
    if not company or not company.api_url:
        return 0

    params = {
        "start_date": start_date_str,
        "end_date": end_date_str,
        "page": 1,
        "items_per_page": 1,
    }

    auth = (company.api_username, company.api_password) if company.api_username and company.api_password else None

    try:
        response = requests.get(company.api_url, auth=auth, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("meta", {}).get("totalItems", 0)
    except requests.RequestException as e:
        print(f"API Error ({company.api_url}): {e}")

    return 0


# ------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------
@method_decorator(login_not_required, name='dispatch')
class CustomLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()

        # Reject if NOT staff and NOT superuser
        if not (user.is_staff or user.is_superuser):
            form.add_error(
                None,
                "Access restricted. Only staff and superusers can log in here.",
            )
            return self.form_invalid(form)

        return super().form_valid(form)


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------
@login_required
def dashboard_view(request):
    total_revenue = Invoice.objects.filter(status=Invoice.StatusChoices.PAID).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')

    active_companies_count = Company.objects.count()
    pending_invoices_count = Invoice.objects.filter(status=Invoice.StatusChoices.GENERATED).count()
    total_requests_processed = Invoice.objects.aggregate(total=Sum('total_requests'))['total'] or 0

    recent_invoices = Invoice.objects.select_related('company').order_by('-created_at')[:5]
    recent_companies = Company.objects.select_related('pocket').order_by('-created_at')[:5]

    context = {
        'total_revenue': total_revenue,
        'active_companies_count': active_companies_count,
        'pending_invoices_count': pending_invoices_count,
        'total_requests_processed': total_requests_processed,
        'recent_invoices': recent_invoices,
        'recent_companies': recent_companies,
    }
    return render(request, 'main.html', context)


# ------------------------------------------------------------------
# Customers & Profiles
# ------------------------------------------------------------------
@login_required
def customers_view(request):
    query = request.GET.get('q', '').strip()

    companies = Company.objects.select_related('pocket').annotate(
        profile_count=Count('profiles')
    ).order_by('-created_at')

    if query:
        companies = companies.filter(
            Q(name__icontains=query) |
            Q(pocket__name__icontains=query) |
            Q(api_username__icontains=query)
        )

    profiles = Profile.objects.select_related('user', 'company').order_by('-created_at')
    pockets = Pocket.objects.all().order_by('name')

    context = {
        'companies': companies,
        'profiles': profiles,
        'pockets': pockets,
        'query': query,
    }
    return render(request, 'customers.html', context)


@login_required
def create_company_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        pocket_id = request.POST.get('pocket_id')
        api_url = request.POST.get('api_url', '').strip()
        api_username = request.POST.get('api_username', '').strip()
        api_password = request.POST.get('api_password', '').strip()

        if name and pocket_id:
            try:
                pocket = Pocket.objects.get(id=pocket_id)
                Company.objects.create(
                    name=name,
                    pocket=pocket,
                    api_url=api_url if api_url else None,
                    api_username=api_username if api_username else None,
                    api_password=api_password if api_password else None
                )
                messages.success(request, f'Company "{name}" created successfully.')
            except Pocket.DoesNotExist:
                messages.error(request, 'Selected pricing pocket does not exist.')
        else:
            messages.error(request, 'Company name and pricing pocket are required.')

    return redirect('customers')


@login_required
def create_profile_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        company_id = request.POST.get('company_id')

        if not username or not password or not company_id:
            messages.error(request, 'Username, password, and company are required.')
            return redirect('customers')

        try:
            company = Company.objects.get(id=company_id)
            user = User.objects.create_user(username=username, email=email, password=password)
            Profile.objects.create(user=user, company=company)
            messages.success(request, f'Profile created for user "{username}" under {company.name}.')
        except Company.DoesNotExist:
            messages.error(request, 'Selected company does not exist.')
        except IntegrityError:
            messages.error(request, f'User with username "{username}" already exists.')

    return redirect('customers')


# ------------------------------------------------------------------
# Pricing Pockets
# ------------------------------------------------------------------
@login_required
def pricing_view(request):
    pockets = Pocket.objects.annotate(companies_count=Count('company')).order_by('price')
    return render(request, 'pricing.html', {'pockets': pockets})


@login_required
def create_pocket_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        requests_count = request.POST.get('requests_count', 0)
        price = request.POST.get('price', 0.00)
        price_per_request_over_limit = request.POST.get('price_per_request_over_limit', 0.00)

        if name:
            Pocket.objects.create(
                name=name,
                requests_count=int(requests_count or 0),
                price=float(price or 0.00),
                price_per_request_over_limit=float(price_per_request_over_limit or 0.00)
            )
            messages.success(request, f'Pricing Pocket "{name}" created successfully.')
        else:
            messages.error(request, 'Pocket name is required.')

    return redirect('pricing')


# ------------------------------------------------------------------
# Invoices
# ------------------------------------------------------------------
@login_required
def invoices_view(request):
    status_filter = request.GET.get('status', '').strip()
    company_filter = request.GET.get('company', '').strip()
    query = request.GET.get('q', '').strip()

    invoices = Invoice.objects.select_related('company').order_by('-invoice_month', '-created_at')

    if company_filter:
        invoices = invoices.filter(company_id=company_filter)

    if status_filter:
        invoices = invoices.filter(status=status_filter)

    if query:
        invoices = invoices.filter(
            Q(name__icontains=query) |
            Q(company__name__icontains=query)
        )

    companies = Company.objects.all().order_by('name')

    total_billed = Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_paid = Invoice.objects.filter(status=Invoice.StatusChoices.PAID).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_unpaid = Invoice.objects.filter(status=Invoice.StatusChoices.GENERATED).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    context = {
        'invoices': invoices,
        'companies': companies,
        'status_filter': status_filter,
        'company_filter': company_filter,
        'query': query,
        'status_choices': Invoice.StatusChoices.choices,
        'total_billed': total_billed,
        'total_paid': total_paid,
        'total_unpaid': total_unpaid,
    }
    return render(request, 'invoices.html', context)


@login_required
def generate_invoice_view(request):
    """
    `/invoices/generate/` — Fetches month API calls directly from Company API
    and generates/updates the Invoice without manual request entry.
    """
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        month_str = request.POST.get('invoice_month', '').strip()
        description = request.POST.get('description', '').strip()

        if not company_id or not month_str:
            messages.error(request, 'Company and invoice period are required.')
            return redirect('invoices')

        invoice_date = None
        try:
            invoice_date = datetime.strptime(month_str, '%m-%Y').date().replace(day=1)
        except ValueError:
            pass

        if not invoice_date:
            messages.error(request, f'Invalid date format "{month_str}". Please select a valid month.')
            return redirect('invoices')

        try:
            company = Company.objects.select_related('pocket').get(id=company_id)
            pocket = company.pocket

            # Calculate start and end dates for the selected invoice month
            start_date_obj = datetime(invoice_date.year, invoice_date.month, 1)
            if invoice_date.month == 12:
                next_month = datetime(invoice_date.year + 1, 1, 1)
            else:
                next_month = datetime(invoice_date.year, invoice_date.month + 1, 1)
            end_date_obj = next_month - timedelta(days=1)

            start_str = start_date_obj.strftime("%d.%m.%Y")
            end_str = end_date_obj.strftime("%d.%m.%Y")

            # Automatically fetch total API request count from the Company API endpoint
            total_requests = fetch_company_month_usage(company, start_str, end_str)

            # Price calculations using Decimal precision
            base_price = Decimal(str(pocket.price)) if pocket else Decimal('0.00')
            price_per_overage = Decimal(str(pocket.price_per_request_over_limit)) if pocket else Decimal('0.00')
            pocket_limit = pocket.requests_count if pocket else 0

            overage_requests = max(0, total_requests - pocket_limit)
            overage_cost = Decimal(overage_requests) * price_per_overage
            calculated_total = base_price + overage_cost

            invoice_name = f"INV-{company.name.upper()[:3]}-{invoice_date.strftime('%m%Y')}"
            auto_description = f"API Billing for {invoice_date.strftime('%m-%Y')} ({total_requests:,} calls)"

            invoice, created = Invoice.objects.update_or_create(
                company=company,
                invoice_month=invoice_date,
                defaults={
                    'name': invoice_name,
                    'total_requests': total_requests,
                    'total_amount': calculated_total,
                    'description': description if description else auto_description,
                }
            )

            if created:
                messages.success(request, f'Invoice "{invoice_name}" generated for ${calculated_total:,.2f} ({total_requests:,} calls fetched automatically).')
            else:
                messages.success(request, f'Existing invoice "{invoice_name}" updated. New total: ${calculated_total:,.2f} ({total_requests:,} calls).')

        except Company.DoesNotExist:
            messages.error(request, 'Selected company was not found.')

    return redirect('invoices')


@login_required
def update_invoice_status_view(request, invoice_id):
    if request.method == 'POST':
        new_status = request.POST.get('status')
        invoice = get_object_or_404(Invoice, id=invoice_id)

        if new_status in Invoice.StatusChoices.values:
            invoice.status = new_status
            invoice.save()
            messages.success(request, f'Invoice "{invoice.name}" status updated to {invoice.get_status_display()}.')
        else:
            messages.error(request, 'Invalid status choice.')

    return redirect('invoices')
