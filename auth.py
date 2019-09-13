#!/bin/python

from yahoo_oauth import OAuth2
import os
import json

#if not os.path.exists('oauth2.json'):
creds = {'consumer_key': 'dj0yJmk9U2N4dW9qczUxbmhkJmQ9WVdrOU9GUlBURE5RTldVbWNHbzlNQS0tJnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTFi', 'consumer_secret': '9fc8962891dc3d65710a30e507c0c58b4da15c2f'}
with open('oauth2.json', "w") as f:
    f.write(json.dumps(creds))
print(json.dumps(creds))

oauth = OAuth2(None, None, from_file='oauth2.json')
