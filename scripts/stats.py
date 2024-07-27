import os
import pandas as pd
from datetime import datetime, timezone, timedelta
from itertools import accumulate
import re
import traceback

from apis.alpaca.data import get_recent_bars
from apis.alpaca.infos import get_current_positions, get_infos

from apps.error import CustomError

from scripts.log import PATH_ACTION_LOGS, create_error_log
from scripts.archiving import PATH_MARKET_LONG_DATA, historical_archiving

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
    recentValues = {
      symbol: recentBars[symbol][-1]['o'] * positions[symbol]['qty'] if symbol in positions else 0\
      for symbol in recentBars.keys()
    }

    # 현재 보유중인 주식의 가치 + 판매한 총 금액 - 구매한 총 금액 계산
    nominalIncomes = list(map(
      lambda x: recentValues[x]\
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
    logs_pd = logs_pd[logs_pd['action'].isin(['CSD', 'TRANS'])][['action', 'dateTime', 'netAmount', 'equity']]

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

def calculate_equity_performance(
  symbol: str,
  startDate: str,
  endDate: str,
  dateInterval: str
):
  '''
  Calculate daily nominal or realized income of a specific equity
  dateInterval: number(int or float) + string('Y' or 'M' or 'd')
      eg: '52d' or '2M' or '1.5Y'
  '''
  dayMultiplier = {
    'd': 1,
    'M': 30,
    'Y': 365
  }

  match = re.match(r'^(\d+(\.\d+)?)([A-Za-z])$', dateInterval)

  if startDate == None:
      startDate = '2000-01-01T00:00:00Z'
  if endDate == None:
      endDate = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec='milliseconds') + 'Z'
  if dateInterval == None:
      dateInterval = '1.5M'

  try:
    if match:
      interval_i = float(match.group(1))
      interval_s = match.group(3)
    else:
      raise ValueError(f"Input string '{dateInterval}' does not match the required format")

    dayInterval = timedelta(days=interval_i * dayMultiplier[interval_s])

    # historical bars 를 호출하고, 호출 기간과 실제 기간이 겹치는 구간으로 데이터 추출
    timeframe = '1Day'

    historical_archiving(
      symbol=symbol,
      timeframe=timeframe,
      startDate=startDate,
      endDate=endDate
    )

    data_pd = pd.read_csv(PATH_MARKET_LONG_DATA + f'{symbol}_{timeframe}.csv')
    data_pd['date'] = pd.to_datetime(data_pd['t'])

    minDate = max(startDate, data_pd['t'].iloc[0])
    maxDate = min(endDate, data_pd['t'].iloc[-1])

    data_pd_filter = data_pd[
      (data_pd['date'] >= datetime.fromisoformat(minDate[:-1]).replace(tzinfo=timezone.utc))\
      & (data_pd['date'] <= datetime.fromisoformat(maxDate[:-1]).replace(tzinfo=timezone.utc))
    ].resample(dayInterval, on='date').first()

    # 구매/판매 리스트 파악하고 구매/판매 날짜를 추출한 데이터에 추가
    # 구매/판매 날짜의 추정 가격 및 전체 날짜의 보유량(accuQty), 소요금액(accuFee) 기록
    if not os.path.isfile(PATH_ACTION_LOGS):
      return {'symbols': [], 'nominalIncomes': []}

    logs_pd = pd.read_csv(PATH_ACTION_LOGS)
    logs_pd = logs_pd[(logs_pd['action'] == 'FILL') & (logs_pd['symbol'] == symbol)][['dateTime', 'orderSide', 'filledQty', 'filledAvgPrice']]
    logs_pd['date'] = pd.to_datetime(logs_pd['dateTime'])

    logs_pd = logs_pd.reset_index(drop=True).set_index('date')

    logs_pd['signedQty'] = -logs_pd['filledQty']
    logs_pd.loc[logs_pd['orderSide'] == 'buy', ['signedQty']] = logs_pd['filledQty']
    logs_pd['filledFee'] = logs_pd['signedQty'] * logs_pd['filledAvgPrice']

    # 목표 기간에 포함된 날짜에 대해 nominal(o(price), accuQty, accuFee) 또는 realized income 계산
    # nominal: o * accuQty - accuFee
    # realized: 보유량이 줄어들었을 때에만 발생. 단가 변화에 수량 변화를 곱하여 계산. accumulated 방식으로 표현.

    logs_pd['accuQty'] = list(accumulate(logs_pd['signedQty']))
    logs_pd['accuFee'] = list(accumulate(logs_pd['filledFee']))

    avgPerShare = []
    realized = []
    for i in range(len(logs_pd)):
      if i == 0:
        if logs_pd['signedQty'].iloc[i] > 0:
          avgPerShare.append(logs_pd['filledAvgPrice'].iloc[i])
        realized.append(0)
        continue

      if logs_pd['signedQty'].iloc[i] > 0:
        if logs_pd['accuQty'].iloc[i - 1] > 0:
          avgPerShare.append((logs_pd['accuQty'].iloc[i - 1] * avgPerShare[i - 1] + logs_pd['filledFee'].iloc[i]) / logs_pd['accuQty'].iloc[i])
        else:
          avgPerShare.append(logs_pd['filledAvgPrice'].iloc[i])
      else:
        avgPerShare.append(avgPerShare[-1])

      priceBefore = 0 if logs_pd['accuQty'].iloc[i - 1] == 0 else avgPerShare[i - 1]
      priceToSell = logs_pd['filledAvgPrice'].iloc[i]
      qtyChanged = logs_pd['signedQty'].iloc[i]
      qtyChanged = 0 if qtyChanged > 0 else qtyChanged

      realized.append(-(priceToSell - priceBefore) * qtyChanged + realized[-1])
    logs_pd['realized'] = realized
    print(avgPerShare)
    print(realized)

    # 목표 기간에 포함된 날짜에 대해 price 정보 추출
    logs_pd['o'] = pd.concat([data_pd.set_index('date'), logs_pd]).sort_index()['o'].ffill()[logs_pd.index]

    merge_pd = pd.concat([data_pd_filter, logs_pd[['accuQty', 'accuFee', 'realized', 'o']]]).sort_index()
    merge_pd['o'].ffill(inplace=True)
    merge_pd['accuQty'].ffill(inplace=True)
    merge_pd['accuFee'].ffill(inplace=True)
    merge_pd['accuQty'].fillna(0, inplace=True)
    merge_pd['accuFee'].fillna(0, inplace=True)
    merge_pd['realized'].ffill(inplace=True)
    merge_pd['realized'].bfill(inplace=True)

    merge_pd = merge_pd.reset_index()[['date', 'o', 'accuQty', 'accuFee', 'realized']]

    merge_pd = merge_pd[
      (merge_pd['date'] >= datetime.fromisoformat(minDate[:-1]).replace(tzinfo=timezone.utc))\
      & (merge_pd['date'] <= datetime.fromisoformat(maxDate[:-1]).replace(tzinfo=timezone.utc))
    ]

    merge_pd['date'] = merge_pd['date'].dt.strftime('%Y-%m-%d')
    merge_pd.to_csv('test.csv')

    return merge_pd.to_dict(orient='list')

  except:
    print(traceback.format_exc())
    create_error_log(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='calculating historical equity performance'
    )
