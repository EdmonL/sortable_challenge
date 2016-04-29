#!/usr/bin/env bash

cd "$(dirname "$0")"
/usr/bin/env python match.py -p products.txt listings.txt "$@" 
