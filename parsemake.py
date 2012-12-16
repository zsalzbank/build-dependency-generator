#!/usr/bin/python

import os
import sys
import re
import json
from collections import deque

# a has of files and the files it depends on
files = {}

# list of directories encountered during parsing
dirs = {}

# return the absolute path of the specified file
def makefile(d, f) :
  if f.startswith('/') : return f

  return os.path.realpath(os.path.join(d, f))

# return the target of the line from the makefile, it
#   it is present
def gettarget(line) :
  try :
    return line.split('`')[1].split('\'')[0]
  except Exception, e :
    return ''

# get some spacing for output
def level(dl, l):
  return (dl+l)*'  '

def myprint(s):
  sys.stderr.write(s + "\n")

# parse the output of a makefiles rules
def parse_file ( filename ) :
  global dirs, files

  i = 0
  l = 0
  dl = 0

  # original CWD is parent directory of file
  orig_cwd = os.path.dirname(os.path.abspath(filename))
  dirs[0] = orig_cwd

  # queue of targets being processed
  tlist = deque('<top>')

  # current index of directory that the makefile is in
  dircount = -1

  # current target being processed
  currentt = '<top>'

  try :
    # parse file line by line
    f = open(filename, 'r')
    for line in f :
      i += 1
      t = gettarget(line)

      # a target was encountered
      if 'Considering target' in line :
        # if the target was never encountered, create it 
        if (t, dircount) not in files :
            files[(t, dircount)] = []

        # add the target to the queue and mark it as the current one
        #   being processed
        tlist.append(currentt)
        currentt = t

        myprint(level(dl, l) + 'target: ' + t)
        l += 1

      # the target was previously processed, but it is still a dependency
      #   of the parent target
      elif 'Pruning file' in line :
        myprint(level(dl, l) + 'depends on: ' + t )
        files[(currentt, dircount)].append(t)

      # the current target is finished
      elif 'No need to remake' in line or 'Must remake' in line :
        l -= 1
        myprint(level(dl, l) + 'done with: ' + t)

        # remove the target from the queue of those being processed
        currentt = tlist.pop()

        # if the target was started by another target, make sure the
        #   net current target exists in the current directory
        if l > 0 :
          if (currentt, dircount) not in files :
            files[(currentt, dircount)] = []

          # mark the current target as dependent on the target of this line
          files[(currentt, dircount)].append(t)
          myprint(level(dl, l) + 'depends on: ' + t)

      # inidicates that a new makefile was opened, which can mean
      #   that the working directory was changed
      elif 'GNU Make' in line : 
        if dircount != -1 :
          myprint(level(dl, l) + 'Left directory: ' + dirs[dircount] )

        # inrement the index of the current directory so it can be used
        #   later
        dircount += 1
        myprint(level(dl, l) + 'New directory:')

      # mark the current directory index with the acutal path of the directory ir
      #   corresponds to.  there is no way to know the directory before parsing the
      #   rules, so this index method must be used
      elif 'Entering directory' in line or 'Leaving directory' in line :
        dirs[dircount] = gettarget(line)

    myprint(level(dl, l) + 'Left directory: ' + dirs[dircount] )

    # loop through the targets and replace the directory index with the acutal
    #   path of the directory, creating full paths of files
    output = {}
    for f in files :
      fn, dirn = f
      if fn == '<top>' : continue

      d = dirs[dirn]
      fn = makefile(d, fn).replace(orig_cwd + "/", "")
      output[fn] = []
      for dep in files[f] :
        output[fn].append(makefile(d, dep).replace(orig_cwd + "/", ""))
        
    # output the results
    print json.dumps(output, indent=4)

  except Exception, e :
    print "Error (line", i, "):", str(e)
    print "\t", line

if __name__ == '__main__' :
  # require an input file. must be the output of a 'make -dn' command
  if len(sys.argv) != 2 :
    print 'Usage:', sys.argv[0], 'input-file'
    sys.exit()

  sys.setrecursionlimit(10000)

  # parse the file
  parse_file(sys.argv[1])
