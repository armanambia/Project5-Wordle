#!/bin/sh

curl -X POST -H 'Content-Type: application/json' localhost:9999/get_game/ -d "{\"user_id\": \"$1\", \"game_id\": \"$2\"}"  | jq
