# 🛡️ Admin & Billing Management Portal

The administrative back-office and control plane for managing client companies, customer user profiles, subscription pricing tiers ("Pockets"), and automated monthly invoice generation with upstream API synchronization.

---

## 🌟 Admin Features

- **📊 Financial & Operational Dashboard**:
  - Total collected revenue (`PAID` invoices).
  - Outstanding balances and pending invoice counts (`GENERATED`).
  - Aggregated global API request consumption.
  - Recent company registrations and recent invoice activity.
- **🏢 Customer & Tenant Management**:
  - **Company Provisioning**: Configure upstream prediction API endpoints, usernames, and passwords per company.
  - **User Profile Assignment**: Create user credentials and associate them directly with client companies.
  - Search and filter companies by name, assigned pocket, or API username.
- **🏷️ Subscription / Pocket Engine**:
  - Define custom pricing tiers with base quotas (`requests_count`), base subscription costs, and per-request overage rates.
  - Track how many companies are subscribed to each plan.
- **⚡ Automated Invoicing & Upstream Sync**:
  - **Zero Manual Counting**: Select a company and target month (`MM-YYYY`); the system automatically queries the client company's external API endpoint to fetch the exact request count.
  - Accurate overage fee calculation using Python `Decimal` arithmetic.
  - Update and transition invoice statuses (`Generated` ➔ `Paid` ➔ etc.).

---

## 🔒 Security & Access Control

Access is strictly restricted to administrative staff:
- Only authenticated users with `is_staff = True` or `is_superuser = True` can access this portal.
- Non-staff accounts are automatically rejected at login with an authorization error.

---

## 🚀 Quick Start with Docker

### 1. Build and Start the Containers
```bash
docker compose up --build -d
```

### 2. Database Setup & Create Admin Account
```bash
docker compose exec web python manage.py makemigrations core
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Log in to the Admin Portal at: `http://localhost:8000/`

---

## 📋 Operational Workflow

```
1. Create Pocket (Plan) ──► 2. Register Company ──► 3. Create User Profile ──► 4. Run Monthly Billing
   (Quota & Overage Rates)     (Set Upstream API)      (Assign User to Company)   (Auto-fetch API usage)
```

1. **Create a Pocket**: Navigate to **Pricing**, set quota limit, base price, and overage fee per request.
2. **Register a Company**: Go to **Customers**, add a company, select the Pocket, and input the company's upstream API URL and Basic Auth credentials.
3. **Provision a User**: Create client login credentials attached to that company.
4. **Generate Invoices**: In **Invoices**, pick a company and a billing month (e.g., `08-2026`). The portal will automatically contact the company's API, calculate overages, and create or update the invoice.

---

## 🛣️ Admin Route Reference

| Route | Method | Description |
| :--- | :--- | :--- |
| `/login/` | `GET`, `POST` | Staff/Superuser login with privilege verification |
| `/` | `GET` | Admin Dashboard (Revenue, Pending Invoices, Request Metrics) |
| `/customers/` | `GET` | Manage companies, customer profiles, and API connections |
| `/customers/company/create/` | `POST` | Register a new company with upstream API details |
| `/customers/profile/create/` | `POST` | Create a new user account linked to a company |
| `/pricing/` | `GET` | View all pricing pockets and subscriber counts |
| `/pricing/create/` | `POST` | Create a new pricing tier with overage pricing |
| `/invoices/` | `GET` | View, search, and filter all company invoices |
| `/invoices/generate/` | `POST` | Auto-fetch API usage and generate monthly invoice |
| `/invoices/<id>/status/` | `POST` | Update invoice status (e.g., `Paid`, `Generated`) |

---

## 💡 Upstream Invoice Calculation Logic

When an invoice is generated for a given month:
1. Dates are automatically resolved to `01.MM.YYYY` – `[Last Day].MM.YYYY`.
2. A single lightweight request is made to the company's external API (`page=1&items_per_page=1`) to read `meta.totalItems`.
3. Financial calculation:
   $$\text{Total} = \text{Base Price} + (\max(0, \text{Total Requests} - \text{Pocket Limit}) \times \text{Overage Price})$$
4. The invoice is created or updated idempotently (`update_or_create`) under the standard format: `INV-[COMPANY_PREFIX]-[MMYYYY]`.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Django
- **Database ORM**: Django ORM with aggregations (`Sum`, `Count`, `Q`)
- **Integration**: `requests` (External API consumption with Basic Auth)
- **Math Precision**: Python `Decimal` for financial integrity
- **Containerization**: Docker & Docker Compose
