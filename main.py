from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from apps.error import CustomError

from apps.dataarchiving import dataArchiving
from apps.logging import logging

tags_metadata = [
  {
    "name": "Data Manipulation Server",
    "description": "데이터 처리 서버",
  }
]

origins = [
  "*"
]

app = FastAPI(
  title="AutoTrading Data",
  summary="자동 알고리즘 매매 프로그램 데이터 처리 서버",
  version="0.0.2",
  openapi_tags=tags_metadata,
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.exception_handler(CustomError)
def custom_error_handler(request: Request, exc: CustomError):
    return JSONResponse(
        content={"message": f"{exc.message} in {exc.detail}"},
        status_code=exc.status_code
    )

@app.get('/')
def hello_world():
    '''
    서버 상태 확인용 엔드포인트
    Endpoint for checking the server is alive or not.
    '''
    return JSONResponse(
      content={"message": "HelloWorld!"},
      status_code=200,
    )

app.mount('/dataArchiving', dataArchiving)
app.mount('/logs', logging)
