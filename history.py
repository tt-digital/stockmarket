import yfinance as yf
import pandas as pd
import mplfinance as mpf
from datetime import date

stock = 'AAPL'
today = date.today()
period = '6mo' # 1mo, 1y,...

data = yf.download(stock, period=period)
mpf.plot(data,type='line',mav=(10,20),volume=True,show_nontrading=True,title=stock + ' Price over ' + period)

df = pd.DataFrame(data)
df.to_csv(str(today) + '_' + stock + '.csv')
