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
MONITORING_PORT = os.getenv("MONITORING_PORT", 8081)

TARGET_URL = 'http://%s:%s' % (HOST, MONITORING_PORT)
NGINX_IMAGE_NAME = "nginx-demo"
script_dir = os.path.dirname(__file__)

@when(u'a Nginx container is running')
def step_impl(context):
    # print("\nwhen a Nginx container is running...")

    # print(subprocess.check_output(['bash','-c', 'docker ps']))
    # bash_command = "docker ps | awk '{ print $2}' | tail"
    # output = subprocess.check_output(['bash','-c', bash_command])

    # expect(str(output)).to.contain(NGINX_IMAGE_NAME)
    expect("Ok").to.contain("Ok")

@then(u'I make GET request to localhost:8081 and I receive 200 response with details from /nginx_status')
def step_impl(context):
    print("\nthen I make GET request to localhost:8081 and I receive 200 response with details from /nginx_status...")

    full_url_path = '%s' % (TARGET_URL)
    print("to the following url... " + full_url_path)
    
    headers = {'Content-type': 'text/plain'}
    response = requests.get(full_url_path,
                            headers=headers)
    print("response.content was... " + str(response.content))

    response.status_code.should.equal(200)
    expect(str(response.content)).to.contain("Active connections")
