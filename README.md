# Wordle Clone

### Project 5 - Group 19 Created by
* Armanul Ambia
* Gaurav Joshi
* Steven Tran

### Project 4 Dependencies Created by
* Aaron Lieberman
* Armanul Ambia
* Iftekharul Islam
* Jacob Nguyen

## Installation

1. Clone the directory
```bash
git clone https://github.com/AaronLieb/WordleClone.git
```

2. Enter the repository directory
```bash
cd WordleClone
```

3. Install the required libraries and tools
```bash
sudo apt update
sudo apt install --yes python3-pip ruby-foreman sqlite3 httpie jq
python3 -m pip install 'fastapi[all]' sqlite-utils
sudo apt install --yes redis
sudo apt install --yes python3-hiredis
sudo apt-get install gnome-schedule
```
If `sudo apt-get install gnome-schedule` doesn't work try
```bash
sudo apt-get install cron
```

4. Go into the `api` directory
```bash
cd api
```

5. Run the initialization script
```bash
./bin/init.sh
```
This will download the wordle wordlists, parse them, create the database, and fill the database

6. Start all the microservices and the load balancer
```bash
./start.sh
```

7. To view the documentation of the endpoints, open the swagger docs

On the port for the microservice use the `/docs/` endpoint to check the available endpoints for that microservice

8. In a separate terminal, you can test the microservices using the scripts in the `bin/endpoint-tests/` directory
Most of the scripts use command line arguments to send words, here is an example of one being used

## Project 2 Endpoints

Check if a guess is a valid five-letter word:
```bash
./bin/endpoint-tests/put_validate.sh <word>
```

Check a guess against the word of the day:
```bash
./bin/endpoint-tests/put_check.sh <word>
```

Add a word to the valid words database:
```bash
./bin/endpoint-tests/post_word.sh <word>
```

Delete a word from the valid words database:
```bash
./bin/endpoint-tests/delete_word.sh <word>
```

Add a word to the answers database:
```bash
./bin/endpoint-tests/post_answer.sh <word>
```

Delete a word from the answers database:
```bash
./bin/endpoint-tests/delete_answer.sh <word>
```

Change the current word of the day to a custom word:
```bash
./bin/endpoint-tests/post_next_answer.sh <word>
```

Remove the custom word of the day and set it back to the original:
```bash
./bin/endpoint-tests/delete_next_answer.sh
```


## Project 3 Endpoints

Test posting win or loss:
```bash
./bin/endpoint-tests/post_win_loss.sh <username> <game_id> <guesses> <won>
```
In this script, 5 argument parameters are passed in, username: int, game_id: int, guesses: int, and won: bool (1 or 0)

Test getting stats:
```bash
./bin/endpoint-tests/get_stats.sh <user_name>
```

Test Getting Users with Most Wins:
```bash
./bin/endpoint-tests/get_top_wins.sh
```

Test Getting Users with Longest Streak:
```bash
./bin/endpoint-tests/get_longest_streak.sh
```


## Project 4 Endpoints

#### NOTE: og_id is the original user integer ID, NOT the user's UUID.

Start a new game for a specific user:
```bash
./bin/p4-endpoints/start_game.sh <og_id> <game_id>
```

Check the guesses made and the number of guess remaining for a specific game a specific user is playing:
```bash
./bin/p4-endpoints/get_game.sh <og_id> <game_id>
```

Make a guess on a specific game for a specific user:
```bash
./bin/p4-endpoints/make_guess.sh <og_id> <game_id> <word>
```


## Project 5 - Dependency Changes
1. change /start/ in redis_connect.py to take in a username and return the status, user_id, game_id. It will also return the guesses made if the game is in progress

2. change /get_game/ in redis_connect.py to take in a UUID as user_id instead of the old user_id, This method now returns a status for if the user_id is invalid, the game_id is invalid, or if both are valid. If both are valid, the endpoint still gives the current guesses and remainig guesses. Also change this endpoint to a POST so it can take in a body in httpx.

3. change /make_guess/ in redis_connect.py to take in a UUID as user_id instead of the old user_id

4. change /finish/ in stats.py to take in a UUID as user_id instead of the old user_id,

5. change /stats/ in stats.py to take in a UUID as user_id instead of the old user_id, Also change this endpoint to a post so it can take in a body in httpx.

## Project 5 - Endpoints
Start a new game for a specific user:
```bash
./bin/p5-endpoints/new_game.sh <user_name>
```

Run the game/{id} endpoint to play the game:
```bash
./bin/p5-endpoints/game_id.sh <game_id> <user_id> <guess>
```
