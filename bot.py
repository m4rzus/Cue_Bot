from SnookerAPI import SnookerAPI
from cue_bot import Cue_Bot
import schedule
import time

bot = Cue_Bot()

schedule.every().day.at( "1:00" ).do( bot.PostTodayMatches )
schedule.every( 2 ).hours.do( bot.UpdateTodayMatches )
schedule.every( 30 ).minutes.do( bot.CheckResults )
schedule.every( 15 ).seconds.do( bot.CheckComments )

while True:
    schedule.run_pending()
    sleep( 1 )
