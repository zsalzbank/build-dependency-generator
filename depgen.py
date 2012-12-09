#!/usr/bin/python

import re
import sys
import json
import pprint
#import pydot

data = None
writes = {}
new_procs = {'processes': {}}

def lreplace(pattern, sub, string):
  return re.sub('^%s' % pattern, sub, string)

def parse_process ( pid, wd ) :
  global new_procs

  p = data['processes'][pid] 

  new_children = []
  for i in range(0, len(p['children'])) :
    if (parse_process(p['children'][i], wd)) :
      new_children.append(p['children'][i])
  p['children'] = new_children

  new_reads = []
  for read in p['reads'] :
    if read.startswith(wd) or read.startswith('/tmp') :
      new_reads.append(lreplace(wd, '', read))
  p['reads'] = new_reads
      
  new_writes = []
  for write in p['writes'] :
    if write.startswith(wd) or write.startswith('/tmp') :
      new_writes.append(lreplace(wd, '', write))
  p['writes'] = new_writes

  if len(new_reads) == 0 and len(new_writes) == 0 and len(new_children) == 0:
    return False
  else :
    new_procs['processes'][pid] = p
    return True

def parse_file ( filename ) :
  global data

  try :
    text = open(filename, 'r').read()
    data = json.loads(text)
  except Exception, e :
    print "Error:", str(e)

  parse_process(data['start'], data['cwd'] + '/')
  new_procs['start'] = data['start']

  print json.dumps(new_procs, indent=4)

if __name__ == '__main__' :
  if len(sys.argv) < 2 :
    print 'Usage:', sys.argv[0], 'input-file'
    sys.exit()

  sys.setrecursionlimit(20)
  parse_file(sys.argv[1])
