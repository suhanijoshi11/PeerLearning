from app import app

# REQUIRED for Vercel WSGI compatibility
def handler(environ, start_response):
    return app.wsgi_app(environ, start_response)
