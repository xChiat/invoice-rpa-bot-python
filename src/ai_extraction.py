import os
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
if not HF_TOKEN:
    raise ValueError("HUGGINGFACE_TOKEN no encontrado en .env. Crea uno en huggingface.co/settings/tokens.")

# TODO Extraccion inteligente de campos clave