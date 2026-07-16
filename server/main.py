from fastapi import FastAPI

app = FastAPI()


@app.get('/')
def home():

    return {'mensagem': 'Olá mundo!'}


if __name__ == '__main__':
    app()
