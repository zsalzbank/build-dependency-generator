#!/usr/bin/python

import os
import sys
import re
from process import Process
import json

start = None
accesses = False
processes = {}

# regular expressions used to parse the input file
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


# return the process id and remaining text of the supplied line
def get_process_number ( line ) :
    m = re_pid_line.match(line) 
    return int(m.group('pid')), m.group('line')

# return the result of a system call
def get_result ( line ) :
    # the result will be the last occurence of a value
    #   after an equal sign
    parts = line.split('=')
    result = parts[len(parts) - 1].strip()

    # parse whatever is after the equal sign to get the
    #   actual value, trimming any extra text
    m = re_result.search(result)

    if m is None :
      # if the regex failed, then there is no result
      return -1
    else :
      return int(m.group('result'))

# parse a system call, modifying the parameters of the specified
#   process that the system call occurred in
def parse_line ( pid, line ) :
  global processes

  # an executable is being started
  if line.startswith('execve(') :
    m = re_execve.match(line)

    # set information about the executable if it 
    #   started successfully
    if get_result(line) == 0 :
      processes[pid].set_executable(m.group('process'))

      # try to get the arguments for the executable.  they
      #   are not available sometimes because strace did not
      #   output all of them
      try :
        args = json.loads(m.group('args'))
        for a in args :
          processes[pid].add_arg(a)
      except Exception as e :
          processes[pid].add_arg("<unreadable>")

  # was a file accessed?
  elif accesses and line.startswith('access(') :
    m = re_access.match(line)
    result = get_result(line)

    # only if the file was accessed successfully
    if result >= 0 :
      processes[pid].add_access(m.group('file'))

  # was a file opened?
  elif line.startswith('open('):
    m = re_open.match(line)
    fd = get_result(line)

    # if the result is greater than 0, the file was opened.
    #   keep track of the file name and descriptor for use later
    if fd >= 0 :
      processes[pid].add_fd(fd, m.group('file'))
      processes[pid].add_access(m.group('file'))

      # if the O_CREAT flag was used, then the file was created
      #   if it didn't already exists, makeing this a write to the
      #   file as well
      if 'O_CREAT' in line :
        processes[pid].add_write(processes[pid].get_file(fd))
      
  # same as 'open()' above
  elif line.startswith('openat('):
    m = re_openat.match(line)
    fd = get_result(line)

    if fd >= 0 :
      processes[pid].add_fd(fd, m.group('file'))
      processes[pid].add_access(m.group('file'))
      if 'O_CREAT' in line :
        processes[pid].add_write(processes[pid].get_file(fd))

  # was a file read?
  elif line.startswith('read(') :
    m = re_read.match(line)
    fd = int(m.group('fd'))
    fname = processes[pid].get_file(fd)
    result = get_result(line)

    # if the read was a success, add the file
    #   name that is associated with the descriptor
    #   to the list of reads
    if result >= 0 :
      processes[pid].add_read(fname)

  # was a file moved?
  elif line.startswith('rename(') :
    m = re_rename.match(line)
    processes[pid].add_access(m.group('fn1'))
    processes[pid].add_access(m.group('fn2'))

    # a move is like reading the original file
    #   and writing to the new file
    if get_result(line) >= 0 :
      processes[pid].add_read(m.group('fn1'))
      processes[pid].add_write(m.group('fn2'))

  # was a pipe created?
  elif line.startswith('pipe(') :
    m = re_pipe.match(line)
    fd1 = int(m.group('fd1'))
    fd2 = int(m.group('fd2'))

    # we need to keep track of pipes being created so
    #   reads and writes to these pipes are not considered
    #   invalid during parsing
    processes[pid].add_fd(fd1, '<PIPE>')
    processes[pid].add_fd(fd2, '<PIPE>')

  # was a file descriptor duplicated
  elif line.startswith('dup2(') :
    m = re_dup2.match(line)
    fd1 = int(m.group('fd1'))
    fd2 = int(m.group('fd2'))

    # make sure we know what this duplicated file descriptor
    #   points to so reads and writes to it are valid
    processes[pid].add_fd(fd2, processes[pid].get_file(fd1))

  # similar to 'dup2' above
  elif line.startswith('dup(') :
    m = re_dup.match(line)
    fd1 = int(m.group('fd1'))
    fd2 = get_result(line)

    processes[pid].add_fd(fd2, processes[pid].get_file(fd1))

  # was fcntl used?
  elif line.startswith('fcntl(') :
    m = re_fcntl.match(line)
    if m is not None :
      command = m.group('command')
      
      # this is yet another way that a file descriptor can be 
      #   duplicated, so it must be tracked
      if command == 'F_DUPFD' :
        fd1 = int(m.group('fd1'))
        fd2 = get_result(line)
        processes[pid].add_fd(fd2, processes[pid].get_file(fd1))

  # was a file written to
  elif line.startswith('write(') :
    m = re_write.match(line)
    fd = int(m.group('fd'))
    result = get_result(line)

    # if the write was successful, track it
    if result >= 0 :
      processes[pid].add_write(processes[pid].get_file(fd))

  # was a file closed?
  elif line.startswith('close(') :
    m = re_close.match(line)
    fd = int(m.group('fd'))
    result = get_result(line)

    # remove the file descriptor from the list of open
    #   descriptors if the fille was closed
    if result >= 0 :
      processes[pid].close_fd(fd)

  # was the process cloned?
  elif line.startswith('clone(') :
    npid = get_result(line)

    # cloning a process copies many of its properties, and
    #   adds the new process to the children of the process
    #   that spawned it
    processes[npid] = processes[pid].clone(npid, pid)
    processes[pid].add_child(npid)

  # similar to 'clone()' above
  elif line.startswith('vfork(') :
    npid = get_result(line)

    processes[npid] = processes[pid].clone(npid, pid)
    processes[pid].add_child(npid)

  # was the directory changed?
  elif line.startswith('chdir(') :
    m = re_chdir.match(line)
    ch = m.group('dir')
    result = get_result(line)

    # if the directory was changed, keep track of it so 
    #   any relative paths are stored correctly
    if result == 0 :
      processes[pid].set_cwd(ch)

# parse the output of strace
def parse_file ( filename ) :
  global start, processes

  tot_lines = sum(1 for line in open(filename))

  try :
    i = 1

    # the initial working directory is the parent directory of the file
    #   being parsed
    orig_cwd = os.path.dirname(os.path.abspath(filename))

    # open the file and parse each line
    f = open(filename, 'r')
    for line in f :
      pid, line = get_process_number(line)

      # if this is the first process being parsed, mark it as such
      if start is None :
        start = pid

      # create and add any new processes to the list of processes
      if pid not in processes :
        processes[pid] = Process(pid)
        processes[pid].set_cwd(orig_cwd)

      # check if the command being parsed was completed on this line of input
      unf = re_unf.search(line)

      # if the line was not a full command, save it for the next time this process
      #   has output in the strace file
      if unf is not None :
        processes[pid].set_unfinished(unf.group('command'))

      # if the line is not unfinished parse it
      else :
        # if there was an unfinished line, then this line must be the end of
        #   that line
        if processes[pid].get_unfinished() is not None :
          res = re_res.search(line)

          # create the full line and parse it just like any other
          if res is not None : 
            line = processes[pid].get_unfinished() + res.group('command')
            parse_line(pid, line)
            processes[pid].set_unfinished(None)

        # the input line was complete, so parse it
        else :
          parse_line(pid, line)

      sys.stderr.write("Line %d/%d -> %f\r" % (i, tot_lines, i*100.0/tot_lines,))      
      i += 1
  except Exception, e :
    print "Error (line", i, "):", str(e)
    print "\t", line

  sys.stderr.write("")      

  # output the results
  output = {}
  output['start'] = start 
  output['cwd'] = orig_cwd
  output['processes'] = {}
  for key in processes.iterkeys():
    output['processes'][int(key)] = processes[key].json()
  print json.dumps(output, indent=4)

if __name__ == '__main__' :
  # require an input filename. it must be the output
  #   of an strace command
  if len(sys.argv) != 2 :
    print 'Usage:', sys.argv[0], 'input-file'
    sys.exit()

  sys.setrecursionlimit(10000)

  # parse the file
  parse_file(sys.argv[1])
