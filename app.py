#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from lti13_cdk.lti13_stack import Lti13Stack


app = cdk.App()
Lti13Stack(app, "Lti13Stack")

app.synth()
