from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

from apps.error import DataReqError

from scripts.log import create_action_log, get_action_log, update_order_log, trace_action_log

logging = FastAPI()

@logging.get('/')
def get_logs():
    logs = get_action_log()

    return JSONResponse(
        content={
            "message": "success",
            "data": logs,
        },
        status_code=200,
    )

@logging.post('/')
def create_logs(args: dict = Body(embed=True)):
    if 'symbol' not in args:
        raise DataReqError('args')

    create_action_log(args)

    return JSONResponse(
        content={"message": "success"},
        status_code=201,
    )

@logging.put('/')
def update_logs():
    update_order_log()
    trace_action_log()

    logs = get_action_log()

    return JSONResponse(
        content={
            "message": "success",
            "data": logs,
        },
        status_code=200,
    )

@logging.get('/alarm')
def check_activities():
    trace_action_log()

    return JSONResponse(
        content={"message": "success"},
        status_code=200,
    )
