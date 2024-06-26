# Copyright 2024 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import jwt
from jwt.exceptions import InvalidTokenError

from grpc import ServicerContext
from envoy.service.ext_proc.v3 import external_processor_pb2 as service_pb2
from extproc.service import callout_server
from extproc.service import callout_tools

def extract_jwt_token(request_headers):
  jwt_token = next((header.raw_value.decode('utf-8')
                   for header in request_headers.headers.headers
                   if header.key == 'Authorization'), None)
  extracted_jwt = jwt_token.split(' ')[1] if jwt_token and ' ' in jwt_token else jwt_token
  return extracted_jwt

def validate_jwt_token(key, request_headers, algorithm):
  jwt_token = extract_jwt_token(request_headers)
  try:
    decoded = jwt.decode(jwt_token, key, algorithms=[algorithm])
    logging.info('Approved - Decoded Values: %s', decoded)
    return decoded
  except InvalidTokenError:
    return None

class CalloutServerExample(callout_server.CalloutServer):
  """Example callout server.

  For request header callouts we provide a mutation to add multiple headers
  based on the decoded fields for example '{decoded-name: John Doe}', and to
  clear the route cache if the JWT Authorization is valid.
  A valid token example value can be found below.

  Valid Token for RS256:
  eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTcxMjE3MzQ2MSwiZXhwIjoyMDc1NjU4MjYxfQ.Vv-Lwn1z8BbVBGm-T1EKxv6T3XKCeRlvRrRmdu8USFdZUoSBK_aThzwzM2T8hlpReYsX9YFdJ3hMfq6OZTfHvfPLXvAt7iSKa03ZoPQzU8bRGzYy8xrb0ZQfrejGfHS5iHukzA8vtI2UAJ_9wFQiY5_VGHOBv9116efslbg-_gItJ2avJb0A0yr5uUwmE336rYEwgm4DzzfnTqPt8kcJwkONUsjEH__mePrva1qDT4qtfTPQpGa35TW8n9yZqse3h1w3xyxUfJd3BlDmoz6pQp2CvZkhdQpkWA1bnwpdqSDC7bHk4tYX6K5Q19na-2ff7gkmHZHJr0G9e_vAhQiE5w

  """

  def on_request_headers(
      self, headers: service_pb2.HttpHeaders,
      context: ServicerContext):
    """Custom processor on request headers."""

    decoded = validate_jwt_token(self.public_key, headers, "RS256")

    if decoded:
      decoded_items = [('decoded-' + key, str(value)) for key, value in decoded.items()]
      return callout_tools.add_header_mutation(add=decoded_items, clear_route_cache=True)
    else:
      callout_tools.deny_request(context, 'Authorization token is invalid')


if __name__ == '__main__':
  # Run the gRPC service
  CalloutServerExample(insecure_address=('0.0.0.0', 8080)).run()