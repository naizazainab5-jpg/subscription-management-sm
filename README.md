# Brightloop - setup (10 minutes)

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
django-admin startproject config .
```
Copy the 4 app folders (accounts, catalog, subscriptions, billing) next to manage.py, then edit **config/settings.py**:

```python
INSTALLED_APPS += ["accounts", "catalog", "subscriptions", "billing"]
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/login/"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"  # reset emails print in terminal

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "accounts.validators.BrightloopPasswordValidator"},
]
```
Then:
```bash
python manage.py makemigrations accounts catalog subscriptions billing
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000/admin/ and add a Tax, Product, Plan, then a Subscription (status active) with a line.
Run billing:  `python manage.py run_billing`  (run it twice: no duplicates).
