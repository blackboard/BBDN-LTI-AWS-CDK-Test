import setuptools

cdk_ver = "1.101.0"

with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="lti13_stack",
    version="0.0.1",

    description="LTI 1.3 Tool Blueprint",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "lti13_cdk"},
    packages=setuptools.find_packages(where="lti13_cdk"),

    install_requires=[
        f"aws-cdk.core=={cdk_ver}",
        f"aws-cdk.aws-ec2=={cdk_ver}",
        f"aws-cdk.aws-lambda=={cdk_ver}",
        f"aws-cdk.aws-apigateway=={cdk_ver}",
        f"aws-cdk.aws-apigatewayv2=={cdk_ver}",
        f"aws-cdk.aws-apigatewayv2-integrations=={cdk_ver}",
        f"aws-cdk.aws-apigatewayv2-authorizers=={cdk_ver}",
        f"aws-cdk.aws-dynamodb=={cdk_ver}",
        f"aws-cdk.aws-s3=={cdk_ver}",
        f"aws-cdk.aws-s3-deployment=={cdk_ver}",
        f"aws-cdk.aws-s3-assets=={cdk_ver}",
        f"aws-cdk.aws-route53=={cdk_ver}",
        f"aws-cdk.aws-route53-targets=={cdk_ver}",
        f"aws-cdk.aws-certificatemanager=={cdk_ver}",
        f"aws-cdk.custom-resources=={cdk_ver}",
        f"aws-cdk.aws-iam=={cdk_ver}",
        f"aws-cdk.aws-sqs=={cdk_ver}",
        f"aws-cdk.aws-lambda-event-sources=={cdk_ver}",
        f"aws-cdk.aws-ec2=={cdk_ver}",
        f"aws-cdk.aws-elasticache=={cdk_ver}",
        f"aws-cdk.aws-lambda-python=={cdk_ver}",
        f"aws-cdk.aws-kms=={cdk_ver}",
        f"aws-cdk.aws-secretsmanager=={cdk_ver}",
        f"aws-cdk.aws-ecs=={cdk_ver}",
        f"aws-cdk.aws-logs=={cdk_ver}",
        f"aws-cdk.aws-ecs-patterns=={cdk_ver}",
        f"aws-cdk.aws-elasticloadbalancingv2=={cdk_ver}",
        f"aws-cdk.aws-ecr-assets=={cdk_ver}",
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
