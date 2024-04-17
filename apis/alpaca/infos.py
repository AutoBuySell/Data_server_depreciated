import requests
import os
import traceback
from datetime import datetime
from dotenv import load_dotenv

from apps.error import CustomError

load_dotenv(verbose=True)

baseurl = os.getenv('ALPACA_PAPER_BASEURL')

headers = {
  'accept': 'application/json',
  'APCA-API-KEY-ID': os.getenv('ALPACA_PAPER_KEY'),
  'APCA-API-SECRET-KEY': os.getenv('ALPACA_PAPER_KEY_SECRET'),
}

def get_infos() -> dict:
  '''
  return current account information including buying_power
  '''

  try:
    response = requests.get(baseurl + '/account', headers=headers)

    assert response.status_code == 200, response.json()

    response = response.json()

    return response

  except:
    print(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='getting current infos'
    )

def get_current_positions(symbols: list = []) -> dict[dict[float|str]]:
  '''
  return a dict of current long positions with symbols as key
  , only if the symbol is in the portfolio
  '''

  try:
    response = requests.get(baseurl + '/positions', headers=headers)

    assert response.status_code == 200, response.json()

    response = response.json()

    if len(symbols) == 0:
      return {
        r['symbol']: {
          'qty': float(r['qty']),
          'position': r['side'],
         } for r in response
      }

    return {
      r['symbol']: {
        'qty': float(r['qty']),
        'position': r['side'],
        } for r in response if r['symbol'] in symbols
    }

  except:
    print(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='getting current positions'
    )

def get_actions() -> dict:
  '''
  return a list of activities of recent dates
  '''

  try:
    response = requests.get(baseurl + '/account/activities', headers=headers)

    assert response.status_code == 200, response.json()

    response = response.json()

    results = [{
      'action': r['activity_type'],
      'orderId': r['order_id'] if 'order_id' in r else '',
      'dateTime': r['transaction_time'] if 'transaction_time' in r else datetime.fromisoformat(r['date']).isoformat(timespec='milliseconds') + 'Z',
      'symbol': r['symbol'] if 'symbol' in r else '',
      'orderQty': r['qty'] if 'qty' in r else '',
      'orderSide': r['side'] if 'side' in r else '',
      'orderPrice': r['price'] if 'price' in r else '',
      'orderStatus': r['order_status'] if 'order_status' in r else '',
      'netAmount': r['net_amount'] if 'net_amount' in r else '',
      'perShareAmount': r['per_share_amount'] if 'per_share_amount' in r else '',
      'NtaDescription': r['description'] if 'description' in r else '',
      'NtaStatus': r['status'] if 'status' in r else '',
    } for r in response]

    return results

  except:
    print(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='getting actions'
    )

def get_order(orderId: str) -> dict:
  '''
  특정 id 의 주문 정보 요청, 해당 주문의 orderStatus(주문상태), filledQty(실행주문수), filledAvgPrice(실행평균가) 반환
  Request order infomation of an orderId
  Return orderStatus, filledQty, filledAvgPrice infomation of the order
  '''

  try:
    response = requests.get(
      baseurl + '/orders' + f'/{orderId}',
      headers=headers
    )

    assert response.status_code == 200, response.json()

    response = response.json()

    new_info = {
      'orderStatus': response['status'],
      'filledQty': response['filled_qty'],
      'filledAvgPrice': response['filled_avg_price'] or 0,
    }

    return new_info

  except:
    print(traceback.format_exc())

    CustomError(
      status_code=500,
      message='Internal server error',
      detail='getting an order information'
    )
