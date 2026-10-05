from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "helpdesk.db"
MODEL_DIR = BASE_DIR / "models"
DATA_PATH = BASE_DIR / "data" / "tickets.csv"
UPLOAD_DIR = BASE_DIR / "uploads"
MAX_CONTENT_LENGTH = 8 * 1024 * 1024
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "doc", "docx", "csv"}
SECRET_KEY = "smart-helpdesk-development-key"
