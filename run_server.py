# run_server.py
from waitress import serve
from restaurant.wsgi import application  # replace 'your_project_name' with your Django project folder

if __name__ == "__main__":
    # Runs server on port 8000, accessible locally
    serve(application, host="0.0.0.0", port=8000)
