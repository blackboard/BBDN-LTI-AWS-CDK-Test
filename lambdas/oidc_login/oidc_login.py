import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
import json
import logging
import os
from pprint import pformat
import uuid


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

def cache_value(key,value,nonce,ip):
    logger.debug(f"oidc_login->cache_value: key={key}")
    logger.debug(f"oidc_login->cache_value: value={value}")
    logger.debug(f"oidc_login->cache_value: nonce={nonce}")
    logger.debug(f"oidc_login->cache_value: ip={ip}")
    logger.debug(f"oidc_login->cache_value: value['client_id']={value['client_id']}")
    logger.debug(f"oidc_login->cache_value: value['lti_deployment_id']={value['lti_deployment_id']}")
    logger.debug(f"oidc_login->cache_value: value['iss']={value['iss']}")
    logger.debug(f"oidc_login->cache_value: value['lti_message_hint']={value['lti_message_hint']}")
    
    try:
        response = cache.put_item(
            Item={
                'key': str(key),
                'client_id': str(value['client_id']),
                'lti_deployment_id': str(value['lti_deployment_id']),
                'iss': str(value['iss']),
                'launch_id' : str(nonce),
                'lti_message_hint': str(value['lti_message_hint']),
                'ip': str(ip)
            }
        )
        logger.info(f"{value} successfully cached as {key}")
    except Exception as e:
        logger.error(f"Error caching {value} as {key} - {e}")

def get_config(login_params):

    config = {}
    
    try:
        results = table.query(KeyConditionExpression=Key("deployment_id").eq(login_params['lti_deployment_id']))

        item = results['Items'][0]
        
        config['deployment_id'] = item['deployment_id']
        config['client_id'] = item['client_id']
        config['iss'] = item['issuer']
        config['auth_login_url'] = item['auth_login_url']
        config['auth_token_url'] = item['auth_token_url']        
        
        logger.debug(f"OIDCLogin->get_config: config=" + pformat(config))
        
        return config
    except Exception as e:
        logger.error(f"OIDCLogin->get_config: Error getting configuration - {e}")
        return None

    return 

def validate_deployment(login_params, config):
    
    if login_params['lti_deployment_id'] == config['deployment_id'] and login_params['client_id'] == config['client_id'] and login_params['iss'] == config['iss']:
        return True
    else:
        return False
    

def build_url(login_params,config,state,nonce):
    
    oidcparams = f"?scope=openid"
    oidcparams += f"&response_type=id_token"
    oidcparams += f"&response_mode=form_post"
    oidcparams += f"&prompt=none"
    oidcparams += f"&client_id={login_params['client_id']}"
    oidcparams += f"&redirect_uri={login_params['target_link_uri']}"
    oidcparams += f"&state={state}"
    oidcparams += f"&nonce={nonce}"
    oidcparams += f"&login_hint={login_params['login_hint']}"

    if "lti_message_hint" in login_params:
        oidcparams += f"&lti_message_hint={login_params['lti_message_hint']}"
    
    return f"{config['auth_login_url']}{oidcparams}"
    

def lambda_handler(event, context):
    logger.debug(f"OIDCLogin->lambda_handler: Event: " + pformat(event))
    logger.debug(f"OIDCLogin->lambda_handler: Context: " + pformat(context))
    
    login_params = event['queryStringParameters']
    
    logger.debug(f"oidc_login->lambda_handler: login_params={login_params}")
    
    config = get_config(login_params)
    
    logger.debug(f"oidc_login->lambda_handler: config={config}")
    
    if config is not None and validate_deployment(login_params,config):
        
        logger.debug(f"oidc_login->lambda_handler: set state")

        state = uuid.uuid4()
        nonce = uuid.uuid4().hex
        
        logger.debug(f"oidc_login->lambda_handler: nonce={nonce}")
        
        location = build_url(login_params,config,state,nonce)
        
        logger.debug(f"oidc_login->lambda_handler: location={location}")

        cache_value(state,login_params,nonce,event['requestContext']['http']['sourceIp'])
        
        logger.debug(f"oidc_login->lambda_handler: return")
    
        return {
            'statusCode' : 302,
            "headers": {
                "Location": location
            }
        }
    else:
        
        message = f"Invalid deployment ID, client ID, or issuer"
    
        return {
            'statusCode' : 400,
            'body' : json.dumps(message),
            "headers": {
                "Content-Type": "application/json"
            }
        }