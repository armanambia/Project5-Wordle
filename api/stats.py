import collections
import contextlib
import sqlite3
import uuid
import typing
from datetime import date
from collections import OrderedDict

from fastapi import FastAPI, Depends, Response, HTTPException, status
from pydantic import BaseModel, BaseSettings


class Settings(BaseSettings):
    stats_database: str
    games_1_database: str
    games_2_database: str
    games_3_database: str
    users_database: str
    logging_config: str

    class Config:
        env_file = ".env"

class User(BaseModel):
    # user id can be fetched or provided depending on if the user knows their id
    user_id: int = None
    username: str

class Game(BaseModel):
    user_id: int
    game_id: int
    guesses: int
    won: bool

class Stats(BaseModel):
    username: str
    game_id: int
    guesses: int
    won: bool

def get_db():
    #db dependency yields a connection to all tables store in a list
    with contextlib.closing(sqlite3.connect(settings.games_1_database)) as db1:
        db1.row_factory = sqlite3.Row
        with contextlib.closing(sqlite3.connect(settings.games_2_database)) as db2:
            db2.row_factory = sqlite3.Row
            with contextlib.closing(sqlite3.connect(settings.games_3_database)) as db3:
                db3.row_factory = sqlite3.Row
                with contextlib.closing(sqlite3.connect(settings.users_database)) as users:
                    users.row_factory = sqlite3.Row
                    yield [db1, db2, db3, users]

#     Alt logic for db dependancy
# def get_db(shard: int = int(User.guid) % 3):
#     let shard_conn = ""
#     if shard == 0:
#         shard_conn = settings.games_1_database
#     if shard == 1:
#         shard_conn = settings.games_2_database
#     if shard == 2:
#         shard_conn = settings.games_3_database

settings = Settings()
app = FastAPI()
sqlite3.register_converter('GUID', lambda b: uuid.UUID(bytes_le=b))
sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)

# games_conn = [
#     sqlite3.connect(settings.games_1_database, detect_types=sqlite3.PARSE_DECLTYPES),
#     sqlite3.connect(settings.games_2_database, detect_types=sqlite3.PARSE_DECLTYPES),
#     sqlite3.connect(settings.games_3_database, detect_types=sqlite3.PARSE_DECLTYPES)
# ]

@app.post("/finish/", status_code=status.HTTP_200_OK)
def process_end(
    stats: Stats, response: Response, db: list() = Depends(get_db)
):
    today = date.today().strftime("%Y-%m-%d")
    username = stats.username
    
    try:
        cur = db[3].cursor()
        cur.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        guid = cur.fetchall()[0][0]
        db[3].commit()
    except Exception as e:
        return {"msg": "Error: Failed to reach users. " + str(e)}
    
    try:
        # Get user_id from username --> get shard with user_id
        cur = db[3].cursor()
        cur.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        u_id = cur.fetchall()[0][0]
        shard = int(uuid.UUID(bytes_le=u_id)) % 3
    except Exception as e:
        return {"msg": "Error: Failed to identify shard. " + str(e)}

    try:
        cur = db[shard].cursor()
        cur.execute("SELECT * FROM games WHERE user_id = ? AND game_id = ?", (guid, stats.game_id))
        db[shard].commit()
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"msg": "Error: Failed to reach games shard. " + str(e)}
    
    rows = cur.fetchall()
    if len(rows) != 0:
        return {"msg": "Game Already Finished"}
    
    try:
        cur = db[shard].cursor()
        cur.execute(
            """
            INSERT INTO games VALUES(?, ?, ?, ?, ?)
            """
            , (guid, stats.game_id, today, stats.guesses, stats.won))
        
        # Refreshing views
        try:
            # Add wins views to shard
            cur.execute('DROP VIEW IF EXISTS wins')
            cur.execute('''
                CREATE VIEW wins
                AS
                    SELECT
                        user_id,
                        COUNT(won)
                    FROM
                        games
                    WHERE
                        won = TRUE
                    GROUP BY
                        user_id
                    ORDER BY
                        COUNT(won) DESC
                ''')
            db[shard].commit()
        except Exception as e:
            print("Error: Failed to create wins view. " + str(e))
        
        try:
            # Add streaks view to shard
            cur = db[shard].cursor()
            cur.execute('DROP VIEW IF EXISTS streaks')
            cur.execute('''
                CREATE VIEW streaks
                AS
                    WITH ranks AS (
                        SELECT DISTINCT
                            user_id,
                            finished,
                            RANK() OVER(PARTITION BY user_id ORDER BY finished) AS rank
                        FROM
                            games
                        WHERE
                            won = TRUE
                        ORDER BY
                            user_id,
                            finished
                    ),
                    groups AS (
                        SELECT
                            user_id,
                            finished,
                            rank,
                            DATE(finished, '-' || rank || ' DAYS') AS base_date
                        FROM
                            ranks
                    )
                    SELECT
                        user_id,
                        COUNT(*) AS streak,
                        MIN(finished) AS beginning,
                        MAX(finished) AS ending
                    FROM
                        groups
                    GROUP BY
                        user_id, base_date
                    HAVING
                        streak > 1
                    ORDER BY
                        user_id,
                        finished
                ''')
            db[shard].commit()
        except Exception as e:
            print("Error: Failed to create streaks view. " + str(e))
        
        return {"msg": "Successfully Posted Win"} if stats.won else {"msg": "Successfully Posted Loss"}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"msg": "Error: Failed to insert into database. " + str(e)}

    return {"msg": "Failed to Post Win/Loss"}

@app.get("/stats/", status_code=status.HTTP_200_OK)
def fetch_stats(
    user: User, response: Response, db: list() = Depends(get_db)
):
    today = date.today().strftime("%Y-%m-%d")
    cur_name = user.username
    cur_id = user.user_id

    if not cur_id:
        try:
            cur = db[3].cursor()
            cur.execute("SELECT user_id FROM users WHERE username = ?", (cur_name,))
            cur_id = cur.fetchall()[0][0]
        except Exception as e:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"msg": "Error: Failed to reach users table. " + str(e)}
    
    try:
        shard = int(uuid.UUID(bytes_le=cur_id)) % 3
    except Exception as e:
        return {"msg": "Error: Failed to identify shard. " + str(e)}

    result = OrderedDict()
    try:
        cur = db[shard].cursor()
        cur.execute("SELECT MAX(streak) FROM streaks WHERE user_id = ?", (cur_id,))
        maxStreak = cur.fetchall()[0][0]
        
        # for current streak, we need to check if there is an existing streak
        # where the finished date is equal to today's date
        cur.execute("SELECT streak FROM streaks WHERE user_id = ? AND ending = ?", (cur_id, today))
        
        curStreak = cur.fetchall()
        curStreak = curStreak[0][0] if len(curStreak) != 0 else 0
        
        cur.execute("SELECT COUNT(game_id) FROM games WHERE user_id = ?", (cur_id,))
        games_played = cur.fetchall()[0][0]
        
        cur.execute("SELECT [COUNT(won)] FROM wins WHERE user_id = ?", (cur_id,))
        games_won = cur.fetchall()[0][0]
        
        cur.execute("SELECT AVG(guesses) FROM games WHERE user_id = ?", (cur_id,))
        avg_guess = cur.fetchall()[0][0]

        cur.execute("SELECT guesses, COUNT(game_id) FROM games WHERE user_id = ? GROUP BY guesses", (cur_id,))
        temp = cur.fetchall()

        # stores list of tuples such as [(1, 3), (2, 5)...]
        guess_distribution = []
        for guess in range(1,7):
            try:
                guess_distribution.append((guess, temp[guess-1][1]))
            except:
                guess_distribution.append((guess, 0))
        db[shard].commit()
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"msg": "Error: Failed to load data. " + str(e)}
    
    result["currentStreak"] = curStreak
    result["maxStreak"] = maxStreak
    tempDict = OrderedDict()
    for item in guess_distribution:
        tempDict[f"{item[0]}"] = item[1] 
    result["guesses"] = tempDict
    result["winPercentage"] = round(games_won/games_played * 100)
    result["gamesPlayed"] = games_played
    result["gamesWon"] = games_won
    result["averageGuesses"] = round(avg_guess)
    return result

@app.get("/top_wins/", status_code=status.HTTP_200_OK)
def fetch_top_wins(
    response: Response, db: list() = Depends(get_db)
):
    result = OrderedDict()
    #Takes the the top 10 wins from each shard and appends it to a list
    top_table = []
    for shard in range(3):
        try: 
            cur = db[shard].cursor()
            cur.execute("SELECT * FROM wins LIMIT 10")
            vals = cur.fetchall()
            for row in vals:
                top_table.append(row)
        except Exception as e:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"msg": "Error: Failed to reach wins table. " + str(e)}

    #Sorts top 30 users from across shards and sorts them and returns the top 10
    top_table.sort(reverse=True, key=lambda row: row[1])
    top_table = top_table[0:10]
    user_ids = []
    for row in top_table:
        user_ids.append(row[0])
    usernames = []
    
    try: 
        for i in user_ids:
            cur = db[3].cursor()
            cur.execute("SELECT username FROM users WHERE user_id = ?", (i,))
            name = cur.fetchall()[0][0]
            usernames.append(name)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"msg": "Error: Failed to reach users table. " + str(e)}
    
    users = []
    for i in range(10):
        temp = OrderedDict()
        temp["username"] = usernames[i]
        temp["user_id"] = uuid.UUID(bytes_le=user_ids[i])
        users.append(temp)
    result["Users"] = users

    return result

@app.get("/longest_streak/", status_code=status.HTTP_200_OK)
def fetch_longest_streaks(
    response: Response, db: list() = Depends(get_db)
):
    result = OrderedDict()
    top_table = []
    for shard in range(3):
        try: 
            cur = db[shard].cursor()
            cur.execute("SELECT user_id, streak FROM streaks ORDER BY streak DESC LIMIT 10")
            vals = cur.fetchall()
            for row in vals:
                top_table.append(row)
        except Exception as e:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"msg": "Error: Failed to reach wins table. " + str(e)}
    
    top_table.sort(reverse=True, key=lambda row: row[1])
    top_table = top_table[0:10]
    user_ids = []
    for row in top_table:
        user_ids.append(row[0])
    usernames =[]
    
    try: 
        for i in user_ids:
            cur = db[3].cursor()
            cur.execute("SELECT username FROM users WHERE user_id = ?", (i,))
            usernames.append(cur.fetchall()[0][0])
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"msg": "Error: Failed to reach users table. " + str(e)}
    
    users = []
    for i in range(10):
        temp = OrderedDict()
        temp["username"] = usernames[i]
        temp["user_id"] = uuid.UUID(bytes_le=user_ids[i])
        users.append(temp)
    result["Users"] = users

    return result