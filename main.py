from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import os
from dotenv import load_dotenv

from apps.error import CustomError, DataReqError

from apps.dataarchiving import dataArchiving
from apps.logging import logging
from apps.stats import stats

tags_metadata = [
  {
    "name": "Data Manipulation Server",
    "description": "데이터 처리 서버",
  }
]

load_dotenv(verbose=True)

frontServerUrl = os.getenv('FRONT_SERVER_URL')

origins = [
    frontServerUrl,
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

@app.exception_handler(DataReqError)
def data_error_handler(request: Request, exc: DataReqError):
    return JSONResponse(
        content={"message": exc.message},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
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

app.include_router(dataArchiving, prefix='/dataArchiving')
app.include_router(logging, prefix='/logs')
app.include_router(stats, prefix='/stats')
