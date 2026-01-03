import os
from dotenv import load_dotenv

load_dotenv()  # Carga .env

print("Setup OK! DB_URL:", os.getenv("DB_URL"))