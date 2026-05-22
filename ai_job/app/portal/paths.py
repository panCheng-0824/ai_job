"""ai_job 根目录与数据文件路径（供门户业务层复用）。"""

from pathlib import Path

# ai_job/app/portal/paths.py -> app -> ai_job
AI_JOB_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = AI_JOB_ROOT / "config"
DATA_DIR = AI_JOB_ROOT / "data"
STUDENT_FILE = DATA_DIR / "user_student.json"
COMPANY_FILE = DATA_DIR / "user_business.json"
JOB_FILE = DATA_DIR / "business_job.json"
USERMODEL_FILE = DATA_DIR / "usermodel.json"
SESSION_FILE = DATA_DIR / "chat_sessions.json"
