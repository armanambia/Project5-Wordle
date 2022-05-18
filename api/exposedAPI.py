import collections
import contextlib
import sqlite3
import typing
import uuid
import typing
import httpx
from datetime import datetime

from fastapi import FastAPI, Depends, Response, HTTPException, status
from pydantic import BaseModel, BaseSettings
from collections import OrderedDict

class User(BaseModel):
    username: str

class Game(BaseModel):
    user_id: str
    guess: str


app = FastAPI()

@app.post("/game/new/", status_code=status.HTTP_200_OK)
def new_game(s: User, response: Response):
    res = OrderedDict()
    # r = httpx.post('https://httpbin.org/post', data={'key': 'value'})
    r = httpx.put('http://127.0.0.1:9999/start/', json={'username': s.username})
    start_resp = r.json()
    res.update(start_resp)
    if 'new' in start_resp["status"]:
        return start_resp
    elif 'progress' in start_resp["status"]:
        # handle the guesses and create a list of only the valid guesses
        guesses = res["guesses"]
        print(type(guesses), guesses)
        valid_guesses = []
        for i,g in guesses.items():
            if g != '':
                valid_guesses.append(g)
            else:
                break
        res['remaining'] = 6 - len(valid_guesses)
        res['guesses'] = valid_guesses
        
        # call the /check endpoint to get the word of the day
        r = httpx.put('http://127.0.0.1:9999/check/', json={'word': 'place'})
        print(r.json())
        correct_word = r.json()['word_of_the_day']
        # create freq map of today's word
        freq_map = {}
        for c in correct_word:
            freq_map[c] = freq_map.get(c, 0) + 1
        print(freq_map)

        # make the correct and present lists using dictionary and map logic
        correct_map = {}
        guess_map = {}
        for guess in valid_guesses:
            r = httpx.put('http://127.0.0.1:9999/check/', json={'word': guess})
            curWord = r.json()
            result = curWord['results']
            guess_map[guess] = result
            for i, l in enumerate(guess):
                if result[i] == 2:
                    if not i in correct_map:
                        correct_map[i] = l
                        freq_map[l] -= 1
        correct = list(correct_map.values())
        present = []
        for g,ans in guess_map.items():
            for i, l in enumerate(g):
                if ans[i] == 1:
                    present.append(l)
                    freq_map[l] -= 1
        
        res['letters'] = {'correct': correct, 'present' : present}
    return res


@app.post("/game/{game_id}/", status_code=status.HTTP_200_OK)
def game_id(game_id: int, g: Game, response: Response):
    res = OrderedDict()

    r = httpx.put('http://127.0.0.1:9999/validate/', json={'word': g.guess})
    valid_resp = r.json()
    if valid_resp['status'] == "Invalid":
        return valid_resp
    
    r = httpx.put('http://127.0.0.1:9999/make_guess/', json={'user_id': g.user_id, 'game_id': game_id, 'guess': g.guess})
    guess_resp = r.json()
    res['status'] = guess_resp['msg']
    if "Success" not in guess_resp['msg']:
        return res
    
    r = httpx.post('http://127.0.0.1:9999/get_game/', json={'user_id': g.user_id, 'game_id': game_id})
    get_resp = r.json()
    res['status'] = guess_resp['msg']
    if get_resp['status'] != "Valid":
        return res
    
    r = httpx.put('http://127.0.0.1:9999/check/', json={'word': g.guess})
    check_resp = r.json()
    correct_word = check_resp['word_of_the_day']
    result = check_resp['results']
    # game is a win
    if g.guess == correct_word:
        win = 1
        res['status'] = 'win'
    # game is lost
    elif get_resp['remaining guesses'] == 0:
        res['status'] = 'loss'
        win = 0
    # game not over
    else:
        res['status'] = "incorrect"
        res['remaining'] = get_resp['remaining guesses'] 
        correct= []
        present = []
        for i in range (5):
            if result[i] == 2:
                correct.append(g.guess[i])
            elif result[i] == 1:
                present.append(g.guess[i])
        res['letters'] = {'correct': correct, 'present': present}
        return res

    res['remaining'] = get_resp['remaining guesses'] 
    guesses_made = 6 - res['remaining']
    r = httpx.post('http://127.0.0.1:9999/finish/', json={'user_id': g.user_id, 'game_id': game_id, 'guesses': guesses_made, 'won': win})
    r = httpx.post('http://127.0.0.1:9999/stats/', json={'user_id': g.user_id})
    res.update(r.json())
    return res