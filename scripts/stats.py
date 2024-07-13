import os
import pandas as pd
from datetime import datetime
import traceback

from apis.alpaca.data import get_recent_bars
from apis.alpaca.infos import get_current_positions, get_infos

from apps.error import CustomError

from scripts.log import PATH_ACTION_LOGS, create_error_log

def calculate_nominal_income() -> dict:
  '''
  Calculate nominal income using action log to make a dictionary {symbol: quantity}
  '''

  try:
    if not os.path.isfile(PATH_ACTION_LOGS):
      return {'symbols': [], 'nominalIncomes': []}

    logs_pd = pd.read_csv(PATH_ACTION_LOGS)
    # order 에 해당하는 action 만 취합
    logs_pd = logs_pd[logs_pd['action'] == 'FILL']
    # 각 order 의 최종적인 income 혹은 cost 계산
    logs_pd['filledFee'] = logs_pd['filledQty'] * logs_pd['filledAvgPrice']

    # 구매 / 판매 각각으로 나눔
    buyLogs = logs_pd[logs_pd['orderSide'] == 'buy']
    sellLogs = logs_pd[logs_pd['orderSide'] == 'sell']

    symbols = list(logs_pd['symbol'].unique())

    if len(symbols) == 0:
      return {
        'symbols': [],
        'nominalIncomes': []
      }

    recentBars = get_recent_bars(symbols=symbols)
    positions = get_current_positions()

    # 현재 보유중인 주식에 대해 실시간 가격을 적용하여 가치 계산
    recentFees = {
      symbol: recentBars[symbol][-1]['o'] * positions[symbol]['qty'] if symbol in positions else 0\
      for symbol in recentBars.keys()
    }

    # 현재 보유중인 주식의 가치 + 판매한 총 금액 - 구매한 총 금액 계산
    nominalIncomes = list(map(
      lambda x: recentFees[x]\
      + sellLogs[sellLogs['symbol'] == x]['filledFee'].sum()\
      - buyLogs[buyLogs['symbol'] == x]['filledFee'].sum(),
      symbols
    ))

    return {
      'symbols': symbols,
      'nominalIncomes': nominalIncomes
    }

  except:
    print(traceback.format_exc())
    create_error_log(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='calculating nominal incomes'
    )

def make_current_positions() -> dict:
  '''
  Make data of current positions list, sum of positive positions, and whole assets
  '''

  try:
    positions = get_current_positions()

    if len(positions.keys()) == 0:
      symbols = []
      currentPositions = []
      currentSum = 0

    recentBars = get_recent_bars(symbols=positions.keys())

    symbols = list(positions.keys())
    currentPositions = [
      recentBars[symbol][-1]['o'] * positions[symbol]['qty'] * (1 if positions[symbol]['position'] == 'long' else -1)\
      for symbol in symbols
    ]
    currentSum = sum([val if val > 0 else 0 for val in currentPositions])

    return {
      'symbols': symbols,
      'currentPositions': currentPositions,
      'currentSum': currentSum
    }

  except:
    print(traceback.format_exc())
    create_error_log(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='making data of current positions and assets'
    )

def make_transactions_list() -> list:
  '''
  Make a list of transactions (deposit & withdrawal) history
  '''

  try:
    accountInfo = get_infos()

    if not os.path.isfile(PATH_ACTION_LOGS):
      return []

    logs_pd = pd.read_csv(PATH_ACTION_LOGS)
    # transaction 에 해당하는 action 만 취합
    logs_pd = logs_pd[logs_pd['action'] == 'TRANS'][['action', 'dateTime', 'netAmount', 'equity']]

    transactionsList = logs_pd.fillna('').to_dict('records')
    transactionsList.append({
      'action': 'current',
      'dateTime': datetime.utcnow().isoformat(timespec='milliseconds') + 'Z',
      'netAmount': 0,
      'equity': float(accountInfo['equity']),
    })

    return transactionsList

  except:
    print(traceback.format_exc())
    create_error_log(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='making a list of transactions history'
    )

# def calculate_equity_income(symbol: str, incomeType: str) -> dict:
#   '''
#   Calculate daily nominal or realized income of a specific equity
#   '''

  
