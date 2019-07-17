from SnookerAPI import SnookerAPI
import sqlite3
import config
import datetime
import time
import praw

def printLog( message ):
    print( datetime.datetime.now(), end = " " )
    print( message )

class Cue_Bot:

    def __init__( self ):
        self.signature = "^(built by /u/m4rzus | data from) ^[Snooker.org](http://www.snooker.org/)"
        self.commands = {
            "video" : "!cue_video",
            "live" : "!cue_live"
        }
        self.tables = [
            "CREATE TABLE IF NOT EXISTS tournaments( id INTEGER PRIMARY KEY AUTOINCREMENT, tournament_id INTEGER, approved INTEGER );",
            "CREATE TABLE IF NOT EXISTS matches( id INTEGER PRIMARY KEY AUTOINCREMENT, tournament_id INTEGER, match_id INTEGER, post_id TEXT, finished INTEGER, date_played TEXT );",
            "CREATE TABLE IF NOT EXISTS replies( id INTEGER PRIMARY KEY AUTOINCREMENT, comment_id TEXT );"
        ]
        self.api = SnookerAPI()
        self.conn = sqlite3.connect( config.bot_database )
        self.cur = self.conn.cursor()
        printLog( "SnookerAPI, SQLite connection and cursor set..." )
        self.CreateTables()
        printLog( "Tables created..." )
        self.reddit = self.Login()
        printLog( "Logged in to Reddit...")

    # ======================================================================== #

    def CreateTables( self ):
        for table in self.tables:
            self.cur.execute( table )
        self.conn.commit()

    # ======================================================================== #

    def Login( self ):
        return praw.Reddit( client_id = config.bot_id, client_secret = config.bot_secret, password = config.bot_pwd, user_agent = config.bot_agent, username = config.bot_usr )

    # ======================================================================== #

    def GetOnlyApproved( self, data, in_json = "ID" ):
        sql = "SELECT tournament_id FROM tournaments WHERE approved=1;"
        self.cur.execute( sql )
        approved_ids = [ x[ 0 ] for x in self.cur.fetchall() ]

        data = [ x for x in data if x[ in_json ] in approved_ids ]
        return data

    # ======================================================================== #

    def isMatchNotSaved( self, id ):
        sql = "SELECT DISTINCT id FROM matches WHERE match_id={};".format( id )
        self.cur.execute( sql )
        return not self.cur.fetchall()

    # ======================================================================== #

    def PostToSubreddit( self, title, text ):
        success = False
        while not success:
            try:
                post = self.reddit.subreddit( config.bot_subreddit ).submit( title, selftext = text )
                success = True
            except Exception as e:
                printLog( e )
                printLog( "^ sleeping for 2 minutes..." )
                time.sleep( 2 * 60 )
        return post

    # ======================================================================== #

    def ReplyToComment( self, comment, text ):
        success = False
        while not success:
            try:
                comment.reply( text )
                success = True
            except Exception as e:
                printLog( e )
                printLog( "^ sleeping for 20 seconds..." )
                time.sleep( 20 )

    # ======================================================================== #

    def FormatMatchForPost( self, match ):
        player1_data = self.api.GetPlayer( match[ "Player1ID" ] )
        player2_data = self.api.GetPlayer( match[ "Player2ID" ] )
        text = "### {} {} ({}) vs {} {} ({})".format( player1_data[ "FirstName" ], player1_data[ "LastName" ], player1_data[ "Nationality" ], player2_data[ "FirstName" ], player2_data[ "LastName" ], player2_data[ "Nationality" ] )
        text += "\n\n"
        text += "Event: **{}**".format( match[ "EventName" ] )
        text += "\n\n"
        text += "Scheduled start: **{}**".format( match[ "ScheduledDate" ].split( "T" )[ 1 ][ :-1: ] )
        text += "\n\n"
        text += "[WorldSnooker](http://livescores.worldsnookerdata.com/LiveScoring/Match/{}/{}/) ^1".format( match[ "EventWorldSnookerID" ], match[ "WorldSnookerID" ] )
        text += "\n\n---\n\n"
        return text

    # ======================================================================== #

    def PostTodayMatches( self ):
        printLog( "=> Requesting today matches..." )
        matches =  self.GetOnlyApproved( self.api.GetTodayMatches(), "EventID" )
        matches = [ x for x in matches if self.isMatchNotSaved( x[ "WorldSnookerID" ] ) and x[ "WorldSnookerID" ] != 0 ]
        text = ""

        if len( matches ) == 0:
            printLog( "No matches for today..." )
            return

        printLog( "Formatting text..." )
        today = str( datetime.date.today() )
        text += "#### {} matches for today ({})\n\n".format( len( matches ), today )
        for match in matches:
            text += self.FormatMatchForPost( match )
        text += "^1 works while match is being played"
        text += "\n\n"
        text += self.signature

        # Post to Reddit
        printLog( "Posting to Reddit..." )
        post = self.PostToSubreddit( "[cue_bot] Matches for " + str( datetime.date.today() ), text )

        # Save into database
        printLog( "Saving to database..." )
        for match in matches:
            sql = "INSERT INTO matches( tournament_id, match_id, post_id, finished, date_played ) VALUES( {}, {}, \"{}\", 0, \"{}\" );".format( match[ "EventID" ], match[ "WorldSnookerID" ], post.id, today )
            self.cur.execute( sql )
        self.conn.commit()
        printLog( "Successfully posted today matches..." )

    # ======================================================================== #

    # Look for matches which were with WorldSnookerID == 0 and update them
    def UpdateTodayMatches( self ):
        printLog( "=> Updating today matches..." )
        today = str( datetime.date.today() )
        sql = "SELECT post_id FROM matches WHERE date_played=\"{}\";".format( today )
        self.cur.execute( sql )
        post_id = self.cur.fetchall()

        if not post_id:
            printLog( "No post to be updated..." )
            return

        post_id = post_id[ 0 ][ 0 ]

        raw_matches =  self.GetOnlyApproved( self.api.GetTodayMatches(), "EventID" )
        matches = [ x for x in raw_matches if self.isMatchNotSaved( x[ "WorldSnookerID" ] ) and x[ "WorldSnookerID" ] != 0 ]

        if not matches:
            printLog( "No matches to be updated..." )
            return

        printLog( "Formatting..." )
        text = "# Update! {} new matches!\n\n---\n\n".format( len( matches ) )
        for match in matches:
            text += self.FormatMatchForPost( match )
        text += "^1 works while match is being played"
        text += "\n\n"
        text += self.signature

        # Using ReplyToComment on PRAW Submission ( has the same .reply() method as Comment)
        self.ReplyToComment( self.reddit.submission( post_id ), text )

        printLog( "Saving to database..." )
        for match in matches:
            sql = "INSERT INTO matches( tournament_id, match_id, post_id, finished, date_played ) VALUES( {}, {}, \"{}\", 0, \"{}\" );".format( match[ "EventID" ], match[ "WorldSnookerID" ], post_id, today )
            self.cur.execute( sql )
        self.conn.commit()

        # Check if more matches with WorldSnookerID == 0 present
        if not [ x for x in raw_matches if x[ "WorldSnookerID" ] == 0 ]:
            sql = "DELETE FROM matches WHERE match_id=0 AND date_played=\"{}\";".format( today )
            self.cur.execute( sql )
            self.conn.commit()
        printLog( "Successfully updated today matches..." )

    # ======================================================================== #

    def CheckResults( self ):
        printLog( "=> Looking for results..." )
        # Get unfinished tournaments
        printLog( "Requesting all unfinished tournaments..." )
        sql = "SELECT DISTINCT tournament_id FROM matches WHERE finished=0;"
        self.cur.execute( sql )
        events = [ x[ 0 ] for x in self.cur.fetchall() ]
        if not events:
            printLog( "No matches without results..." )
            return

        # Get all matches
        printLog( "Requesting all matches for unfinished tournaments..." )
        matches = []
        for id in events:
            matches += self.api.GetMatchesByEvent( id )

        # Get unfinished matches from database
        printLog( "Requesting all unfinished matches..." )
        sql = "SELECT match_id, post_id FROM matches WHERE finished=0;"
        self.cur.execute( sql )
        # Save match - post association
        matches_posts = {}
        for match in self.cur.fetchall():
            matches_posts[ match[ 0 ] ] = match[ 1 ]
        # Filter out unfinished matches jsons wich already ended
        printLog( "Deleting all necessary matches..." )
        matches = [ x for x in matches if x[ "WorldSnookerID" ] in matches_posts and x[ "WinnerID" ] != 0 ]
        # For each post and save to database
        printLog( "Formating, posting and saving results..." )
        for match in matches:
            player1_data = self.api.GetPlayer( match[ "Player1ID" ] )
            player2_data = self.api.GetPlayer( match[ "Player2ID" ] )
            text = "Results just came in!"
            text += "\n\n"
            text += "### {} {} ({}) >!{}!< vs >!{}!< {} {} ({})".format( player1_data[ "FirstName" ], player1_data[ "LastName" ], player1_data[ "Nationality" ], match[ "Score1" ], match[ "Score2" ], player2_data[ "FirstName" ], player2_data[ "LastName" ], player2_data[ "Nationality" ] )
            text += "\n\n"
            text += "{} - {}".format( match[ "StartDate" ], match[ "EndDate" ] )
            if match[ "Note" ] != "":
                text += "\n\n Note: " + match[ "Note" ]
            text += "\n\n"
            text += "[WorldSnooker](http://livescores.worldsnookerdata.com/Matches/Result/{}/{}/)".format( match[ "EventWorldSnookerID" ], match[ "WorldSnookerID" ] )
            if match[ "VideoURL" ] != "":
                text += " | [Video]({})".format( match[ "VideoURL" ] )
            text += "\n\n---\n\n"
            text += "^(No video found? Try replying !cue_video {} and I will try to find it!)".format( match[ "WorldSnookerID" ] )
            text += "\n\n"
            text += self.signature
            self.ReplyToComment( self.reddit.submission( matches_posts[ match[ "WorldSnookerID" ] ] ), text )

            sql = "UPDATE matches SET finished=1 WHERE match_id=" + str( match[ "WorldSnookerID" ] )
            self.cur.execute( sql )

        self.conn.commit()
        printLog( "Successfully posted results for {} matches".format( len( matches ) ) )

    # ======================================================================== #

    def SaveReply( self, comment_id ):
        sql = "INSERT INTO replies( comment_id ) VALUES( \"{}\" )".format( comment_id )
        self.cur.execute( sql )
        self.conn.commit()

    # ======================================================================== #

    def IsNotReplied( self, comment ):
        sql = "SELECT * FROM replies WHERE comment_id=\"{}\";".format( comment.id )
        self.cur.execute( sql )
        return not self.cur.fetchall()

    # ======================================================================== #

    def GetVideo( self, match_id ):
        sql = "SELECT tournament_id FROM matches WHERE match_id={};".format( match_id )
        self.cur.execute( sql )
        data = self.cur.fetchall()
        if not data:
            return []
        match = [ x for x in self.api.GetMatchesByEvent( data[ 0 ][ 0 ] ) if x[ "WorldSnookerID" ] == match_id ]
        if not match:
            return []
        if match[ 0 ][ "VideoURL" ] == "":
            return []
        return match[ 0 ][ "VideoURL" ]

    # ======================================================================== #

    def ReplyVideo( self, comment ):
        printLog( "Replying to video request made by {} - {}".format( comment.author, comment.id ) )
        message = comment.body.split()
        if len( message ) < 2 or not message[ 1 ].isdigit():
            printLog( "Something wrong, ignoring..." )
            printLog( comment.body )
            return

        video = self.GetVideo( int( message[ 1 ] ) )

        if not video:
            printLog( "Match not found..." )
            text = "Unfortunately I couldn't find video footage of this match.\n\nTry later if your match is not older than several days."
        else:
            printLog( "Match found..." )
            text = "I found a video for this match! [Click here to watch it!]({})".format( video )

        text += "\n\n---\n\n"
        text += self.signature

        self.ReplyToComment( comment, text )
        self.SaveReply( comment.id )
        printLog( "Replied and saved..." )

    # ======================================================================== #

    def ReplyLive( self, comment ):
        printLog( "Replying to live request made by {} - {}".format( comment.author, comment.id ) )
        if comment.submission.author != config.bot_usr:
            printLog( "Submission not made by me..." )
            return
        printLog( "Getting all live matches..." )
        matches = self.api.GetLiveMatches()
        if not matches:
            printLog( "No live matches..." )
            self.ReplyToComment( comment, "No live matches." )
            self.SaveReply( comment.id )
            return

        printLog( "Formatting..." )
        text = "# Currently Live Matches\n\n"
        for match in matches:
            if match[ "Player1" ].strip() == "" or match[ "Player2" ].strip() == "":
                text += "{} vs {}".format( match[ "Nationality1" ], match[ "Nationality2" ] )
            else:
                text += "{} vs {}".format( match[ "Player1" ], match[ "Player2" ] )
            text += " - >!{}:{}!<\n\n".format( match[ "Score1" ], match[ "Score2" ] )
        text += "\n\n---\n\n"
        text += self.signature
        self.ReplyToComment( comment, text )
        self.SaveReply( comment.id )
        printLog( "Replied and saved..." )

    # ======================================================================== #

    def CheckComments( self ):
        printLog( "=> Looking at comments..." )
        for comment in self.reddit.subreddit( config.bot_subreddit ).comments( limit = 50 ):
            command = comment.body.split()
            if not command:
                continue
            command = command[ 0 ]
            if command in self.commands.values() and self.IsNotReplied( comment ):
                printLog( "Found comment with command..." )
                if self.commands[ "video" ] == command:
                    self.ReplyVideo( comment )
                elif self.commands[ "live" ] == command:
                    self.ReplyLive( comment )
        printLog( "All comments checked..." )
