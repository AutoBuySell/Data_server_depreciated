import pandas as pd
import os
import traceback

from apis.alpaca.data import get_recent_bars, get_historical_bars
from apps.error import CustomError

PATH_MARKET_DATA = '../data/market_data/'
PATH_MARKET_LONG_DATA = '../data/market_long_data/'

def real_time_archiving(symbols: list[int], timeframe: str) -> list[str]:
  '''
  실시간으로 주가 정보를 받아 저장소에 업데이트 하는 함수
  Updating stored data with real-time data

  1. 해당 symbol 에 대한 기록 파일이 존재하지 않는 경우 새로 파일을 생성하여 기록
  2. 최종 항목을 다운받아 봤을 때 저장된 내용과 변동사항이 없는 경우 수행 X
  3. 최종 항목을 다운받아 봤을 때 새로 추가된 항목이 있을 경우 새로운 내용을 덧붙여 갱신
  4. 최종 항목을 다운받아 봤을 때 완전히 새로운 항목인 경우 모든 내용을 덧붙여 갱신
  5. 그 외 수행 X

  1, 3, 4 의 경우 새로 업데이트 된 것으로 간주함
  새로 업데이트 된 symbol 리스트 를 반환함
  Return a list of update symbols
  '''
  updated = []

  data = get_recent_bars(symbols, timeframe)

  try:
    for key in data.keys():
      if not os.path.isfile(PATH_MARKET_DATA + f'{key}_{timeframe}.csv'): # In case of No stored data
        pd.DataFrame.from_records(data[key], columns=['t', 'o']).to_csv(PATH_MARKET_DATA + f'{key}_{timeframe}.csv', index=False)
      else:
        prev_pd = pd.read_csv(PATH_MARKET_DATA + f'{key}_{timeframe}.csv')
        new_pd = pd.DataFrame.from_records(data[key], columns=['t', 'o'])
        if prev_pd['t'].iloc[-1] == new_pd['t'].iloc[-1]: # In case of stored data is up to date (not update)
          continue
        elif prev_pd['t'].iloc[-1] in list(new_pd['t']): # In case any duplicated data exists, update not duplicated data only
          pd.concat(
            [prev_pd, new_pd.iloc[list(new_pd['t']).index(prev_pd['t'].iloc[-1]) + 1:]]
          ).to_csv(PATH_MARKET_DATA + f'{key}_{timeframe}.csv', index=False)
        elif prev_pd['t'].iloc[-1] < new_pd['t'].iloc[0]: # In case no duplicated data exists, update all new data
          pd.concat(
            [prev_pd, new_pd]
          ).to_csv(PATH_MARKET_DATA + f'{key}_{timeframe}.csv', index=False)
        else: # not update
          continue

      updated.append(key)

      return updated

  except Exception:
    print(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message="Internal server error",
      detail="updating realtime data"
    )

def historical_archiving(symbol: str, timeframe: str, startDate: str, endDate: str) -> None:
  '''
  평가용 장기 데이터를 다운받아 저장소에 저장하는 함수
  Storing long-term data for evaluation

  원하는 시작 날짜와 종료 날짜 데이터가 이미 모두 존재하는 경우 추가 작업은 진행하지 않음
  '''
  if os.path.isfile(PATH_MARKET_LONG_DATA + f'{symbol}_{timeframe}.csv'):
    prev_pd = pd.read_csv(PATH_MARKET_LONG_DATA + f'{symbol}_{timeframe}.csv')
    oldest = prev_pd['t'].iloc[0]
    newest = prev_pd['t'].iloc[-1]

    if startDate >= oldest and endDate <= newest:
      return

  data = get_historical_bars(symbol, timeframe, startDate, endDate)
  if len(data) == 0:
    return

  data_pd = pd.DataFrame.from_records(data, columns=['t', 'o'])
  data_pd['judge'] = [0] * len(data_pd)
  data_pd.to_csv(PATH_MARKET_LONG_DATA + f'{symbol}_{timeframe}.csv', index=False)
