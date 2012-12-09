#!/usr/bin/python

import re
import sys
import json
import pprint
#import pydot

data = None
graph = False
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

new_procs = {'processes': {}}

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

  #parse_writes()

  if graph :
    make_graph3()
  else :
    print json.dumps(new_procs, indent=4)

def make_graph() :
  g = pydot.Dot(graph_type='digraph')
  nodes = {}

  for p in new_procs['processes'] :
    if p not in nodes:
      nodes[p] = pydot.Node(p)

    for c in new_procs['processes'][p]['children'] :
      if c not in nodes:
        nodes[c] = pydot.Node(c)

      print p, '->', c
      g.add_edge(pydot.Edge(nodes[p], nodes[c]))

  g.write_svg('out.svg')
  g.write_raw('out.raw')

def make_graph2() :
  g = pydot.Dot(graph_type='digraph')
  files = {}

  for p in new_procs['processes'] :
    p = new_procs['processes'][p]
    for write in p['writes'] :
      if write not in files:
        files[write] = pydot.Node(write)

      for read in p['reads'] :
        if read not in files:
          files[read] = pydot.Node(read)

        #print write, '->', read
        g.add_edge(pydot.Edge(files[write], files[read]))

  g.write_svg('out.svg')
  g.write_raw('out.raw')

def make_graph3() :
  data = {}

  idx = 0
  for p in new_procs['processes'] :
    p = new_procs['processes'][p]
    for write in p['writes'] :
      if write not in files:
        files[write] = pydot.Node(write)

      for read in p['reads'] :
        if read not in files:
          files[read] = pydot.Node(read)

        #print write, '->', read
        g.add_edge(pydot.Edge(files[write], files[read]))

    idx += 1

if __name__ == '__main__' :
  if len(sys.argv) < 2 :
    print 'Usage:', sys.argv[0], 'input-file'
    sys.exit()

  if len(sys.argv) == 3 and sys.argv[2] == "graph" :
    graph = True

  sys.setrecursionlimit(20)
  parse_file(sys.argv[1])
