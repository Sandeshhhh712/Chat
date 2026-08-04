from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

SECRET_KEY = "5b83430a468a304c17da69cd5835d250dd169a05847e0f86b630bd567091aa8c"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_hash = PasswordHash.recommended()


def get_password_hash(password):
    return pwd_hash.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_hash.verify(plain_password, hashed_password)


oauth2scheme = OAuth2PasswordBearer(tokenUrl="token")
