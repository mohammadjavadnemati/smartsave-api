# SmartSave API 💰

A smart personal finance management system built with Django REST Framework.

## Features

- **Authentication** — JWT-based auth with token blacklisting
- **Expense Management** — Track expenses with categories, filters, and search
- **Income Management** — Multiple income sources with monthly reports
- **Savings Goals** — Set goals, track deposits, and predict completion time
- **Budget Management** — Set budgets per category with alert system
- **Analytics Dashboard** — Financial health score, trends, and smart insights
- **Recurring Expenses** — Auto-generate recurring expenses (Netflix, rent, etc.)
- **Savings Impact Calculator** — See how much you'd save by cutting an expense

---

## Tech Stack

- **Backend**: Django 5.0, Django REST Framework
- **Database**: PostgreSQL
- **Auth**: JWT (SimpleJWT) with access token blacklisting
- **Docs**: drf-spectacular (Swagger UI)
- **Testing**: pytest, factory-boy, pytest-cov

---

## Project Structure

```
smartsave/
├── config/                  # Project settings
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   └── urls.py
├── apps/
│   ├── accounts/            # Authentication
│   ├── expenses/            # Expense & category management
│   ├── incomes/             # Income management
│   ├── savings/             # Savings goals
│   ├── budgets/             # Budget management
│   └── analytics/           # Dashboard & analytics
├── core/                    # Shared utilities
│   ├── permissions.py
│   ├── pagination.py
│   └── utils.py
└── requirements/
    ├── base.txt
    ├── development.txt
    └── production.txt
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL

### Installation

```bash
# Clone the repository
git clone https://github.com/username/smartsave.git
cd smartsave

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements/development.txt

# Create .env file
cp .env.example .env
# Edit .env with your settings
```

### Environment Variables

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=smartsave_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

### Database Setup

```bash
# Create PostgreSQL database
createdb smartsave_db

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Run Development Server

```bash
python manage.py runserver
```

Visit:
- **API**: http://127.0.0.1:8000/api/v1/
- **Swagger UI**: http://127.0.0.1:8000/api/docs/
- **ReDoc**: http://127.0.0.1:8000/api/redoc/
- **Admin**: http://127.0.0.1:8000/admin/

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register/` | Register new user |
| POST | `/api/v1/auth/login/` | Login |
| POST | `/api/v1/auth/logout/` | Logout (blacklists tokens) |
| POST | `/api/v1/auth/token/refresh/` | Refresh access token |
| GET/PATCH | `/api/v1/auth/profile/` | Get/update profile |
| POST | `/api/v1/auth/change-password/` | Change password |

### Expenses
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/expenses/` | List/create expenses |
| GET/PATCH/DELETE | `/api/v1/expenses/{id}/` | Expense detail |
| GET | `/api/v1/expenses/summary/` | Expense summary |
| GET | `/api/v1/expenses/savings-impact/?q=cigarettes` | Savings impact calculator |
| GET/POST | `/api/v1/expenses/categories/` | List/create categories |
| GET/POST | `/api/v1/expenses/recurring/` | List/create recurring expenses |
| GET | `/api/v1/expenses/recurring/summary/` | Recurring expenses summary |

### Incomes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/incomes/` | List/create incomes |
| GET | `/api/v1/incomes/summary/` | Income summary |
| GET | `/api/v1/incomes/monthly-report/` | Monthly income report |
| GET | `/api/v1/incomes/vs-expenses/` | Income vs expenses comparison |
| GET/POST | `/api/v1/incomes/sources/` | List/create income sources |

### Savings Goals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/savings/goals/` | List/create goals |
| GET/PATCH/DELETE | `/api/v1/savings/goals/{id}/` | Goal detail |
| GET | `/api/v1/savings/goals/progress/` | Overall progress |
| GET | `/api/v1/savings/goals/{id}/predict/?monthly_saving=250` | Predict completion |
| GET/POST | `/api/v1/savings/deposits/` | List/create deposits |

### Budgets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/budgets/` | List/create budgets |
| GET/PATCH/DELETE | `/api/v1/budgets/{id}/` | Budget detail |
| GET | `/api/v1/budgets/alerts/` | Budget alerts |
| GET | `/api/v1/budgets/summary/` | Budget summary |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/dashboard/` | Main dashboard |
| GET | `/api/v1/analytics/trends/` | Monthly trends |
| GET | `/api/v1/analytics/categories/` | Expense by category |
| GET | `/api/v1/analytics/health/` | Financial health score |
| GET | `/api/v1/analytics/insights/` | Smart financial insights |

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=apps --cov-report=html

# Run specific app tests
pytest apps/expenses/

# Run without coverage
pytest --no-cov
```

Current coverage: **85%**

---

## Key Features Explained

### Financial Health Score (0-100)
Calculated based on:
- **Savings Rate** (30 pts) — % of income saved
- **Budget Adherence** (30 pts) — how well you stick to budgets
- **Income Stability** (20 pts) — consistency of income
- **Expense Ratio** (20 pts) — expenses vs income ratio

### Savings Impact Calculator
Search any expense keyword (e.g. "cigarettes") and see:
- All matching transactions
- Total spent
- Monthly average
- How much you'd save in 1 month / 6 months / 1 year / 5 years

### Budget Alert System
- 🟡 **Warning** — 80%+ of budget used
- 🔴 **Exceeded** — Over budget

### Recurring Expenses
Auto-generates expenses from templates (Netflix, rent, gym, etc.) — no manual action needed.

---

## License

MIT
