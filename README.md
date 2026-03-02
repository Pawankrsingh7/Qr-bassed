# Smart Restaurant Ordering System

## Project Structure

- `config/` : project configuration, API routing, split settings (`base`, `dev`, `prod`).
- `apps/restaurants/` : restaurant entities (multi-restaurant foundation).
- `apps/tables/` : table state, QR token, verification PIN.
- `apps/menu/` : categories and menu items.
- `apps/orders/` : session lifecycle, order items, confirmation flow.
- `apps/payments/` : payment transaction and cash payment closure.
- `apps/kitchen/` : kitchen dashboard + queue/confirmation APIs.
- `apps/dashboard/` : admin analytics + menu/table/session APIs.
- `apps/core/` : shared permissions, root pages, management commands.
- `templates/` : basic customer, kitchen, admin templates.

## Core Workflow

1. Admin prints table QR codes from `/tables/restaurants/<restaurant_slug>/qr-catalog/`.
2. Customer scans QR and opens `/order/<restaurant_slug>/<table_number>/<qr_token>/`.
3. Order page auto-starts session by calling `POST /api/customer/sessions/bootstrap/` using QR token.
4. Customer places first order `POST /api/customer/sessions/{id}/items/`.
5. Session remains `pending_confirmation` and response says `Waiting for staff confirmation.`
6. Staff confirms session using:
   - `POST /api/kitchen/sessions/{id}/confirm/` or
   - `POST /api/customer/sessions/{id}/confirm/`
7. Session becomes `active`; kitchen queue receives live items.
8. Customer requests bill via `POST /api/customer/sessions/{id}/request-bill/`.
9. Staff records cash payment via `POST /api/payments/sessions/{id}/cash/`.
10. Session closes and table status moves back to `free`.

## Key APIs

### Customer
- `GET /api/customer/menu/?restaurant_slug=<slug>`
- `POST /api/customer/sessions/bootstrap/`
- `GET /api/customer/sessions/open/?restaurant_slug=<slug>&table_number=1`
- `GET /api/customer/sessions/{id}/`
- `POST /api/customer/sessions/{id}/items/`
- `POST /api/customer/sessions/{id}/request-bill/`

### Kitchen (staff-only)
- `GET /api/kitchen/queue/`
- `PATCH /api/kitchen/order-items/{item_id}/status/`
- `GET /api/kitchen/pending-confirmations/`
- `POST /api/kitchen/sessions/{id}/confirm/`

### Admin/Dashboard (staff-only)
- `GET /api/dashboard/overview/`
- `GET /api/dashboard/sessions/history/`
- `POST /api/dashboard/sessions/{id}/manual-close/`
- `GET /api/dashboard/tables/status/`
- `GET/POST /api/dashboard/menu/categories/`
- `GET/POST /api/dashboard/menu/items/`
- `PUT/DELETE /api/dashboard/menu/items/{item_id}/`

## Admin Web Features

- Login-protected admin panel: `/dashboard/` (staff users only)
- Add staff/kitchen/manager users from dashboard form
- Generate tables in bulk (for example count `5` creates tables `1..5` if missing)
- Auto-generate QR token + table PIN for each created table
- View total tables and status counts (`free`, `in process`, `paid`)
- Add and view menu categories/items
- View per-table QR links and scan URLs

## Security/Abuse Prevention

- Session confirmation is staff-gated.
- Kitchen, payment, and dashboard APIs require authenticated staff users.
- Optional table `verification_pin` check blocks remote prank orders.

## Management Commands

- Seed demo data: `python manage.py seed_demo_data`
- Rotate table PINs: `python manage.py rotate_table_pins --restaurant-slug=demo-restaurant`

## Run (Development)

1. Create virtualenv and install deps: `pip install -r requirements.txt`
2. Run migrations: `python manage.py makemigrations && python manage.py migrate`
3. Seed demo records: `python manage.py seed_demo_data`
4. Start server: `python manage.py runserver`

Demo staff login from seed command:
- `username: staff`
- `password: staff1234`

Default uses `config.settings.dev` with SQLite.
For PostgreSQL/production, use env vars from `.env.example` and `config.settings.prod`.
