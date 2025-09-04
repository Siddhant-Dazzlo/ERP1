web: gunicorn --config gunicorn.conf.py wsgi:app
worker: celery -A celery_app worker --loglevel=info
