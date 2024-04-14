import os
import pandas as pd
from datetime import datetime
import traceback

from apps.error import CustomError

from apis.alpaca.infos import get_infos, get_current_positions, get_actions, get_order

LOG_TEMPLATE = {
  'action': '',
  'orderId': '',
  'dateTime': '',
  'symbol': '',
  'confidence': '',
  'orderQty': '',
  'orderSide': '',
  'orderPrice': '',
  'orderStatus': '',
  'filledQty': '',
  'filledAvgPrice': '',
  'position': '',
  'qty': '',
  'buyingPower': '',
  'cash': '',
  'netAmount': '',
  'perShareAmount': '',
}

PATH_ACTION_LOGS = '../data/log_data/action_logs.csv'
PATH_ERROR_LOGS = '../data/log_data/data_server_error_logs.csv'

TERMINATED_STATUS = ['filled', 'canceled', 'expired', 'rejected', 'closed']

def create_action_log(newLog: dict[str|int|float]) -> None:
  '''
  Create a line of action log when an action occured.
  '''

  try:
    accountInfos = get_infos()
    currentPositions = get_current_positions([newLog['symbol']])

    if newLog['symbol'] not in currentPositions:
      position = ''
      qty = 0
    else:
      position = currentPositions[newLog['symbol']]['position']
      qty = currentPositions[newLog['symbol']]['qty']

    emptyLog = LOG_TEMPLATE.copy()
    log = {
      **emptyLog,
      **newLog,
      'date_server': datetime.now().isoformat(timespec='milliseconds') + 'Z',
      'position': position,
      'qty': qty,
      'buyingPower': accountInfos['buying_power'],
      'cash': accountInfos['cash'],
    }

    if os.path.isfile(PATH_ACTION_LOGS):
      logs_pd = pd.read_csv(PATH_ACTION_LOGS)
      logs_pd = pd.concat([logs_pd, pd.DataFrame(log, index=[0])], ignore_index=True)
    else:
      logs_pd = pd.DataFrame(log, index=[0])

    logs_pd.to_csv(PATH_ACTION_LOGS, index=False)

  except:
    print(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='creating an action log'
    )

def update_order_log():
  '''
  Update lines of order logs which are not in terminated status
  '''

  try:
    if not os.path.isfile(PATH_ACTION_LOGS):
      return

    logs_pd = pd.read_csv(PATH_ACTION_LOGS)
    orderIds = logs_pd[~logs_pd['orderStatus'].isin(TERMINATED_STATUS)]['orderId']

    for orderId in orderIds:
      new_info = get_order(orderId=orderId)

      index = logs_pd[logs_pd['orderId'] == orderId].index

      for key in new_info.keys():
        logs_pd.loc[index, key] = new_info[key]

    logs_pd.to_csv(PATH_ACTION_LOGS, index=False)

  except:
    print(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='updating order logs'
    )

def trace_action_log():
  '''
  Get uncontrollable actions occured to record
  '''

  try:
    actions = get_actions()

    emptyLog = LOG_TEMPLATE.copy()
    newLogs = []
    for action in actions:
      newLogs.append({
        **emptyLog,
        **actions,
      })

    if os.path.isfile(PATH_ACTION_LOGS):
      logs_pd = pd.read_csv(PATH_ACTION_LOGS)
      logs_pd = pd.concat([logs_pd, pd.DataFrame(newLogs, index=[0])], ignore_index=True)\
                  .drop_duplicates().sort_values('dateTime').reset_index(drop=True)
    else:
      logs_pd = pd.DataFrame(newLogs, index=[0])

    logs_pd.to_csv(PATH_ACTION_LOGS, index=False)

  except:
    print(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='tracing action logs'
    )

def get_action_log():
  '''
  Get all of the action logs stored currently
  '''

  try:
    if not os.path.isfile(PATH_ACTION_LOGS):
      return []

    logs_pd = pd.read_csv(PATH_ACTION_LOGS)

    return logs_pd.to_dict(orient='records')

  except:
    print(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='getting all action logs'
    )

def create_error_log(content: str) -> None:
  '''
  Create a line of error log when an error occured.
  '''

  try:
    new_log = {
      'date': datetime.now().isoformat(timespec='milliseconds') + 'Z',
      'content': content
    }

    if os.path.isfile(PATH_ERROR_LOGS):
      logs_pd = pd.read_csv(PATH_ERROR_LOGS)
      logs_pd = pd.concat([logs_pd, pd.DataFrame(new_log, index=[0])], ignore_index=True)
    else:
      logs_pd = pd.DataFrame(new_log, index=[0])

    logs_pd.to_csv(PATH_ERROR_LOGS, index=False)

  except:
    print(traceback.format_exc())

    raise CustomError(
      status_code=500,
      message='Internal server error',
      detail='creating an error log'
    )
