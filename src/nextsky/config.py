from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
COUNTRIES_CSV = DATA_DIR / "countries.csv"
TARGET_COUNTRIES_CSV = DATA_DIR / "target_countries.csv"
GEOJSON_COUNTRIES_PATH = DATA_DIR / "geo" / "ne_50m_admin_0_countries.geojson"
DEFAULT_DB_PATH = DATA_DIR / "nextcountry.db"
