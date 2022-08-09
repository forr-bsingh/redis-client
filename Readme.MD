Usage for redis-client.py

Commands : 
- HELP: `python redis-client.py --help`
- RUN: `python redis-client.py --env <env> --key <pattern> --display true --delete true`
- Example with display & delete: `py redis-client.py -e dev --key res* --display true --delete true`
- Example with display only : `py redis-client.py -e dev --key res* --display true`
- Example with delete without display : `py redis-client.py -e dev --key res* --delete true`
