from fastapi import APIRouter
from fastapi.responses import JSONResponse

from scripts.log import update_order_log

from scripts.stats import calculate_nominal_income, make_current_positions, make_transactions_list

stats = APIRouter()

@stats.get('/nominal_income')
def get_nominal_income():
    update_order_log()

    data = calculate_nominal_income()

    return JSONResponse(
        content={
            "message": "success",
            "data": data,
        },
        status_code=200,
    )

@stats.get('/current_assets')
def get_current_assets():
    data = make_current_positions()

    return JSONResponse(
        content={
            "message": "success",
            "data": data,
        },
        status_code=200,
    )

@stats.get('/transactions')
def get_transactions():
    data = make_transactions_list()

    return JSONResponse(
        content={
            "message": "success",
            "data": data,
        },
        status_code=200,
    )

@stats.get('/equity_income')
def get_equity_income(symbol: str, incomeType: str):
    print(symbol, incomeType)
    data = 123

    return JSONResponse(
        content={
            "message": "success",
            "data": data,
        },
        status_code=200,
    )
