#!/bin/bash
# get result from curl

HOST=${LISTEN:-localhost}

result=$(curl -sS -X GET http://${HOST}/health_check)

echo $result

if [[ $result == '{"status": "OK"}' ]]
then
    exit 0
else:
    exit 1
fi
