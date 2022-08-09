#!/usr/bin/env python3

# step 1: import the redis-py client package
from rediscluster import RedisCluster
import sys, getopt

servers = dict([('PROD',''), ('STAGE',''), ('TEST',''), ('DEV',''), ('LOCAL', 'localhost') ])
ports = dict([('PROD','6379'), ('STAGE','6379'), ('TEST','6379'), ('DEV','6379'), ('LOCAL', '6379') ])

# step 2: define our connection information for Redis
# Replaces with your configuration information

def print_usage():
    print ('Usage for redis cleanup client:')
    print ('    redis-client.py --env <env> --key <pattern> [--display true] [--delete true]')
    print('OR')
    print ('    redis-client.py -e <env> -k <pattern> [-d true] [-dl true]')

def read_input(argv):
    "Read parameter for env key patterns"
    display_keys = False
    delete_keys = False
    if len(argv) < 4 :
        print_usage()
        sys.exit(2)
    
    try:
        opts, args = getopt.getopt(argv,"e:k:d:",["env=","key=","display="])
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print_usage()
            sys.exit()
        elif opt in ("-e", "--env"):
            env = arg.upper()
        elif opt in ("-k", "--key"):
            if not arg.endswith("*"):
                print ("Key pattern must end with '*' for pattern search across redis cluster")
                sys.exit(2)
            key_pattern = arg
        elif opt in ("-d", "--display"):
            display_keys = arg == 'true'
        elif opt in ("-dl", "--delete"):
            delete_keys = arg == 'true'
    return env,key_pattern,display_keys,delete_keys

def find_connection(env):
    "Find connection details based on env"
    return servers[env],ports[env];    

def hello_redis(redis_host, redis_port):
    "Connect to redis at given host and port"
    return RedisCluster(host=redis_host, port=redis_port, password='', decode_responses=True)


def scan_keys(r, pattern):
    "Returns a list of all the keys matching a given pattern"
    
    try:
        return r.keys(pattern)
    except ValueError as error:
        print ("Exception while scanning keys, reason:", error)
    
    return []

def print_keys(result):
    "Print keys to standard display"
    
    print("Keys found with given pattern are : ", result)

def delete_keys(r, result):
    "Delete the given list of keys"
 
    for key in result:
        try:
            r.delete(key)
        except Exception as cause:
            print ("Delete failed for key:", key, " cause: ", cause)

if __name__ == '__main__':
    env,key_pattern,display_keys,delete_keys = read_input(sys.argv[1:])
    print('Setting up for', env)
    redis_host,redis_port = find_connection(env)
    print("Trying to connect to ", redis_host, ":", redis_port)
    r = hello_redis(redis_host, redis_port)
    print("Connected sucessfully ", redis_host, ":", redis_port)
    print("Looking for keys matching the pattern: ", key_pattern)
    result = scan_keys(r, key_pattern)
    print("Found ", len(result), " keys")
    if(display_keys == True):
        print_keys(result)
    if(delete_keys == True):
        print("Deletion in progress for ", len(result), " keys")
        delete_keys(r, result)