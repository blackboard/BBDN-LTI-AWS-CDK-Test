import base64
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
import json
import logging
import lti_util
import os
from pprint import pformat
from urllib import parse as urlparse


dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['TABLE_NAME']
table = dynamodb.Table(TABLE_NAME)

CACHE_NAME = os.environ['CACHE_NAME']
cache = dynamodb.Table(CACHE_NAME)

LOG_LEVEL = os.environ['LOG_LEVEL']
logger = logging.getLogger()

if LOG_LEVEL == "DEBUG":
    logger.setLevel(logging.DEBUG)
elif LOG_LEVEL == "ERROR":
    logger.setLevel(logging.ERROR)
elif LOG_LEVEL == "WARN":
    logger.setLevel(logging.WARN)
else:
    logger.setLevel(logging.INFO)

def get_body(event):
    return base64.b64decode(str(event['body'])).decode('ascii')

def get_config(login_params):

    config = {}
    
    try:
        results = table.query(KeyConditionExpression=Key("deployment_id").eq(login_params['lti_deployment_id']))

        item = results['Items'][0]
        
        config['deployment_id'] = item['deployment_id']
        config['client_id'] = item['client_id']
        config['iss'] = item['issuer']
        config['key_set_url'] = item['key_set_url']
        config['auth_token_url'] = item['auth_token_url']        
        
        logger.debug(f"LTIValidation->get_config: config=" + pformat(config))
        
        return config
    except Exception as e:
        logger.error(f"LTIValidation->get_config: Error getting configuration - {e}")
        return None

    return 

def delete_cache(key):
    cache.delete_item(
        Key={
            'key': key
        }
    )

def get_cache_data(state):
    try:
        results = cache.query(KeyConditionExpression=Key("key").eq(state))
        
        logger.debug(f"LTIValidation->get_cache_data: Results: " + pformat(results))
        logger.debug(f"Count: {results['Count']}")

        if results['Count'] > 0:
            item = results['Items'][0]

            logger.debug(f"LTIValidation->get_cache_data: Key: {state} Value: " + pformat(item))
            
            return item
        else:
            logger.error(f"LTIValidation->get_cache_data: invalid state parameter - {state}")
            return None
    except Exception as e:
        logger.error(f"LTIValidation->get_cache_data: Error getting cache - {e}")
        return None
    finally:
        delete_cache(state)

def lambda_handler(event, context):
    logger.debug(f"LTIValidation->lambda_handler: Event: " + pformat(event))
    logger.debug(f"LTIValidation->lambda_handler: Context: " + pformat(context))

    try:
        msg_map = dict(urlparse.parse_qsl(get_body(event)))
        logger.debug(str(msg_map))

        id_token = msg_map.get('id_token','err')
        state = msg_map.get('state','err')
        
        cache = get_cache_data(state)

        if not cache:
            retval={
                'statusCode' : 401,
                'body' : 'Invalid state parameter. You no hax0r!',
                "headers": {
                    "Content-Type": "text/plain"
                }
            }
            logger.error(str(retval))
            return retval
        elif cache['ip'] != event['requestContext']['http']['sourceIp']:
            retval={
                'statusCode' : 401,
                'body' : 'Wrong IP. You no hax0r!',
                "headers": {
                    "Content-Type": "text/plain"
                }
            }
            logger.error(str(retval))
            return retval

        config = get_config(cache)

        lti = lti_util.lti_util(logger,config['client_id'],config['key_set_url'])
        
        return_json = lti.process_launch(id_token)
        
        return return_json
        
    except Exception as e:
        return {
            'statusCode' : 500,
            'body' : str(e),
            "headers": {
                "Content-Type": "text/plain"
            }
        }