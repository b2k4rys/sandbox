from dotenv import load_dotenv
import os



load_dotenv()

DATABASE_URL=os.getenv('DATABASE_URL')
token_expire_minutes=os.getenv('TOKEN_EXPIRE_MINUTES')
SECRET_KEY=os.getenv('SECRET_KEY')