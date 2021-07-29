#!/usr/bin/env python3
from aws_cdk import (
    core as cdk, 
    aws_lambda as _lambda, 
    aws_apigateway as _apigw, 
    aws_apigatewayv2 as _apigw2, 
    aws_apigatewayv2_integrations as _a2int,
    aws_apigatewayv2_authorizers as _a2auth,
    aws_dynamodb as _dynamo,
    custom_resources as _resources,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_s3_assets as s3assets,
    aws_route53 as route53,
    aws_route53_targets as alias,
    aws_certificatemanager as acm,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_lambda_event_sources as ales,
    aws_ec2 as ec2,
    aws_elasticache as cache,
    aws_lambda_python as lambpy,
    aws_kms as kms,
    aws_secretsmanager as secretsmanager,
    aws_ecs as ecs,
    aws_logs as logs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2
)

import json

from Config import r53

class Lti13Stack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        
        super().__init__(scope, construct_id, **kwargs)

        log_level = "DEBUG"
        
        lti_config_table = _dynamo.Table(
            self, id="ltiConfigTable",
            table_name="ltiConfigTable",
            partition_key=_dynamo.Attribute(name="deployment_id", type=_dynamo.AttributeType.STRING),
            removal_policy=cdk.RemovalPolicy.DESTROY,
            encryption=_dynamo.TableEncryption.AWS_MANAGED
        )

        lti_cache_table = _dynamo.Table(
            self, id="ltiCacheTable",
            table_name="ltiCacheTable",
            partition_key=_dynamo.Attribute(name="key", type=_dynamo.AttributeType.STRING),
            removal_policy=cdk.RemovalPolicy.DESTROY,
            encryption=_dynamo.TableEncryption.AWS_MANAGED
        )

        # Set up the custom resource policy so we can populate the database upon creation
        policy = _resources.AwsCustomResourcePolicy.from_sdk_calls(
            resources=['*']
        )

        # Get the data to be added to the new table
        data = self.get_initial_data()

        # Create and execute custom resources to add data to the new table
        for i in range(0,len(data)):
            lti_config = _resources.AwsCustomResource (
                self, 'initDBResource' + str(i), 
                policy=policy,
                on_create=_resources.AwsSdkCall(
                    service='DynamoDB',
                    action='putItem',
                    parameters={ 'TableName': lti_config_table.table_name, 'Item': data[i] },
                    physical_resource_id=_resources.PhysicalResourceId.of('initDBData' + str(i)),
                ),
            )
        
        jwt_lambda_layer = lambpy.PythonLayerVersion(
            self, 'JwtLambdaLayer',
            entry='jwt',
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_8],
            description='JWT Library',
            layer_version_name='JWTLambdaLayer'
        )

        oidc_login_lambda = lambpy.PythonFunction(
            self, "OIDCLambda",
            entry="lambdas/oidc_login",
            index="oidc_login.py",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="lambda_handler",
            timeout=cdk.Duration.seconds(10),
            environment = {
                'TABLE_NAME': lti_config_table.table_name,
                'CACHE_NAME': lti_cache_table.table_name,
                'LOG_LEVEL' : log_level
            },
        )

        lti_validation_lambda =  lambpy.PythonFunction(
            self, "LTIValidationLambda",
            entry="lambdas/lti_validation",
            index="lti_validation.py",
            runtime=_lambda.Runtime.PYTHON_3_8,
            layers=[jwt_lambda_layer],
            handler="lambda_handler",
            timeout=cdk.Duration.seconds(10),
            environment = {
                'TABLE_NAME': lti_config_table.table_name,
                'CACHE_NAME': lti_cache_table.table_name,
                'LOG_LEVEL' : log_level
            }
        )

        lti_config_table.grant_read_data(oidc_login_lambda)
        lti_config_table.grant_read_data(lti_validation_lambda)

        lti_cache_table.grant_full_access(oidc_login_lambda)
        lti_cache_table.grant_full_access(lti_validation_lambda)

        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self, 'BbDevConZone',
            hosted_zone_id=r53['LTI_TOOL_HOSTED_ZONE'],
            zone_name=r53['LTI_TOOL_DOMAIN_NAME']
        )

        domain_name = f"lti.{r53['LTI_TOOL_DOMAIN_NAME']}"

        devcon_certificate = acm.Certificate(self, "DevConCertificate",
            domain_name=domain_name,
            validation=acm.CertificateValidation.from_dns(hosted_zone)
        )

        bbdevcon_domain = _apigw2.DomainName (
            self,'RegDomain',
            certificate=devcon_certificate,
            domain_name=domain_name
        )

        lti_api_arecord = route53.ARecord(
            self, "AliasRecord",
            zone=hosted_zone,
            record_name="lti",
            target=route53.RecordTarget.from_alias(
                alias.ApiGatewayv2DomainProperties(bbdevcon_domain.regional_domain_name,bbdevcon_domain.regional_hosted_zone_id)
            )
        )

        # Set up proxy integrations
        oidc_login_integration = _a2int.LambdaProxyIntegration(
            handler=oidc_login_lambda,
        )

        lti_validation_integration = _a2int.LambdaProxyIntegration(
            handler=lti_validation_lambda,
        )

        # Define API Gateway and HTTP API
        lti_api = _apigw2.HttpApi(
            self, 'LTIGateway',
            default_domain_mapping={
                "domain_name": bbdevcon_domain
            }
        )

        cdk.CfnOutput(self, "API Endpoint", value=lti_api.api_endpoint)
        cdk.CfnOutput(self, "Default Stage", value=str(lti_api.default_stage.to_string()))
        cdk.CfnOutput(self, "URL", value=lti_api.url)

        post_oidc_login_route = _apigw2.HttpRoute(
            self, "PostOIDCLoginRoute",
            http_api=lti_api,
            route_key=_apigw2.HttpRouteKey.with_('/login', _apigw2.HttpMethod.POST),
            integration=oidc_login_integration
        )

        get_oidc_login_route = _apigw2.HttpRoute(
            self, "GetOIDCLoginRoute",
            http_api=lti_api,
            route_key=_apigw2.HttpRouteKey.with_('/login', _apigw2.HttpMethod.GET),
            integration=oidc_login_integration
        )

        lti_tool_validation_route = _apigw2.HttpRoute(
            self, "LTIToolValidationRoute",
            http_api=lti_api,
            route_key=_apigw2.HttpRouteKey.with_('/launch', _apigw2.HttpMethod.POST),
            integration=lti_validation_integration
        )

        cdk.CfnOutput(self, "GET OIDC Login Endpoint: ", value=get_oidc_login_route.path)
        cdk.CfnOutput(self, "POST OIDC Login Endpoint: ", value=post_oidc_login_route.path)
        cdk.CfnOutput(self, "LTI Launch Endpoint: ", value=lti_tool_validation_route.path)
    
    def get_initial_data(self):

        with open('lti.json') as json_file:
            dataset = json.load(json_file)
            
            data = []

            for deployment in dataset['deployments']:
                data.append({
                    'deployment_id': { 'S': deployment['deployment_id'] },
                    'client_id': { 'S': deployment['client_id'] },
                    'issuer': { 'S': deployment['issuer'] },
                    'auth_login_url': { 'S': deployment['auth_login_url'] },
                    'auth_token_url': { 'S': deployment['auth_token_url'] },
                    'key_set_url': { 'S': deployment['key_set_url'] },
                    'default': { 'BOOL': deployment['default'] }
                })
        
        return data