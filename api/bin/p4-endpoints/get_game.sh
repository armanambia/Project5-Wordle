#!/bin/sh

curl -X GET -H 'Content-Type: application/json' localhost:9999/get_game/ -d "{\"og_id\": \"$1\", \"game_id\": \"$2\"}"  | jq
