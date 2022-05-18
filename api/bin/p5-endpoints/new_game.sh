#!/bin/sh

curl -X POST -H 'Content-Type: application/json' localhost:9999/game/new/ -d "{\"username\": \"$1\"}"  | jq
