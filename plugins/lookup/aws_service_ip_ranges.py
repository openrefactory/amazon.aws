# (c) 2016 James Turner <turnerjsm@gmail.com>
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
name: aws_service_ip_ranges
author:
  - James Turner (!UNKNOWN) <turnerjsm@gmail.com>
requirements:
  - must have public internet connectivity
short_description: Look up the IP ranges for services provided in AWS such as EC2 and S3.
description:
  - AWS publishes IP ranges used on the public internet by EC2, S3, CloudFront, CodeBuild, Route53, and Route53 Health Checking.
  - This module produces a list of all the ranges (by default) or can narrow down the list to the specified region or service.
options:
  service:
    description: 'The service to filter ranges by. Options: EC2, S3, CLOUDFRONT, CODEbUILD, ROUTE53, ROUTE53_HEALTHCHECKS'
  region:
    description: 'The AWS region to narrow the ranges to. Examples: us-east-1, eu-west-2, ap-southeast-1'
  ipv6_prefixes:
    description: 'When I(ipv6_prefixes=True) the lookup will return ipv6 addresses instead of ipv4 addresses'
    version_added: 2.1.0
'''

EXAMPLES = """
vars:
  ec2_ranges: "{{ lookup('aws_service_ip_ranges', region='ap-southeast-2', service='EC2', wantlist=True) }}"
tasks:

- name: "use list return option and iterate as a loop"
  debug: msg="{% for cidr in ec2_ranges %}{{ cidr }} {% endfor %}"
# "52.62.0.0/15 52.64.0.0/17 52.64.128.0/17 52.65.0.0/16 52.95.241.0/24 52.95.255.16/28 54.66.0.0/16 "

- name: "Pull S3 IP ranges, and print the default return style"
  debug: msg="{{ lookup('aws_service_ip_ranges', region='us-east-1', service='S3') }}"
# "52.92.16.0/20,52.216.0.0/15,54.231.0.0/17"
"""

RETURN = """
_raw:
  description: comma-separated list of CIDR ranges
"""

import json

from ansible.errors import AnsibleLookupError
from ansible.module_utils.six.moves.urllib.error import HTTPError
from ansible.module_utils.six.moves.urllib.error import URLError
from ansible.module_utils._text import to_native
from ansible.module_utils.urls import ConnectionError
from ansible.module_utils.urls import open_url
from ansible.module_utils.urls import SSLValidationError
from ansible.plugins.lookup import LookupBase


class LookupModule(LookupBase):
    def run(self, terms, variables, **kwargs):
        if "ipv6_prefixes" in kwargs and kwargs["ipv6_prefixes"]:
            prefixes_label = "ipv6_prefixes"
            ip_prefix_label = "ipv6_prefix"
        else:
            prefixes_label = "prefixes"
            ip_prefix_label = "ip_prefix"

        try:
            resp = open_url('https://ip-ranges.amazonaws.com/ip-ranges.json')
            amazon_response = json.load(resp)[prefixes_label]
        except getattr(json.decoder, 'JSONDecodeError', ValueError) as e:
            # on Python 3+, json.decoder.JSONDecodeError is raised for bad
            # JSON. On 2.x it's a ValueError
            raise AnsibleLookupError("Could not decode AWS IP ranges: {0}".format(to_native(e)))
        except HTTPError as e:
            raise AnsibleLookupError("Received HTTP error while pulling IP ranges: {0}".format(to_native(e)))
        except SSLValidationError as e:
            raise AnsibleLookupError("Error validating the server's certificate for: {0}".format(to_native(e)))
        except URLError as e:
            raise AnsibleLookupError("Failed look up IP range service: {0}".format(to_native(e)))
        except ConnectionError as e:
            raise AnsibleLookupError("Error connecting to IP range service: {0}".format(to_native(e)))

        if 'region' in kwargs:
            region = kwargs['region']
            amazon_response = (item for item in amazon_response if item['region'] == region)
        if 'service' in kwargs:
            service = str.upper(kwargs['service'])
            amazon_response = (item for item in amazon_response if item['service'] == service)
        iprange = [item[ip_prefix_label] for item in amazon_response]
        return iprange
