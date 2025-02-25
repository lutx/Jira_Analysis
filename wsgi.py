from app import create_app

# Create the application instance
application = create_app()
app = application  # for Flask CLI to find the app

if __name__ == "__main__":
    app.run() 