#!/usr/bin/python

import re
import sys
import json
import pprint

data = None
writes = {}

def lreplace(pattern, sub, string):
  return re.sub('^%s' % pattern, sub, string)

def parse_reads ( reads, level = 1 ) :
  files = []
  for read in reads :
    if read in writes :
      # print '\t'*level, read
      files.extend(parse_reads(writes[read], level+1)) 
    else :
      files.append(read)
  return files

def parse_writes () :
  global writes 

  for write in writes.iterkeys() :
    new_write = []
    for read in writes[write] :
      if read != write :
        new_write.append(read)
    writes[write] = new_write
      
  result = {}
  for write in writes.iterkeys() :
    #print write
    result[write] = list(set(parse_reads(writes[write])))
      
  writes = result

def parse_process ( pid, wd ) :
  global writes

  p = data['processes'][pid] 

  for i in range(0, len(p['writes'])) :
    r = []
    for read in p['reads'] :
      if (read.startswith(wd) or read.startswith('/tmp')) and p['writes'].count(read) == 0 :
        r.append(lreplace(wd, '', read))

    if r :
      writes[lreplace(wd, '', p['writes'][i])] = r

  for i in range(0, len(p['children'])) :
    parse_process(p['children'][i], wd)

def parse_file ( filename ) :
  global data

  try :
    text = open(filename, 'r').read()
    data = json.loads(text)
  except Exception, e :
    print "Error:", str(e)

  parse_process(data['start'], data['cwd'] + '/')

  parse_writes()

  pp = pprint.PrettyPrinter(indent=2)
  pp.pprint(writes)

if __name__ == '__main__' :
  if len(sys.argv) != 2 :
    print 'Usage:', sys.argv[0], 'input-file'
    sys.exit()

  sys.setrecursionlimit(20)
  parse_file(sys.argv[1])
