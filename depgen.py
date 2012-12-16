#!/usr/bin/python

import re
import sys
import json
import pprint

data = None
writes = {}
new_procs = {'processes': {}}

def lreplace(pattern, sub, string):
  return re.sub('^%s' % pattern, sub, string)

# return true if there are relevant reads, writes or children of the
#   provided process
def parse_process ( pid, wd ) :
  global new_procs

  p = data['processes'][str(pid)] 

  # recursively parse child processes, seeing if they are relevant.
  #   only add relevant processes to the output data
  new_children = []
  for i in range(0, len(p['children'])) :
    if (parse_process(p['children'][i], wd)) :
      new_children.append(p['children'][i])
  p['children'] = new_children

  # a relevent read or write will be either in the provided working
  #   directory, or in /tmp

  # parse the reads, only including those that are relevant
  new_reads = []
  for read in p['reads'] :
    if read.startswith(wd) or read.startswith('/tmp') :
      new_reads.append(lreplace(wd, '', read))
  p['reads'] = new_reads
      
  # parse the writes, only including those that are relevant
  new_writes = []
  for write in p['writes'] :
    if write.startswith(wd) or write.startswith('/tmp') :
      new_writes.append(lreplace(wd, '', write))
  p['writes'] = new_writes

  # a process is relevant if it has any reads, writes or children
  if len(new_reads) == 0 and len(new_writes) == 0 and len(new_children) == 0:
    return False
  else :
    new_procs['processes'][pid] = p
    return True

# input file must be the json output of the depread script
def parse_file ( filename ) :
  global data

  # load the file as json into an object
  try :
    text = open(filename, 'r').read()
    data = json.loads(text)
  except Exception, e :
    print "Error:", str(e)

  # parse the data starting with the first process that is run
  #   during the build.  use the initial CWD of the build to trim
  #   any extra data from the paths
  parse_process(data['start'], data['cwd'] + '/')

  # make sure to keep the start process for the output
  new_procs['start'] = data['start']

  # output the new data
  print json.dumps(new_procs, indent=4)

if __name__ == '__main__' :
  # requires the first argument to be the input file
  if len(sys.argv) < 2 :
    print 'Usage:', sys.argv[0], 'input-file'
    sys.exit()

  sys.setrecursionlimit(20)

  # parse the input file
  parse_file(sys.argv[1])
