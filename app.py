from src import create_app
import os

# Create the Flask application
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, port=port, host="0.0.0.0")
