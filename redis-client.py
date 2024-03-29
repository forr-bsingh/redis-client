#!/usr/bin/env python3

# step 1: import the redis-py client package
from rediscluster import RedisCluster
import sys, getopt

servers = dict([
    ('AWS_DEV',''),
    ('AWS_TEST',''),
    ('AWS_STAGE',''),
    ('AWS_PROD',''),
    ('PROD',''), 
    ('STAGE',''), 
    ('TEST',''), 
    ('DEV',''), 
    ('LOCAL', 'localhost')
    ])

""" servers = dict([
    ('AWS_DEV',''),
    ('AWS_TEST',''),
    ('AWS_STAGE',''),
    ('AWS_PROD',''),
    ('PROD',''), 
    ('STAGE',''), 
    ('TEST',''), 
    ('DEV',''), 
    ('LOCAL', 'localhost')
    ]) """

ports = dict([
    ('AWS_DEV','6379'),
    ('AWS_TEST','6379'),
    ('AWS_STAGE','6379'),
    ('AWS_PROD','6379'),
    ('PROD','6379'),
    ('STAGE','6379'), 
    ('TEST','6379'), 
    ('DEV','6379'), 
    ('LOCAL', '6379') 
    ])

# step 2: define our connection information for Redis
# Replaces with your configuration information

def print_usage():
    print ('Usage for redis cleanup client:')
    print ('    redis-client.py --env <env> --key <pattern> [--display true] [--delete true]')
    print('OR')
    print ('    redis-client.py -e <env> -k <pattern> [-d true] [-dl true]')

def read_input(argv):
    "Read parameter for env key patterns"
    display = False
    delete = False
    if len(argv) < 4 :
        print_usage()
        sys.exit(2)
    
    try:
        opts, args = getopt.getopt(argv,"e:k:d:",["env=","key=","display=","delete="])
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
            if not arg.__contains__("*"):
                print ("Key pattern must contain '*' for pattern match across redis cluster")
                sys.exit(2)
            key_pattern = arg
        elif opt in ("-d", "--display"):
            display = arg == 'true'
        elif opt in ("-dl", "--delete"):
            delete = arg == 'true'
    return env,key_pattern,display,delete

def find_connection(env):
    "Find connection details based on env"
    return servers[env],ports[env];    

def hello_redis(redis_host, redis_port):
    "Connect to redis at given host and port"
    return RedisCluster(host=redis_host, port=redis_port, password='', decode_responses=True, skip_full_coverage_check=True)


def scan_keys(r, pattern):
    "Returns a list of all the keys matching a given pattern"
    
    try:
        return r.keys(pattern)
    except ValueError as error:
        print ("Exception while scanning keys, reason:", error)
    
    return []

def print_keys(r, result):
    "Print keys to standard display"
    
    for key in result:
        try:
            print ("=============================[KEY: ", key, ", TYPE: ", r.type(key), ", TTL(ms): ", r.pttl(key), "]=============================")
            match r.type(key):
                case "string":
                    value = r.get(key)
                case "list":
                    value = r.lrange(key, 0, -1)
                case "set":
                    value = r.smembers(key)
                case "zset":
                    value = r.zrange(key, 0, -1, False, True)
                case "hash":
                    value = r.hgetall(key)
                case "stream":
                    value = ""
                case _:
                    value = ""
            print("VALUE: ", value)
        except Exception as cause:
            print("Could not fetch value for the key :", key, " cause: ", cause)
    print("Keys found with given pattern are : ", len(result))

def delete_keys(r, result):
    "Delete the given list of keys"
 
    print("Deletion in progress for ", len(result), " keys")
    for key in result:
        try:
            print("Deleting : ", key)
            r.delete(key)
        except Exception as cause:
            print ("Delete failed for key:", key, " cause: ", cause)

if __name__ == '__main__':
    env,key_pattern,display,delete = read_input(sys.argv[1:])
    print('Setting up for', env)
    redis_host,redis_port = find_connection(env)
    print("Trying to connect to ", redis_host, ":", redis_port)
    r = hello_redis(redis_host, redis_port)
    print("Connected sucessfully ", redis_host, ":", redis_port)
    print("Looking for keys matching the pattern: ", key_pattern)
    result = scan_keys(r, key_pattern)
    print("Found ", len(result), " keys")
    if(display == True):
        print_keys(r, result)
    if(delete == True):
        delete_keys(r, result)
