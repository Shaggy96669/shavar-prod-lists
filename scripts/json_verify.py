#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import glob
import json
import re
from types import DictType, ListType, UnicodeType
from urlparse import urlparse

parser = argparse.ArgumentParser(description='Verify json files for shavar.')
parser.add_argument("-f", "--file", help="filename to verify")

bad_uris = []
errors = []
file_contents = []
file_name = ""
result = 0


def run(file):
    global file_name
    file_name = file
    try:
        verify(file)
    except:
        errors.append("\tError: Problem handling file")
    finish()


def verify(file):
    try:
        with open(file) as f:
            raw_data = f.readlines()
            # save contents of file, including line numbers
            for x in range(0, len(raw_data)):
                line_number = x+1
                file_contents.append([raw_data[x], line_number])
            # attempt to parse file as json
            json_obj = json.loads("".join(raw_data))
            try:
                # determine which schema this file uses
                if ("categories" in json_obj):
                    # google_mapping.json
                    # disconnect_blacklist.json
                    find_uris(json_obj["categories"])
                else:
                    # disconnect_entitylist.json
                    find_uris_in_entities(json_obj)
            except:
                errors.append("\tError: Can't parse file")
    except ValueError as e:
        # invalid json formatting
        errors.append("\tError: %s" % e)
        return
    except IOError as e:
        # non-existent file
        errors.append("\tError: Can't open file: %s" % e)
        return


"""
categories_json is expected to match this format:
    "categories": {
        "Disconnect": [
            {
                "Facebook": {
                    "http://www.facebook.com/": [
                        "facebook.com",
                        ...
                    ]
                }
            },
            {
                "Google": {
                    "http://www.google.com/": [
                        "2mdn.net",
                        ...
                    ]
                }
            },
            ...
        ],
        "Advertising": [
            {
                "[x+1]": {
                    "http://www.xplusone.com/": [
                        "ru4.com",
                        ...
                    ]
                }
            },
        ]
        ...
    }
"""
def find_uris(categories_json):
    assert type(categories_json) is DictType
    for category, category_json in categories_json.iteritems():
        assert type(category) is UnicodeType
        assert type(category_json) is ListType
        for entity in category_json:
            assert type(entity) is DictType
            for entity_name, entity_json in entity.iteritems():
                assert type(entity_name) is UnicodeType
                assert type(entity_json) is DictType
                # pop dnt out of the dict, so we can iteritems() over the rest
                try:
                    dnt_value = entity_json.pop('dnt', '')
                    assert dnt_value in ["w3c", "eff", ""]
                except AssertionError:
                    errors.append("%s has bad DNT value: %s" % (entity_name,
                                                                dnt_value))
                for domain, uris in entity_json.iteritems():
                    assert type(domain) is UnicodeType
                    assert type(uris) is ListType
                    for uri in uris:
                        check_uri(uri)


def find_uris_in_entities(entitylist_json):
    assert len(entitylist_json.items()) > 0
    assert type(entitylist_json) is DictType
    for entity, types in entitylist_json.iteritems():
        assert type(entity) is UnicodeType
        assert type(types) is DictType
        for prop_type, uris in types.iteritems():
            assert prop_type in ["properties", "resources"]
            assert type(uris) is ListType
            [check_uri(uri) for uri in uris]


def check_uri(uri):
    # Valid URI:
    # 	no scheme, port, fragment, path or query string
    # 	no disallowed characters
    # 	no leading/trailing garbage
    parsed_uri = urlparse(uri)
    try:
        assert parsed_uri.scheme == ''
        # domains of urls without schemes are parsed into 'path'
        assert parsed_uri.netloc == ''
        assert parsed_uri.params == ''
        assert parsed_uri.query == ''
        assert parsed_uri.fragment == ''
        assert len(parsed_uri.path) < 128
    except AssertionError:
        bad_uris.append(uri)
    return


def find_line_number(uri):
    line = 0
    try:
        for x in range(0, len(file_contents)):
            temp = file_contents[x][0].decode("utf-8", "ignore")
            if re.search(uri, temp):
                line = file_contents[x][1]
                file_contents.pop(x)
                break
    except ValueError as e:
        print e
        line = -1
    return str(line)


def make_errors_from_bad_uris():
    for x in range(0, len(bad_uris)):
        errors.append("\tError: Bad URI: %s\t: in line %s" %
                      (bad_uris[x], find_line_number(bad_uris[x])))


def finish():
    make_errors_from_bad_uris()
    if (len(errors) == 0):
        print "\n" + file_name + " : valid"
    else:
        global result
        result = 1
        print "\n" + file_name + " : invalid"
        for error in errors:
            print error
    reset()


def reset():
    global bad_uris
    bad_uris = []
    global errors
    errors = []
    global file_contents
    file_contents = []
    global file_name
    file_name = ""


def start(filename=None):
    if (filename):
        run(filename)
    else:
        for f in glob.glob("*.json"):
            run(f)


args = parser.parse_args()
start(args.file)
exit(result)