class CustomError(Exception):
  def __init__(self, status_code: int, message: str, detail: str) -> None:
    '''
    status_code: appropriate status code
    message: general message for the error
    detail: detail cause of the error for development usage

    ex)
    status_code: 500
    message: Internal server error
    detail: accessing to Alpaca APIs
    '''

    self.status_code = status_code
    self.message = message
    self.detail = detail

class DataReqError(Exception):
  def __init__(self, name: str) -> None:
    '''
    name: A string of required data which were absent
    '''

    self.message = f'Required variables, {name}, were absent'
