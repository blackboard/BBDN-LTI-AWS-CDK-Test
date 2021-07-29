import base64
import json
import jwt
#from jwt import PyJWKClient
import logging
import os
from pprint import pformat
from urllib import parse as urlparse
import urllib3

class lti_util:

    def __init__(self, logger, client_id, jwks_url):
        self.logger = logger
        self.client_id = client_id
        self.jwks_url = jwks_url

        self.http = urllib3.PoolManager()

    def decode_jwt_parts(self, part):
        self.logger.error(f"LTIValidation->decode_jwt_parts: part: {part}")
        s = str(part).strip()
        self.logger.error(f"LTIValidation->decode_jwt_parts: s: {s}")
        
        try:
            return base64.b64decode(s).decode('utf-8')
        except Exception:
            padding = len(s) % 4
            self.logger.error(f"LTIValidation->decode_jwt_parts: padding: {padding}")
            if padding == 1:
                self.logger.error(f"LTIValidation->decode_jwt_parts: Invalid base64 string: {s}")
                return ''
            elif padding == 2:
                self.logger.error(f"LTIValidation->decode_jwt_parts: padding equals 2: {s}")
                s += '=='
            elif padding == 3:
                self.logger.error(f"LTIValidation->decode_jwt_parts: padding equals 3: {s}")
                s += '='
            return base64.b64decode(s).decode('utf-8')
    
    def get_public_key(self,kid):
        
        r = self.http.request("GET", self.jwks_url)

        keys = json.loads(r.data)

        self.logger.debug(f"LTIValidation->get_public_key: keys" + pformat(keys))

        for key in keys['keys']:
            if key['kid'] == kid:
                return key
        
        return None
        
    def process_launch(self, id_token):
        self.logger.debug(f"LTIValidation->process_launch: id_token: {id_token}")

        jwt_parts = id_token.split(".")
        self.logger.debug(f"LTIValidation->process_launch: jwt_parts: {jwt_parts}")
        self.logger.debug(f"LTIValidation->process_launch: jwt_parts: {jwt_parts[0]}")
        self.logger.debug(f"LTIValidation->process_launch: jwt_parts: {jwt_parts[1]}")
        self.logger.debug(f"LTIValidation->process_launch: jwt_parts: {jwt_parts[2]}")

        jwt_header = json.loads(self.decode_jwt_parts(jwt_parts[0]))
        self.logger.debug(f"LTIValidation->process_launch: jwt_header: " + pformat(jwt_header))

        jwt_body = json.loads(self.decode_jwt_parts(jwt_parts[1]))
        self.logger.debug(f"LTIValidation->process_launch: jwt_body: " + pformat(jwt_body))

        aud = ""
        if isinstance(jwt_body['aud'], list):
            aud = jwt_body['aud'][0]
        else:
            aud = jwt_body['aud']

        self.logger.debug(f"LTIValidation->process_launch: aud: {aud}")
        self.logger.debug(f"LTIValidation->process_launch: client_id: {self.client_id}")
        
        if aud != self.client_id:
            return {
                'statusCode' : 401,
                'body' : 'Invalid client_id',
                "headers": {
                    "Content-Type": "text/plain"
                }
            }

        self.logger.debug(f"LTIValidation->process_launch: get public key: {jwt_header['kid']}")
        
        public_key = self.get_public_key(jwt_header['kid'])

        if public_key is None:
            return {
                'statusCode' : 401,
                'body' : 'Invalid client_id',
                "headers": {
                    "Content-Type": "text/plain"
                }
            }

        instance = jwt.JWT()
        
        verifying_key = jwt.jwk_from_dict(public_key)
        
        try:

            data = instance.decode(
                id_token, verifying_key, do_time_check=True
            )
        
            self.logger.debug(f"LTIValidation->process_launch: post_validation_data: {data}")

            return {
                'statusCode' : 200,
                'body' : pformat(json.dumps(data)),
                "headers": {
                    "Content-Type": "application/json"
                }
            }

        except Exception as e:
            self.logger.error(f"LTIValidation->process_launch: Exception: {e}")
            return {
                'statusCode' : 500,
                'body' : f"LTIValidation->process_launch: Exception: {e}",
                "headers": {
                    "Content-Type": "text/plain"
                }
            }
       
    
