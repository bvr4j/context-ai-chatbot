from app.main import app

# Expose app for ASGI servers and Vercel serverless entrypoint
__all__ = ["app"]
