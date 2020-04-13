import os

SERVER_HOST_MASK = os.environ.get('NFCMUSIK_SERVER_HOST', default='0.0.0.0')
SERVER_PORT = os.environ.get('NFCMUSIK_SERVER_PORT', 5000)
MUSIC_ROOT = os.environ.get('NFCMUSIK_AUDIO_FILE_ROOT', '/usr/local/nfcmusik/music')
DEFAULT_VOLUME = os.environ.get('NFCMUSIK_AUDIO_VOLUME', 70)
