import os
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg://locklab:locklab_demo_pw@localhost:17742/locklab')
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
JWT_SECRET = os.getenv('JWT_SECRET', 'local-lock-lab-change-before-public-use')
REVIEW_TTL_SECONDS = int(os.getenv('REVIEW_TTL_SECONDS', '60'))
REVIEW_SWEEP_SECONDS = int(os.getenv('REVIEW_SWEEP_SECONDS', '10'))
ARTIFACT_DIR = os.getenv('ARTIFACT_DIR', '/artifacts')
