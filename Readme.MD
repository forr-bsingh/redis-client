**Usage for redis-client.py**

***Commands*** : 
- HELP: `python redis-client.py --help`
- RUN: `python redis-client.py --env <env> --key <pattern> --display true --delete true`
- Example with display & delete: `py redis-client.py -e dev --key res* --display true --delete true`
- Example with display only : `py redis-client.py -e dev --key res* --display true`
- Example with delete without display : `py redis-client.py -e dev --key res* --delete true`

***Steps to setup the env:***

  1. Set up venv using the command 
  
  `python3 -m venv <path to virtual env>`
      
  `python3 -m venv ~/work/python/venv`

  2. Activate venv using the command
  
  `source <path to virtual env>/bin/activate` 
  
  `source ~/work/python/venv/bin/activate`

  3. Once in venv install the following dependencies:

     a. Upgrade PIP to latest version. 
     
     `pip install -U pip`

     b. Install redis-py-cluster. 
     
     `pip install redis-py-cluster`

     c. Upgrade setup tools. 
     
     `pip install -U setuptools wheel`
