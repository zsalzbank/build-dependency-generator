#!/usr/bin/python

import os
import sys
import re
from process import Process
import json

start = None
accesses = False
processes = {}

re_pid_line = re.compile('(?P<pid>\d*)\s*(?P<line>.*)')
re_result = re.compile('(?P<result>-?\d*)')
re_execve = re.compile('execve\("(?P<process>.*?)", (?P<args>\[.*\]),')
re_access = re.compile('access\("(?P<file>.*?)"')
re_open = re.compile('open\("(?P<file>.*?)"')
re_openat = re.compile('openat\((?P<fd>.*?), "(?P<file>.*?)"')
re_read = re.compile('read\((?P<fd>\d*),')
re_rename = re.compile('rename\("(?P<fn1>.*?)", "(?P<fn2>.*?)"\)')
re_pipe = re.compile('pipe\(\[(?P<fd1>\d*), (?P<fd2>\d*)')
re_dup2 = re.compile('dup2\((?P<fd1>\d*), (?P<fd2>\d*)')
re_dup = re.compile('dup\((?P<fd1>\d*)\)')
re_fcntl = re.compile('fcntl\((?P<fd1>\d*), (?P<command>.*?),')
re_write = re.compile('write\((?P<fd>\d*),')
re_close = re.compile('close\((?P<fd>\d*)\)')
re_chdir = re.compile('chdir\("(?P<dir>.*?)"\)')
re_unf = re.compile('(?P<command>.*?)\s*<unfinished ...>')
re_res = re.compile('<... (.*?) resumed>\s*(?P<command>.*)')

def get_process_number ( line ) :
    m = re_pid_line.match(line) 
    return int(m.group('pid')), m.group('line')

def get_result ( line ) :
    parts = line.split('=')
    result = parts[len(parts) - 1].strip()
    m = re_result.search(result)
    if m is None :
      return -1
    else :
      return int(m.group('result'))

def parse_line ( pid, line ) :
  global processes

  # are we starting an executable
  if line.startswith('execve(') :
    m = re_execve.match(line)

    # did it run succesfully?
    if get_result(line) == 0 :
      processes[pid].set_executable(m.group('process'))
      try :
        args = json.loads(m.group('args'))
        for a in args :
          processes[pid].add_arg(a)
      except Exception as e :
          processes[pid].add_arg("<unreadable>")

  # are we accessing a file?
  elif accesses and line.startswith('access(') :
    m = re_access.match(line)
    result = get_result(line)

    if result >= 0 :
      processes[pid].add_access(m.group('file'))

  # are we opening a file?
  elif line.startswith('open('):
    m = re_open.match(line)
    fd = get_result(line)

    if fd >= 0 :
      processes[pid].add_fd(fd, m.group('file'))
      processes[pid].add_access(m.group('file'))
      if 'O_CREAT' in line :
        processes[pid].add_write(processes[pid].get_file(fd))
      
  elif line.startswith('openat('):
    m = re_openat.match(line)
    fd = get_result(line)

    if fd >= 0 :
      processes[pid].add_fd(fd, m.group('file'))
      processes[pid].add_access(m.group('file'))
      if 'O_CREAT' in line :
        processes[pid].add_write(processes[pid].get_file(fd))

  # are we reading a file?
  elif line.startswith('read(') :
    m = re_read.match(line)
    fd = int(m.group('fd'))
    fname = processes[pid].get_file(fd)
    result = get_result(line)

    if result >= 0 :
      processes[pid].add_read(fname)

  # are we moving a file?
  elif line.startswith('rename(') :
    m = re_rename.match(line)
    processes[pid].add_access(m.group('fn1'))
    processes[pid].add_access(m.group('fn2'))

    if get_result(line) >= 0 :
      processes[pid].add_read(m.group('fn1'))
      processes[pid].add_write(m.group('fn2'))

  # are we creating a pipe
  elif line.startswith('pipe(') :
    m = re_pipe.match(line)
    fd1 = int(m.group('fd1'))
    fd2 = int(m.group('fd2'))

    processes[pid].add_fd(fd1, '<PIPE>')
    processes[pid].add_fd(fd2, '<PIPE>')

  # are we duplicating an fd
  elif line.startswith('dup2(') :
    m = re_dup2.match(line)
    fd1 = int(m.group('fd1'))
    fd2 = int(m.group('fd2'))

    processes[pid].add_fd(fd2, processes[pid].get_file(fd1))

  # are we duplicating an fd
  elif line.startswith('dup(') :
    m = re_dup.match(line)
    fd1 = int(m.group('fd1'))
    fd2 = get_result(line)

    processes[pid].add_fd(fd2, processes[pid].get_file(fd1))

  # are we using fcntl
  elif line.startswith('fcntl(') :
    m = re_fcntl.match(line)
    if m is not None :
      command = m.group('command')
      
      if command == 'F_DUPFD' :
        fd1 = int(m.group('fd1'))
        fd2 = get_result(line)
        processes[pid].add_fd(fd2, processes[pid].get_file(fd1))

  # are we writing a file?
  elif line.startswith('write(') :
    m = re_write.match(line)
    fd = int(m.group('fd'))
    result = get_result(line)

    if result >= 0 :
      processes[pid].add_write(processes[pid].get_file(fd))

  # are we closing a file?
  elif line.startswith('close(') :
    m = re_close.match(line)
    fd = int(m.group('fd'))
    result = get_result(line)

    if result >= 0 :
      processes[pid].close_fd(fd)

  # are we cloning this process?
  elif line.startswith('clone(') :
    npid = get_result(line)

    processes[npid] = processes[pid].clone(npid, pid)
    processes[pid].add_child(npid)

  # are we forking this process?
  elif line.startswith('vfork(') :
    npid = get_result(line)

    processes[npid] = processes[pid].clone(npid, pid)
    processes[pid].add_child(npid)

  # are we changing directories?
  elif line.startswith('chdir(') :
    m = re_chdir.match(line)
    ch = m.group('dir')
    result = get_result(line)

    if result == 0 :
      processes[pid].set_cwd(ch)

def parse_file ( filename ) :
  global start, processes

  tot_lines = sum(1 for line in open(filename))

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

      unf = re_unf.search(line)
      if unf is not None :
        processes[pid].set_unfinished(unf.group('command'))
      else :
        if processes[pid].get_unfinished() is not None :
          res = re_res.search(line)
          if res is not None : 
            line = processes[pid].get_unfinished() + res.group('command')
            parse_line(pid, line)
            processes[pid].set_unfinished(None)
        else :
          parse_line(pid, line)

      sys.stderr.write("Line %d/%d -> %f\r" % (i, tot_lines, i*100.0/tot_lines,))      
      i += 1
  except Exception, e :
    print "Error (line", i, "):", str(e)
    print "\t", line

  print ""
  output = {}
  output['start'] = start 
  output['cwd'] = orig_cwd
  output['processes'] = {}
  for key in processes.iterkeys():
    output['processes'][int(key)] = processes[key].json()
  print json.dumps(output, indent=4)

if __name__ == '__main__' :
  if len(sys.argv) != 2 :
    print 'Usage:', sys.argv[0], 'input-file'
    sys.exit()

  sys.setrecursionlimit(10000)
  parse_file(sys.argv[1])
