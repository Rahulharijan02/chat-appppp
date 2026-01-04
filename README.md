# Developer Portfolio Network

A lightweight social networking starter inspired by Facebook-style features, built with Django, HTMX, Bootstrap, and vanilla HTML/CSS. It is framed as a developer portfolio community so you can showcase updates, connect with peers, and keep a clean, documented codebase.

## Features
- User registration and login using Django auth.
- Profile pages with bio, location, role, avatar, and portfolio link fields.
- Post creation with public/friends-only visibility, likes, and comments updated via HTMX.
- Friend requests with accept/decline flow and quick dashboard in the feed sidebar.
- Private 1:1 chats between friends, with an inbox and conversation pages.
- Bootstrap styling with responsive layout and a small custom stylesheet.
- Admin interface for moderating content.

## Project layout
```
manage.py
requirements.txt
developer_portfolio/        # Django project settings and URLs
social/                     # Core social app (models, views, forms, migrations)
templates/                  # Django templates (auth + social pages)
static/social/              # Custom CSS
```

## Getting started
1. Create and activate a virtual environment, then install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Apply migrations and create a superuser for admin access:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
3. Run the development server:
   ```bash
   python manage.py runserver
   ```
4. Visit `http://localhost:8000/feed/` to browse the feed. Use the navigation bar to log in, register, or view your profile.

## Key URLs
- `/feed/` — main news feed with friend requests and post composer.
- `/signup/` — registration form.
- `/accounts/login/` — login page (also linked from the navbar).
- `/profile/<username>/` — public profile with edit form for the owner.
- `/admin/` — Django admin console.

## Notes
- HTMX endpoints render only the like button or comment list when requested via HTMX, keeping interactions fast.
- Profile creation is automatic when a user is created.
- The default secret key is for development only; set `DJANGO_SECRET_KEY` in production and disable debug via `DJANGO_DEBUG=0`.
