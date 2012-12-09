#!/usr/bin/python

import os
import sys
import re
from process import Process
import json

start = None
processes = {}
commands = []

def get_process_number ( line ) :
    m = re.search('(?P<pid>\d*)\s*(?P<line>.*)', line) 
    return m.group('pid'), m.group('line')

def parse_line ( pid, line ) :
  global processes

  m = re.search("(.*?)\(", line)
  commands.append(m.group(1))

  # are we starting an executable
  if line.startswith('execve') :
    m = re.search('execve\("(?P<process>.*?)".*? = (?P<result>\d*)', line)

    # did it run succesfully?
    if m.group('result') == '0' :
      processes[pid].set_executable(m.group('process'))

  # are we accessing a file?
  elif line.startswith('access') :
    m = re.search('access\("(?P<file>.*?)".*? = (?P<result>-?\d*)', line)
    result = int(m.group('result'))

    if result >= 0 :
      processes[pid].add_access(m.group('file'))

  # are we opening a file?
  elif line.startswith('open'):
    m = re.search('open\("(?P<file>.*?)".*? = (?P<result>-?\d*)', line)
    fd = int(m.group('result'))

    if fd >= 0 :
      processes[pid].add_fd(fd, m.group('file'))
      processes[pid].add_access(m.group('file'))

  # are we reading a file?
  elif line.startswith('read(') :
    m = re.search('read\((?P<fd>\d*).*?\)\s*= (?P<result>-?\d*)', line)
    fd = int(m.group('fd'))
    fname = processes[pid].get_file(fd)
    result = int(m.group('result'))

    if result >= 0 :
      processes[pid].add_read(fname)

  # are we moving a file?
  elif line.startswith('rename') :
    m = re.search('rename\("(?P<fn1>.*?)", "(?P<fn2>.*?)"\)\s*= (?P<result>-?\d*)', line)
    processes[pid].add_access(m.group('fn1'))
    processes[pid].add_access(m.group('fn2'))

    if int(m.group('result')) >= 0 :
      processes[pid].add_read(m.group('fn1'))
      processes[pid].add_write(m.group('fn2'))

  # are we creating a pipe
  elif line.startswith('pipe') :
    m = re.search('pipe\(\[(?P<fd1>\d*), (?P<fd2>\d*)', line)
    fd1 = int(m.group('fd1'))
    fd2 = int(m.group('fd2'))

    processes[pid].add_fd(fd1, '<PIPE>')
    processes[pid].add_fd(fd2, '<PIPE>')

  # are we duplicating an fd
  elif line.startswith('dup2') :
    m = re.search('dup2\((?P<fd1>\d*), (?P<fd2>\d*)', line)
    fd1 = int(m.group('fd1'))
    fd2 = int(m.group('fd2'))

    processes[pid].add_fd(fd2, processes[pid].get_file(fd1))

  # are we duplicating an fd
  elif line.startswith('dup') :
    m = re.search('dup\((?P<fd1>\d*)\)\s*= (?P<result>\d*)', line)
    fd1 = int(m.group('fd1'))
    fd2 = int(m.group('result'))

    processes[pid].add_fd(fd2, processes[pid].get_file(fd1))

  # are we using fcntl
  elif line.startswith('fcntl') :
    m = re.search('fcntl\((?P<fd1>\d*), (?P<command>.*?),.*?\s*= (?P<result>-?\d*)', line)
    if m is not None :
      command = m.group('command')
      
      if command == 'F_DUPFD' :
        fd1 = int(m.group('fd1'))
        fd2 = int(m.group('result'))
        processes[pid].add_fd(fd2, processes[pid].get_file(fd1))

  # are we writing a file?
  elif line.startswith('write') :
    m = re.search('write\((?P<fd>\d*), ".*?"\.?\.?\.?, \d*\)\s*= (?P<result>\d*)', line)
    fd = int(m.group('fd'))
    result = int(m.group('result'))

    if result >= 0 :
      processes[pid].add_write(processes[pid].get_file(fd))

  # are we closing a file?
  elif line.startswith('close') :
    m = re.search('close\((?P<fd>\d*)\)\s*= (?P<result>-?\d*)', line)
    fd = int(m.group('fd'))
    result = int(m.group('result'))

    if result >= 0 :
      processes[pid].close_fd(fd)

  # are we cloning this process?
  elif line.startswith('clone') :
    m = re.search('clone\(.*?\) = (?P<result>-?\d*)', line)
    npid = m.group('result')

    processes[npid] = processes[pid].clone(npid, pid)
    processes[pid].add_child(npid)

  # are we forking this process?
  elif line.startswith('vfork') :
    m = re.search('vfork\(\)\s*= (?P<result>-?\d*)', line)
    npid = m.group('result')

    processes[npid] = processes[pid].clone(npid, pid)
    processes[pid].add_child(npid)

  # are we changing directories?
  elif line.startswith('chdir') :
    m = re.search('chdir\("(?P<dir>.*?)"\)\s*= (?P<result>-?\d*)', line)
    ch = m.group('dir')
    result = int(m.group('result'))

    if result == 0 :
      processes[pid].set_cwd(ch)

  elif line.startswith('exit_group') :
    pass

def parse_file ( filename ) :
  global start, processes

  try :
    i = 1
    orig_cwd = os.path.dirname(os.path.abspath(filename))
    f = open(filename, 'r')
    for line in f :
      pid, line = get_process_number(line)

      if start is None :
        start = pid

      # is this a new process
      if pid not in processes :
        processes[pid] = Process(pid)
        processes[pid].set_cwd(orig_cwd)

      unf = re.search('(?P<command>.*?)\s*<unfinished ...>', line)
      res = re.search('<... (.*?) resumed>\s*(?P<command>.*)', line)
      if unf is not None :
        processes[pid].set_unfinished(unf.group('command'))
      elif processes[pid].get_unfinished() is not None and res is not None :
        line = processes[pid].get_unfinished() + res.group('command')
        parse_line(pid, line)
        processes[pid].set_unfinished(None)
      else :
        parse_line(pid, line)

      i += 1
  except Exception, e :
    print "Error (line", i, "):", str(e)
    print "\t", line

  output = {}
  output['start'] = start 
  output['cwd'] = orig_cwd
  output['processes'] = {}
  for key in processes.iterkeys():
    output['processes'][key] = processes[key].json()
  print json.dumps(output, indent=4)

if __name__ == '__main__' :
  if len(sys.argv) != 2 :
    print 'Usage:', sys.argv[0], 'input-file'
    sys.exit()

  parse_file(sys.argv[1])
