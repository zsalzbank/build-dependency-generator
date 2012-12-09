import os
import json

class Process :
  def __init__ (self, pid) :
    self.executable = ''
    self.pid = pid
    self.fds = {0: '<stdin>', 1: '<stdout>', 2: '<stderr>'}
    self.args = []
    self.children = []
    self.accesses = []
    self.reads = []
    self.writes = []
    self.unfinished = None
    self.parent = None
    self.cwd = None

  def clone(self, p, parent) :
    p = Process(p)

    p.set_cwd(self.cwd)
    p.set_executable(self.executable)
    for fd in self.fds :
      p.add_fd(fd, self.fds[fd])

    p.set_parent(parent)

    return p

  def add_arg(self, a) :
    self.args.append(a)

  def relevant(self, f) :
    fo = self.getpath(f)
    return fo

  def getpath(self, p) :
    if p[0] == '/' :
      return os.path.abspath(p)
    else :
      return os.path.abspath(os.path.join(self.cwd, p))

  def set_cwd(self, c) :
    self.cwd = self.getpath(c)

  def get_cwd(self) :
    return self.cwd

  def set_executable (self, e) :
    self.executable = e

  def set_parent(self, p) :
    self.parent = p

  def add_child (self, c) :
    self.children.append(c)

  def add_access (self, a) :
    a = self.relevant(a)
    if a is not None :
      self.accesses.append(a)

  def add_fd (self, fd, f) :
    self.fds[fd] = self.getpath(f)

  def close_fd (self, fd) :
    del self.fds[fd]

  def get_file (self, fd) :
    if fd in self.fds :
      return self.fds[fd]
    else :
      return None

  def set_unfinished (self, u) :
    self.unfinished = u

  def get_unfinished (self) :
    return self.unfinished

  def add_write (self, w) :
    if w[0] != '<' and w[len(w)-1] != '>' :
      w = self.relevant(w)
      if w is not None :
        self.writes.append(w)

  def add_read (self, r) :
    if r[0] != '<' and r[len(r)-1] != '>' :
      rp = self.relevant(r)
      if rp is not None :
        self.reads.append(rp)

  def json (self) :
    obj = {}
    obj['executable'] = self.executable
    obj['parent'] = self.parent
    obj['children'] = self.children
    obj['reads'] = list(set(self.reads))
    obj['writes'] = list(set(self.writes))
    obj['args'] = self.args

    return obj

  def __repr__ (self) :
    rstr = "\n\tExecutable: " + self.executable
    rstr += "\n\tArgs: " + str(self.args)
    rstr += "\n\tFDs: " + str(self.fds)
    rstr += "\n\tParent: " + str(self.parent)
    rstr += "\n\tChildren: " + str(self.children)
    rstr += "\n\tAccesses: " + str(list(set(self.accesses)))
    rstr += "\n\tUnfinished: " + str(self.unfinished)
    rstr += "\n\tReads: " + str(list(set(self.reads)))
    rstr += "\n\tWrites: " + str(list(set(self.writes)))

    return rstr + "\n"
