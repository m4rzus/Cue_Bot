import requests
import datetime


class SnookerAPI:

    def __init__( self ):
        self.main_url = "http://api.snooker.org/"
        self.date_format = "%Y-%m-%d"

    # ======================================================================== #

    def Request( self, url ):
        return requests.get( self.main_url + url, headers= { "X-Requested-By" : "RedditSnooker" } )

    # ======================================================================== #

    # Return json with player data or [] if given id not found
    def GetPlayer( self, id ):
        data = self.Request( "?p=" + str( id ) ).json()
        return data[ 0 ] if data else []

    # ======================================================================== #

    # Return list of currently played matches or [] if no matches are played
    # Format:
    #   ID1 - player1 id
    #   Player1 - name and surname
    #   Nationality1 - player1 nationality - if given id returns team, this should be used instead of Player1
    #   Score1 - player1's score
    #   ID2 - player2 id
    #   Player2 - name and surname
    #   Nationality2 - player2 nationality - if given id returns team, this should be used instead of Player2
    #   Score2 - player2's score
    #   worldsnooker - id to worldsnooker website
    #   StartTime - time the match started
    def GetLiveMatches( self ):
        data = []
        raw_data = self.Request( "?t=7" ).json()

        for raw_match in raw_data:
            match_data = {}

            # Get player1 data
            tmp = self.GetPlayer( raw_match[ "Player1ID" ] )
            match_data[ "Player1" ] = tmp[ "FirstName" ] + " " + tmp[ "LastName" ]
            match_data[ "ID1" ] = raw_match[ "Player1ID" ]
            match_data[ "Nationality1" ] = tmp[ "Nationality" ]
            match_data[ "Score1" ] = raw_match[ "Score1" ]
            # Get player2 data
            tmp = self.GetPlayer( raw_match[ "Player2ID" ] )
            match_data[ "Player2" ] = tmp[ "FirstName" ] + " " + tmp[ "LastName" ]
            match_data[ "ID2" ] = raw_match[ "Player2ID" ]
            match_data[ "Nationality2" ] = tmp[ "Nationality" ]
            match_data[ "Score2" ] = raw_match[ "Score2" ]

            match_data[ "worldsnooker" ] = raw_match[ "WorldSnookerID" ]
            match_data[ "StartTime" ] = raw_match[ "StartDate" ]
            # Add match to data list
            data.append( match_data )

        return data

    # ======================================================================== #

    # Return list of json data of events that are being played today or [] if no
    def GetEventsByDay( self, date ):
        data = []
        year = date.year

        raw_data = self.Request( "?t=5&s=" + str( year ) ).json()
        # Turn timestamp from string to datetime object
        first_match = datetime.datetime.strptime( raw_data[ 0 ][ "StartDate" ], self.date_format ).date()
        # First half of year, previous season haven't ended yet
        if ( date < first_match ):
            year -= 1
            raw_data = self.Request( "?t=5&s=" + str( year ) ).json()

        for event in raw_data:
            # Turn timestamps from string to datetime objects
            start = datetime.datetime.strptime( event[ "StartDate" ], self.date_format ).date()
            end = datetime.datetime.strptime( event[ "EndDate" ], self.date_format ).date()
            # if event is being played, append to list
            if date >= start and date <= end:
                data.append( event )
        return data

    # ======================================================================== #

    # Return event played today
    def GetCurrentEvents( self ):
        return self.GetEventsByDay( datetime.date.today() )

    # ======================================================================== #

    # Get info about upcoming event and number of days
    # Format:
    #   0: <number of days>
    #   1: <event json data>
    def GetNextEvent( self ):
        date = datetime.date.today()
        year = date.year - 1

        # Check previous season first
        raw_data = self.Request( "?t=5&s=" + str( year ) ).json()
        # Turn timestamp from string to datetime object
        start = datetime.datetime.strptime( raw_data[ -1 ][ "StartDate" ], self.date_format ).date()
        # Previous ended already, get raw_data from current
        if date > start:
            year += 1
            raw_data = self.Request( "?t=5&s=" + str( year ) ).json()

        for event in raw_data:
            # Turn timestamp from string to datetime object
            start = datetime.datetime.strptime( event[ "StartDate" ], self.date_format ).date()
            # Return number of days to event if next event found
            if date < start:
                return [ str( start - date ).split( " " )[ 0 ], event ]

    # ======================================================================== #

    def GetMatchesByEvent( self, id ):
        event = self.Request( "?e=" + str( id ) ).json()[ 0 ]
        data = self.Request( "?t=6&e=" + str( id ) ).json()
        for i in data:
            i[ "EventName" ] = event[ "Name" ]
            i[ "EventWorldSnookerID" ] = event[ "WorldSnookerId" ]
        return data

    # ======================================================================== #

    # Return sorted list of matches by Scheduled time of start or []
    def GetMatchesByDay( self, date ):
        events = self.GetEventsByDay( date )
        if events == []:
            return []
        data = []
        # Fetch matches for every event played today and add event name
        for event in events:
            tmp = self.GetMatchesByEvent( event[ "ID" ] )
            for i in tmp:
                i[ "EventName" ] = event[ "Name" ]
                i[ "EventWorldSnookerID" ] = event[ "WorldSnookerId" ]
            data += tmp
        # Delete all matches not played today
        data = [ x for x in data if str( date ) in x[ "ScheduledDate" ] ]

        # Sort if any matches found and return
        return sorted( data, key = lambda k : k[ "ScheduledDate" ] ) if data else []

    # ======================================================================== #

    def GetTodayMatches( self ):
        return self.GetMatchesByDay( datetime.date.today() )
