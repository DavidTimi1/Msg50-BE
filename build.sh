set -o errexit

echo "Installing requirements..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating superuser..."
python manage.py create_admin

echo "Starting deployment..."

