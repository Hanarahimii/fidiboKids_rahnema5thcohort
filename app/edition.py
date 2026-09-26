"""Explicit, server-enforced separation of local presentation and child test editions."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'edition.json').read_text()) if (ROOT / 'edition.json').exists() else {}
MODE = os.getenv('KIDSBOOK_EDITION', CONFIG.get('mode', 'presentation'))
if MODE not in ('presentation', 'child-test'):
    raise RuntimeError('KIDSBOOK_EDITION must be presentation or child-test')
DONATION_URL = os.getenv('KIDSBOOK_DONATION_URL', CONFIG.get('donation_url', '')).strip()
if DONATION_URL and (urlparse(DONATION_URL).scheme != 'https' or not urlparse(DONATION_URL).netloc or urlparse(DONATION_URL).username):
    raise RuntimeError('Donation URL must be an absolute HTTPS payment link')
SECURE_COOKIES = os.getenv('KIDSBOOK_SECURE_COOKIES', '0') == '1'
