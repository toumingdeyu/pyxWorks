#!/usr/bin/python

import sys, os, io, time
import cgi
import cgitb; cgitb.enable()

if __name__ != "__main__": sys.exit(0)

### https://jsonapi.org/examples/#error-objects
### runnable in firefox

json_data = """
{
  "meta": {
    "totalPages": 13
  },
  "data": [
    {
      "type": "articles",
      "id": "3",
      "attributes": {
        "title": "JSON:API paints my bikeshed!",
        "body": "The shortest article. Ever.",
        "created": "2015-05-22T14:56:29.000Z",
        "updated": "2015-05-22T14:56:28.000Z"
      }
    }
  ],
  "links": {
    "self": "http://example.com/articles?page[number]=3&page[size]=1",
    "first": "http://example.com/articles?page[number]=1&page[size]=1",
    "prev": "http://example.com/articles?page[number]=2&page[size]=1",
    "next": "http://example.com/articles?page[number]=4&page[size]=1",
    "last": "http://example.com/articles?page[number]=13&page[size]=1"
  }
}
"""

print("Content-type: application/vnd.api+json")
print("Status: %s %s\r\n" % ('222',""))
print(json_data)



