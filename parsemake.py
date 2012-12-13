#!/usr/bin/python

import os
import sys
import re
import json
from collections import deque

files = {}
dirs = {}
real = True

def makefile(d, f) :
  if f.startswith('/') : return f

  return os.path.realpath(os.path.join(d, f))

def gettarget(line) :
  try :
    return line.split('`')[1].split('\'')[0]
  except Exception, e :
    return ''

def level(dl, l):
  return (dl+l)*'  '

def myprint(s):
  if real: return
  print s

def parse_file ( filename ) :
  global dirs, files

  try :
    i = 0
    orig_cwd = os.path.dirname(os.path.abspath(filename))
    l = 0
    dl = 0
    tlist = deque('<top>')
    dirlist = deque(orig_cwd)
    currentt = '<top>'
    dircount = -1
    dirs[0] = orig_cwd

    f = open(filename, 'r')
    for line in f :
      i += 1
      t = gettarget(line)

      if 'Considering target' in line :
        if (t, dircount) not in files :
            files[(t, dircount)] = []

        tlist.append(currentt)
        currentt = t

        myprint(level(dl, l) + 'target: ' + t)
        l += 1
      elif 'Pruning file' in line :
        myprint(level(dl, l) + 'depends on: ' + t )
        files[(currentt, dircount)].append(t)
      elif 'No need to remake' in line or 'Must remake' in line :
        l -= 1
        myprint(level(dl, l) + 'done with: ' + t)
        currentt = tlist.pop()
        if l > 0 :
          if (currentt, dircount) not in files :
            files[(currentt, dircount)] = []

          files[(currentt, dircount)].append(t)
          myprint(level(dl, l) + 'depends on: ' + t)
      elif 'GNU Make' in line : 
        if dircount != -1 :
          myprint(level(dl, l) + 'Left directory: ' + dirs[dircount] )

        dircount += 1
        myprint(level(dl, l) + 'New directory:')
      elif 'Entering directory' in line or 'Leaving directory' in line :
        dirs[dircount] = gettarget(line)

    myprint(level(dl, l) + 'Left directory: ' + dirs[dircount] )

    output = {}
    for f in files :
      fn, dirn = f
      if fn == '<top>' : continue

      d = dirs[dirn]
      fn = makefile(d, fn).replace(orig_cwd + "/", "")
      output[fn] = []
      for dep in files[f] :
        output[fn].append(makefile(d, dep).replace(orig_cwd + "/", ""))
        
    if real:
        print json.dumps(output, indent=4)

  except Exception, e :
    print "Error (line", i, "):", str(e)
    print "\t", line

if __name__ == '__main__' :
  if len(sys.argv) != 2 :
    print 'Usage:', sys.argv[0], 'input-file'
    sys.exit()

  sys.setrecursionlimit(10000)
  parse_file(sys.argv[1])
