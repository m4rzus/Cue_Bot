import praw
from datetime import datetime
from time import sleep
from config import *

def printLog( message ):
    print( datetime.now(), end = " " )
    print( message )

def main():
    printLog( "Logging in..." )
    reddit = praw.Reddit( client_id = bot_id, client_secret = bot_secret, password = bot_pwd, user_agent = bot_agent, username = bot_usr )
    printLog( "Logged in..." )

if __name__ == "__main__":
    main()
