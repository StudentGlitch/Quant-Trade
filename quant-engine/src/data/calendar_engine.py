import pandas_market_calendars as mcal
from datetime import datetime
import pytz
from loguru import logger

class CalendarEngine:
    """
    Phase 18.1: Global Timezone & Calendar Normalization.
    Handles disparate global holidays and overlapping sessions.
    """
    def __init__(self):
        # Initialize standard supported calendars
        try:
            self.us_cal = mcal.get_calendar('XNYS') # NYSE/NASDAQ
            # mcal doesn't have native IDX sometimes, we can use a custom or fallback. 
            # In practice, Singapore (XSES) or Hong Kong (XSES) has similar hours, 
            # but let's assume we implement a basic custom calendar for IDX if not available.
            # For MVP, we'll try to get XIDX, fallback to an Asian proxy or custom logic.
            try:
                self.idx_cal = mcal.get_calendar('XIDX')
            except Exception:
                logger.warning("XIDX calendar not found in pandas_market_calendars. Using custom/24-7 fallback for MVP.")
                self.idx_cal = mcal.get_calendar('24/7') 
                
            self.crypto_cal = mcal.get_calendar('24/7')
            logger.info("Global calendars initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize market calendars: {e}")
            raise

    def is_market_open(self, exchange_code: str, dt: datetime = None) -> bool:
        """Check if a specific exchange is currently in an active trading session."""
        if dt is None:
            dt = datetime.now(pytz.utc)
            
        cal = self._get_cal(exchange_code)
        
        # Determine if the given dt falls within an open session today
        schedule = cal.schedule(start_date=dt.date(), end_date=dt.date())
        if schedule.empty:
            return False
            
        market_open = schedule.iloc[0]['market_open']
        market_close = schedule.iloc[0]['market_close']
        
        return market_open <= dt <= market_close

    def get_last_close(self, exchange_code: str, dt: datetime = None) -> datetime:
        """Get the timestamp of the last official market close."""
        if dt is None:
            dt = datetime.now(pytz.utc)
            
        cal = self._get_cal(exchange_code)
        schedule = cal.schedule(start_date=dt.date() - pd.Timedelta(days=10), end_date=dt.date())
        
        # Find the most recent close that is strictly before `dt`
        past_closes = schedule[schedule['market_close'] < dt]
        if past_closes.empty:
            return dt # Fallback
            
        return past_closes.iloc[-1]['market_close']

    def _get_cal(self, exchange_code: str):
        code = exchange_code.upper()
        if code in ['NASDAQ', 'NYSE', 'XNYS']:
            return self.us_cal
        elif code in ['IDX', 'XIDX']:
            return self.idx_cal
        elif code in ['BINANCE', 'CRYPTO']:
            return self.crypto_cal
        else:
            logger.warning(f"Unknown exchange {code}, defaulting to 24/7.")
            return self.crypto_cal
