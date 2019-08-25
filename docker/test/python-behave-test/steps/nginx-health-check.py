#!/usr/bin/env python3
import os
import unittest
import socket
import time
import pdb
import json
import requests
from sure import expect
import subprocess

HOST = os.getenv("HOST", "localhost")
HTTP_PORT = os.getenv("HTTP_PORT", 8080)

HTTP_TARGET_URL = 'http://%s:%s' % (HOST, HTTP_PORT)
HEALTH_CHECK_ENDPOINT = "healthz"

script_dir = os.path.dirname(__file__)

@then(u'I make GET request to http://localhost:8080/healthz then I should receive 200')
def step_impl(context):
    print("\nthen I make GET request to http://localhost:8080/healthz then I should receive 200...")

    full_url_path = '%s/%s' % (HTTP_TARGET_URL, HEALTH_CHECK_ENDPOINT)
    print("to the following url... " + full_url_path)
    
    headers = {'Content-type': 'text/plain'}
    response = requests.get(full_url_path,
                            headers=headers)
    print("response.content was... " + str(response.content))

    response.status_code.should.equal(200)
    expect(str(response.content)).to.contain("Hello from /healthz")
