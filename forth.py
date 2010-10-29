#! /usr/bin/env python

import sys

class Stack(list):
    def push(self, x):
        self.append(x)

    def peek(self):
        return self[-1]

    def set_top(self, top):
        for i in range(len(self)-1, top-1, -1):
            del self[i]

    def dump(self, indent=0):
        top = len(self) - 1
        for n, value in enumerate(self):
            print ' '*indent, '%d:' % (top-n), to_string(value)

def inverse(s):
    return '\033[4m' + s + '\033[24m'

def to_string(x, level=0):
    if level > 5:
        return '...'

    try:
        return x.__name__
    except AttributeError:
        if isinstance(x, list):
            return '[' + ', '.join(map(lambda y: to_string(y, level+1), x)) + ']'
        else:
            return repr(x)

class Frame(object):
    def __init__(self, definition):
        self.definition = definition
        self.position = 0

    def dump(self, indent=0):
        if self.position == len(self.definition):
            return

        print ' '*indent,
        for n, word in enumerate(self.definition):
            word = to_string(word)

            if n == self.position:
                print inverse(word),
            else:
                print word,
        print

    def get_current_instruction(self):
        return self.definition[self.position]

    def next(self):
        instruction = self.get_current_instruction()

        self.position += 1

        return instruction

stack = Stack()
return_stack = Stack()

words = {}

class List(list):
    def __init__(self):
        self.flags = 0

    def __setitem__(self, i, x):
        if i >= len(self):
            self.extend([None]*(i - len(self) + 1))

        super(List, self).__setitem__(i, x)

def compile(definition):
    if callable(definition):
        return definition
    else:
        l = List()
        l.extend([words[n] if isinstance(n, basestring) else n for n in definition])
        return l

# flags
IMMED = 0x80

def define(name, flags, definition):
    compiled = compile(definition)
    compiled.__name__ = name
    compiled.flags = flags
    words[name] = compiled

class Var(object):
    def __init__(self, name):
        self.__name__ = name

    def __repr__(self):
        return 'Variable ' + self.__name__

    def __call__(self, frame):
        stack.push(self)

    def store(self, value):
        vars[self.__name__] = value

    def fetch(self):
        value = vars[self.__name__]
        if isinstance(value, Ref):
            value = Ref(value.memory, value.address)
        return value

class Ref(object):
    def __init__(self, memory, address=0):
        self.memory = memory
        self.address = address
        self.__name__ = 'Ref'

    def __repr__(self):
        return 'Ref at address %s' % self.address

    def __call__(self, frame):
        stack.push(self)

    def __sub__(self, other):
        assert isinstance(other, int) or (self.memory is other.memory)
        if isinstance(other, int):
            return self.address - other
        else:
            return self.address - other.address

    def __add__(self, other):
        assert isinstance(other, int)
        return Ref(self.memory, self.address + other)

    def __iand__(self, other):
        assert isinstance(other, int)
        return Ref(self.memory, self.address & other)

    def store(self, value):
        self.memory[self.address] = value

    def fetch(self):
        return self.memory[self.address]

    def copy(self):
        return self.memory[:self.address]

vars = {}
def defvar(name, value):
    if isinstance(value, list):
        value = Ref(value)

    vars[name] = value
    define(name, 0, Var(name))

def tdfa(frame):
    stack.push(Ref(stack.pop()))
define('>DFA', 0, tdfa)

def tffa(frame):
    stack.push(stack.pop().flags)
define('>FFA', 0, tffa)

def execute_(frame):
    execute(Frame([stack.pop()]))
define('EXECUTE', 0, execute_)

defvar('STATE', 0)
defvar('BASE', 10)
defvar('HERE', [None]*500)
defvar('LATEST', None)
defvar('S0', 0)
defvar('DEBUG', False)

def dump_here():
    print 'HERE',
    here = vars['HERE']
    for a in range(here.address):
        x = here.memory[a]
        if not x is None:
            print to_string(x),
        else:
            break
    print

def dspfetch(frame):
    stack.push(len(stack)-1)
define('DSP@', 0, dspfetch)

def dspstore(frame):
    stack.set_top(stack.pop())

define('DSP!', 0, dspstore)

def rspfetch(frame):
    stack.push(len(return_stack)-1)
define('RSP@', 0, rspfetch)

def rspstore(frame):
    return_stack.set_top(stack.pop())
define('RSP!', 0, rspstore)

def dup(frame):
    stack.push(stack.peek())

def qdup(frame):
    if stack.peek() != 0:
        stack.push(stack.pop())
define('?DUP', 0, qdup)

def over(frame):
    stack.push(stack[-2])
define('OVER', 0, over)

def rot(frame):
    # a b c -> b c a
    c = stack.pop()
    b = stack.pop()
    a = stack.pop()
    stack.push(b)
    stack.push(c)
    stack.push(a)
define('ROT', 0, rot)

def nrot(frame):
    # a b c -> c a b
    c = stack.pop()
    b = stack.pop()
    a = stack.pop()
    stack.push(c)
    stack.push(a)
    stack.push(b)
define('-ROT', 0, nrot)

def twodrop(frame):
    stack.pop()
    stack.pop()
define('2DROP', 0, twodrop)

def twodup(frame):
    stack.push(stack[-2])
    stack.push(stack[-2])
define('2DUP', 0, twodup)

def swap(frame):
    a = stack.pop()
    b = stack.pop()
    stack.push(a)
    stack.push(b)

def drop(frame):
    stack.pop()
define('DROP', 0, drop)

def fetch(frame):
    stack.push(stack.pop().fetch())
define('@', 0, fetch)
define('C@', 0, fetch)

def store(frame):
    var = stack.pop()
    var.store(stack.pop())
define('!', 0, store)
define('C!', 0, store)

def addstore(frame):
    var = stack.pop()
    var.store(var.fetch() + stack.pop())
define('+!', 0, addstore)

def substore(frame):
    var = stack.pop()
    var.store(var.fetch() - stack.pop())
define('-!', 0, substore)

def comma(frame):
    here = vars['HERE']
    here.store(stack.pop())
    here.address += 1
define(',', 0, comma)

def lbrac(frame):
    vars['STATE'] = 0
define('[', IMMED, lbrac)

def rbrac(frame):
    vars['STATE'] = 1
define(']', 0, rbrac)

def create(frame):
    name = stack.pop()
    latest = List()
    latest.__name__ = name
    words[name] = latest
    vars['HERE'] = Ref(latest)
    vars['LATEST'] = latest
define('CREATE', 0, create)

def immediate(frame):
    vars['LATEST'].flags ^= IMMED
define('IMMEDIATE', IMMED, immediate)

def divmod_(frame):
    x = stack.pop()
    div, mod = divmod(stack.pop(), x)
    stack.push(mod)
    stack.push(div)

def tor(frame):
    return_stack.push(stack.pop())
define('>R', 0, tor)

def fromr(frame):
    stack.push(return_stack.pop())
define('R>', 0, fromr)

def rdrop(frame):
    return_stack.pop()
define('RDROP', 0, rdrop)

def binary(operator):
    def word(frame):
        x = stack.pop()
        stack.push(operator(stack.pop(), x))

    word.__name__ = operator.__name__
    return word

def boolean(operator):
    def word(frame):
        x = stack.pop()
        stack.push(1 if operator(stack.pop(), x) else 0)

    word.__name__ = operator.__name__
    return word

def zboolean(operator):
    def word(frame):
        stack.push(1 if operator(stack.pop(), 0) else 0)

    word.__name__ = 'z' + operator.__name__
    return word

def rspstore(frame):
    global return_stack
    old_stack = return_stack
    return_stack = Stack()
    return_stack.extend(old_stack[:stack.pop()])

def rspfetch(frame):
    stack.push(len(return_stack))

def rz(frame):
    stack.push(0)

def branch(frame):
    n = frame.get_current_instruction()
    frame.position += n

def lit(frame):
    stack.push(frame.next())

def print_(frame):
    print stack.pop()

def emit(frame):
    sys.stdout.write(stack.pop())
    sys.stdout.flush()
define('EMIT', 0, emit)

def char(frame):
    word(frame)
    stack.push(stack.pop()[0])
define('CHAR', 0, char)

def interpret(frame):
    word(frame)
    w = stack.peek()
    find(frame)
    definition = stack.pop()
    if definition is None:
        try:
            n = int(w, vars['BASE'])
        except ValueError:
            print line, 'PARSE ERROR inside', to_string(vars['LATEST']), repr(w)
            # import pprint; pprint.pprint(words)
            import sys; sys.exit(1)
            return
        else:
            if vars['STATE'] == 0:
                execute(Frame([lit, n]))
            else:
                stack.push(n)
                comma(frame)
    elif definition.flags & IMMED or vars['STATE'] == 0:
        execute(Frame([definition]))
    else:
        stack.push(definition)
        comma(frame)

def find(frame):
    stack.push(words.get(stack.pop()))

buffer = None

def key(frame):
    global buffer, input_stream, line

    if buffer is None:
        if input_stream.isatty():
            stack.dump()
            sys.stdout.write('[%d] ? ' % vars['STATE'])
            sys.stdout.flush()
        buffer = input_stream.readline()
        line += 1

        if buffer == '': # EOF
            if input_stream == sys.stdin:
                print 'bye'
                sys.exit(0)

            input_stream = sys.stdin

    if len(buffer) > 0:
        stack.push(buffer[0])
        buffer = buffer[1:]
    else:
        stack.push('\n')
        buffer = None

line = 0

def word(frame):
    w = ''
    inside_comment = False
    while True:
        key(frame)
        k = stack.pop()

        if inside_comment:
            if k == '\n':
                inside_comment = False
            continue

        if w == '' and k == '\\':
            inside_comment = True
            continue

        if k.isspace() or k == '\n':
            if w != '':
                stack.push(w)
                break
            else:
                continue

        w += k

import operator

define('R0', 0, rz)
define('RSP!', 0, rspstore)
define('BRANCH', 0, branch)

def zbranch(frame):
    n = frame.next()
    if stack.pop() == 0:
        frame.position += n-1
define('0BRANCH', 0, zbranch)

define('LIT', 0, lit)
define('DUP', 0, dup)
define('SWAP', 0, swap)
define('/MOD', 0, divmod_)
define('*', 0, binary(operator.mul))
define('+', 0, binary(operator.add))
define('-', 0, binary(operator.sub))
define('AND', 0, binary(operator.iand))
define('OR', 0, binary(operator.ior))
define('XOR', 0, binary(operator.ixor))
define('=', 0, boolean(operator.eq))
define('<>', 0, boolean(operator.ne))
define('<', 0, boolean(operator.lt))
define('>', 0, boolean(operator.gt))
define('>=', 0, boolean(operator.ge))
define('<=', 0, boolean(operator.le))
define('0=', 0, zboolean(operator.eq))
define('0<>', 0, zboolean(operator.ne))
define('0<', 0, zboolean(operator.lt))
define('0>', 0, zboolean(operator.gt))
define('0>=', 0, zboolean(operator.ge))
define('0<=', 0, zboolean(operator.le))
define('PRINT', 0, print_)
define('INTERPRET', 0, interpret)
define('QUIT', 0, ['R0', 'RSP!', 'INTERPRET', 'BRANCH', -4])
define('FIND', 0, find)
define('KEY', 0, key)
define('WORD', 0, word)

def incr(frame):
    stack.push(1 + stack.pop())
define('1+', 0, incr)
define('4+', 0, incr)

def decr(frame):
    stack.push(stack.pop() - 1)
define('1-', 0, decr)
define('4-', 0, decr)

def invert(frame):
    stack.push(~stack.pop())
define('INVERT', 0, invert)

def nop(frame):
    pass

define(':', 0, ['WORD', 'CREATE', ']'])
define(';', IMMED, ['['])
def tick(frame):
    stack.push(frame.next())
define('\'', 0, tick)
define('\'\'', 0, ['WORD', 'FIND', 'DROP'])
define('>CFA', 0, nop)

define('DOCOL', 0, nop)

def litstring(frame):
    n = frame.next()
    s = frame.next()
    stack.push(s)
    stack.push(n)
define('LITSTRING', 0, litstring)

def tell(frame):
    n = stack.pop()
    s = stack.pop()
    sys.stdout.write(s)
define('TELL', 0, tell)

def getenv(frame):
    import os
    stack.push(os.getenv(stack.pop()))
define('GETENV', 0, getenv)

def random_(frame):
    import random
    stack.push(random.randint(0, 1000))
define('RANDOM', 0, random_)

def pdb_(frame):
    import pdb
    pdb.set_trace()
define('PDB', 0, pdb_)

def execute(frame):
    indent = 0
    if vars['DEBUG']:
        print 'entering frame', id(frame)

    while True:
        if vars['DEBUG']:
            frame.dump(indent)

        try:
            instruction = frame.next()
        except IndexError:
            if vars['DEBUG']:
                print ' '*indent, 'exiting frame', id(frame)
            indent -= 2
            try:
                frame = return_stack.pop()
            except IndexError:
                if vars['DEBUG']:
                    stack.dump(indent)
                return

            continue

        if callable(instruction):
            instruction(frame)
            if vars['DEBUG']:
                stack.dump(indent)
        elif isinstance(instruction, list):
            return_stack.push(frame)
            frame = Frame(instruction)
            indent += 2
            if vars['DEBUG']:
                print ' '*indent, 'entering frame', id(frame)
        else: # unquoted literal
            stack.push(instruction)

define('DOUBLE', 0, ['DUP', '+'])
define('DOUBLE2', 0, ['LIT', 2, '*'])

def exit(frame):
    pass
define('EXIT', 0, exit)

# execute(Frame(compile(['LIT', 10, 'DOUBLE', 'PRINT'])))
args = sys.argv[1:]
if len(args) > 0 and args[0] == '-f':
    input_stream = open(args[1], 'r')
    args = args[2:]
    while True:
        try:
            execute(Frame(compile(['QUIT'])))
        except Exception as e:
            print line, 'inside', to_string(vars['LATEST']), e
            import pdb; pdb.post_mortem()
else:
    input_stream = sys.stdin
    execute(Frame(compile(args if len(args) > 0 else ['QUIT'])))
