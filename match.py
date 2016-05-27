#!/usr/bin/env python

def parse_args():
  import argparse

  argparser = argparse.ArgumentParser(description='Match price listings with products.')
  argparser.add_argument('--product', '-p', metavar='<path>', required=True, help='product file')
  argparser.add_argument('listings', metavar='<listing file>', nargs='+', help='listing files')
  argparser.add_argument('--output', '-o', metavar='<path>', help='output file')
  return argparser.parse_args()


def make_tokenizer():
  import re

  nonalphanum = re.compile(r'(([^\w.]|_)+)|([\W_][\W_]+)|(\s+[\W_]+)|([\W_]+)\s+', re.UNICODE)
  decimal = re.compile(r'(\d+\.\d+)', re.UNICODE)
  uselessdot1 = re.compile(r'(\d)\.([^\d])', re.UNICODE)
  uselessdot2 = re.compile(r'([^\d])\.(\d)', re.UNICODE)

  def tokenize(s):
    s = s.lower()
    s = re.sub(nonalphanum, ' ', s)
    s = re.sub(decimal, r' \1 ', s)
    s = re.sub(uselessdot1, r'\1  \2', s)
    s = re.sub(uselessdot2, r'\1  \2', s)
    for t in s.split():
      t = t.strip('.')
      if t:
        yield t

  return tokenize


tokenize = make_tokenizer()


def compose_str(l):
  return ' ' + ' '.join(t.strip() for t in l) + ' '


def index(l, index, name):
  for t in l:
    postings = index.get(t)
    if postings == None:
      index[t] = [pname]
    else:
      postings.append(pname)


if __name__ == '__main__':
  args = parse_args()

  import fileinput
  import json
  import sys

  if args.output is not None:
    sys.stdout = open(unicode(args.output), 'w')

  manuf_index = {} # token -> list of names
  model_index = {} # token -> list of names
  products = {} # name -> (manufacturer, family, model)
  with open(args.product) as f:
    for p in f:
      p = json.loads(p)
      pname = p['product_name']
      manuf = tuple(tokenize(p['manufacturer']))
      assert manuf
      index(manuf, manuf_index, pname)
      model = tuple(tokenize(p['model']))
      assert model
      index(model, model_index, pname)
      family = tuple(tokenize(p.get('family', '')))
      products[pname] = (compose_str(manuf), compose_str(family), compose_str(model))

  matches = {}
  for l in fileinput.input(args.listings):
    l = json.loads(l)
    manuf = tuple(tokenize(l['manufacturer']))
    title = tuple(tokenize(l['title']))
    if not manuf:
      manuf = title
    manuf_cands = set(p for t in manuf for p in manuf_index.get(t, ()))
    manuf = compose_str(manuf)
    for pname in tuple(manuf_cands):
      if products[pname][0] not in manuf:
        manuf_cands.remove(pname)
    if not manuf_cands:
      continue
    model_cands = set(p for t in title for p in model_index.get(t, ()) if p in manuf_cands)
    del manuf_cands
    title = compose_str(title)
    for pname in tuple(model_cands):
      p = products[pname]
      if p[2] not in title or p[1].strip() and p[1] not in title:
        model_cands.remove(pname)
    if not model_cands:
      continue
    cands = {}
    maxlen = 0
    for pname in model_cands:
      p = products[pname]
      s = compose_str(p)
      if maxlen < len(s):
        maxlen = len(s)
        maxp = p
      cands[pname] = (p, s)
    del model_cands
    for pname in cands.keys():
      p, s = cands[pname]
      if len(s) < maxlen and p[0] in maxp[0] and p[1] in maxp[1] and p[2] in maxp[2]:
        del cands[pname]
    cands = cands.keys()

    if len(cands) == 1:
      pname = cands[0]
      listings = matches.get(pname)
      if listings == None:
        matches[pname] = [l]
      else:
        listings.append(l)
  fileinput.close()

  for pname, l in matches.iteritems():
    print json.dumps({'product_name': pname, 'listings': l})

  if hasattr(args, 'output'):
    sys.stdout.close()
    sys.stdout = sys.__stdout__


