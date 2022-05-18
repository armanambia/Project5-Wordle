#!/usr/bin/env python3
import collections
import contextlib
import sqlite3
import typing
import uuid
import typing

from datetime import datetime

from fastapi import FastAPI, Depends, Response, HTTPException, status
from pydantic import BaseModel, BaseSettings
from collections import OrderedDict

import redis
r = redis.Redis()

class Settings(BaseSettings):
    games_1_database: str
    games_2_database: str
    games_3_database: str
    users_database: str
    logging_config: str
    epoch: str
    max_words: int
    class Config:
        env_file = ".env"


class UserStart(BaseModel):
    username: str

class GameStart(BaseModel):
    user_id: str
    game_id: int


class GameGuess(BaseModel):
    user_id: str
    game_id: int
    guess: str

def dayIndex():
    epoch = datetime.strptime(settings.epoch, "%Y-%m-%d")
    diff_days = (datetime.now() - epoch).days
    return diff_days % settings.max_words

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

settings = Settings()
app = FastAPI()
@app.put("/start/", status_code=status.HTTP_200_OK)
def check(s: UserStart, response: Response, db: sqlite3.Connection = Depends(get_db)):
    
    res = OrderedDict()
    print("inside start")
    try:
        cur = db[3].cursor()
        cur.execute("SELECT user_id FROM users WHERE username = ?", (s.username,))
        try:
            guid = cur.fetchall()[0][0]
        except Exception as e:
            res['status'] = "No user_id found"
            return res
        db[3].commit()
    except Exception as e:
        return {"msg": "Error: Failed to reach users. " + str(e)}
    
    shard = int(uuid.UUID(bytes_le=guid)) % 3
    game_id = dayIndex()


    try:
        cur = db[shard].cursor()
        cur.execute("SELECT * FROM games WHERE user_id = ? AND game_id = ?", (guid, game_id))
        games = cur.fetchall()
        db[shard].commit()
    except Exception as e:
        return {"msg": "Error: Failed to reach game. " + str(e)}
    
    print(f"{guid},{game_id}")
    val = r.hgetall(f"{guid},{game_id}")
    print(val)
    start = 0
    start_val = 0
    for k,v in val.items():
        start = k
        start_val = v
        print(start)
        print(start_val)
        print(start_val.decode("utf-8"))
        break

    # the game of the day is over
    if len(games) != 0:
        if games[0][4] == 1:
            res['status'] = "won"
        else:
            res['status'] = "lost"
        res["user_id"] = str(uuid.UUID(bytes_le=guid))
        res["game_id"] = game_id
    # game is in progress
    elif len(val) > 0 and start_val.decode("utf-8") != '':
        res['status'] = "in-progress"
        res["user_id"] = str(uuid.UUID(bytes_le=guid))
        res["game_id"] = game_id
        res["guesses"] = val
    # new game
    else:
        guesses = {1:'',2:'',3:'',4:'',5:'',6:''}
        r.hmset(f"{guid},{game_id}", guesses)
        res['status'] = "new"
        res["user_id"] = str(uuid.UUID(bytes_le=guid))
        res["game_id"] = game_id
    
    return res

@app.put("/make_guess/", status_code=status.HTTP_200_OK)
def make_guess(s: GameGuess, response: Response, db: sqlite3.Connection = Depends(get_db)):
    try:
        guid = uuid.UUID(s.user_id).bytes_le
    except:
        return {"msg": "Error: Invalid GUID " }
    print(type(guid), guid)
    shard = int(uuid.UUID(bytes_le=guid)) % 3
        
    try:
        cur = db[3].cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (guid,))
        val = cur.fetchall()
    except:
        return {"msg": "Error: Failed to reach users. " + str(e)}

    if len(val) ==0:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return  {"msg": "Error: User does not exist " }
    
    val = r.hgetall(f"{guid},{s.game_id}")
    if len(val) == 0:
        return {"msg": "Error: Game does not exist. "}

    for k,v in val.items():
        if len(v) == 0:
            val[k] = s.guess
            r.hmset(f"{guid},{s.game_id}", val)
            return {"msg": "Success: Guess has been inserted"}
    
    return {"msg": "Error: Only 6 guesses are allowed"}

@app.post("/get_game/", status_code=status.HTTP_200_OK)
def get_game(s: GameStart, response: Response, db: sqlite3.Connection = Depends(get_db)):
    # try:
    #     cur = db[3].cursor()
    #     cur.execute("SELECT user_id FROM users WHERE og_id = ?", (s.og_id,))
    #     guid = cur.fetchall()[0][0]
    #     print("1", type(guid), guid)

    #     val = uuid.UUID(bytes_le=guid)
    #     print("2", type(val), val)
        
    #     val = str(uuid.UUID(bytes_le=guid))
    #     print("3", type(val), val)
        
    #     val = uuid.UUID(val)
    #     print("4", type(val), val)
        
    #     val = val.bytes_le
    #     print("5", type(val), val)

    #     db[3].commit()
    # except Exception as e:
    #     return {"msg": "Error: Failed to reach users. " + str(e)}
    result = OrderedDict()
    try:
        guid = uuid.UUID(s.user_id).bytes_le
    except:
        result['status'] = "Invalid user_id"
        return result
    print(type(guid), guid)
    shard = int(uuid.UUID(bytes_le=guid)) % 3
    
    

    try:
        cur = db[3].cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (guid,))
        val = cur.fetchall()
    except:
        result['status'] = "Failed to reach users"
        return result

    if len(val) ==0:
        response.status_code = status.HTTP_400_BAD_REQUEST
        result['status'] = "Invalid user_id"
        return result

    val = r.hgetall(f"{guid},{s.game_id}")
    if len(val) == 0:
        response.status_code = status.HTTP_400_BAD_REQUEST
        result['status'] = "Invalid game_iD"
        return result
    
    guesses = OrderedDict()

    guess_count = 0
    for k,v in val.items():
        guess_num = int(k.decode("utf-8"))
        if len(v) != 0:
            guess_count += 1
            guesses[guess_num] = v.decode("utf-8")
        else:
           break
    result['status'] = "Valid"
    result["current guesses"] = guesses
    result["remaining guesses"] = 6 - guess_count
    return result

    
