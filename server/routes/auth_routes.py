from fastapi import APIRouter

auth_router = APIRouter(prefix='/auth', tags=['Autenticação'])


@auth_router.get('/')
def home():
    return {'mensagem': 'Olá mundo'}
