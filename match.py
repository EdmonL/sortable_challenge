#!/usr/bin/env python

def parse_args():
  import argparse

  argparser = argparse.ArgumentParser(description='Match price listings with products.')
  argparser.add_argument('--products', '-p', metavar='<path>', required=True, nargs='+', help='product files')
  argparser.add_argument('listings', metavar='<listing file>', nargs='+', help='listing files')
  argparser.add_argument('--output', '-o', metavar='<path>', help='output file')
  return argparser.parse_args()


def make_tokenizer():
  import re

  nonalphanum = re.compile(r'[\W_]+', re.UNICODE)

  def tokenize(s):
    for t in re.sub(nonalphanum, ' ', s.lower()).split():
      yield t

  return tokenize


tokenize = make_tokenizer()


def normalize_product(p):
  pname = p['product_name']
  required = set(tokenize(p['manufacturer'] + ' ' + p['model']))
  optional = set(tokenize(p.get('family', ''))) - required # family is optional to mention
  return (pname, required, optional)


def listing_description(l):
  return set(tokenize(l['title'] + ' ' + l['manufacturer']))


if __name__ == '__main__':
  args = parse_args()

  import fileinput
  import itertools
  import json

  index = {}
  products = {}
  for line in fileinput.input(args.products):
    p = normalize_product(json.loads(line))
    products[p[0]] = (p[1], p[2])
    for t in itertools.chain(p[1], p[2]):
      postings = index.get(t, [])
      postings.append(p[0])
      index[t] = postings
  fileinput.close()

  matches = {}
  for line in fileinput.input(args.listings):
    listing = json.loads(line)
    d = listing_description(listing)
    candidates = {}
    for t in d:
      for pname in index.get(t, []):
        candidates[pname] = candidates.get(pname, 0) + 1
    for pname in candidates.keys():
      p = products[pname]
      l = candidates[pname]
      if l == len(p[0]) + len(p[1]) or l == len(p[0]) and p[0].issubset(d):
        continue
      del candidates[pname]
    if len(candidates) == 1:
      pname = candidates.iterkeys().next()
      l = matches.get(pname, [])
      l.append(listing)
      matches[pname] = l
  fileinput.close()

  for pname, l in matches.iteritems():
    print json.dumps({'product_name': pname, 'listings': l})


