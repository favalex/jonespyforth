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
            print ' '*indent, '%d:' % (top-n), repr(value)

def inverse(s):
    return '\033[4m' + s + '\033[24m'

def to_string(x):
    if isinstance(x, list):
        return '[' + ', '.join(map(to_string, x)) + ']'
    elif callable(x):
        return x.__name__
    else:
        return str(x)

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

def compile(definition):
    if callable(definition):
        return definition
    else:
        return [words[n][1] if isinstance(n, basestring) else n for n in definition]

# flags
IMMED = 0x80

def define(name, flags, definition):
    words[name] = (flags, compile(definition))

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
        return vars[self.__name__]

class Ref(object):
    def __init__(self, memory):
        self.memory = memory
        self.address = 0
        self.__name__ = 'Ref'

    def __repr__(self):
        return 'Ref at address %s' % self.address

    def __call__(self, frame):
        stack.push(self)

    def store(self, value):
        self.memory[self.address] = value

    def fetch(self):
        return self.memory[self.address]

    def copy(self):
        return self.memory[:self.address]

vars = {}
def defvar(name, value):
    if isinstance(value, list):
        ref = Ref(value)
        vars[name] = ref
        define(name, 0, ref)
    else:
        vars[name] = value
        define(name, 0, Var(name))

defvar('STATE', 0)
defvar('BASE', 10)
defvar('HERE', [None]*100)
defvar('LATEST', None)
defvar('S0', 0)
defvar('DEBUG', False)

def dspfetch(frame):
    stack.push(len(stack)-1)
define('DSP@', 0, dspfetch)

def dspstore(frame):
    stack.set_top(stack.pop())

define('DSP!', 0, dspstore)

def dup(frame):
    stack.push(stack.peek())

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

def store(frame):
    var = stack.pop()
    var.store(stack.pop())
define('!', 0, store)

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
    vars['HERE'].address = 0
    vars['LATEST'] = stack.pop()
    words[vars['LATEST']] = (0, [])
define('CREATE', 0, create)

def finish(frame):
    flags, definition = words[vars['LATEST']]
    words[vars['LATEST']] = (flags, vars['HERE'].copy())
define('FINISH', 0, finish)

def immediate(frame):
    flags, definition = words[vars['LATEST']]
    flags ^= IMMED
    words[vars['LATEST']] = (flags, definition)
define('IMMEDIATE', IMMED, immediate)

def divmod_(frame):
    x = stack.pop()
    div, mod = divmod(stack.pop(), x)
    stack.push(mod)
    stack.push(div)

def binary(operator):
    def word(frame):
        x = stack.pop()
        stack.push(operator(stack.pop(), x))

    word.__name__ = operator.__name__
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
    stack.push(frame.get_current_instruction())
    frame.next()

def print_(frame):
    print stack.pop()

def emit(frame):
    sys.stdout.write(stack.pop())
    sys.stdout.flush()
define('EMIT', 0, emit)

def zequ(frame):
    stack.push(1 if stack.pop() == 0 else 0)
define('0=', 0, zequ)

def char(frame):
    word(frame)
    stack.push(stack.pop()[0])
define('CHAR', 0, char)

def interpret(frame):
    word(frame)
    w = stack.peek()
    find(frame)
    if stack.peek() is None:
        stack.pop()
        try:
            n = int(w, vars['BASE'])
        except ValueError:
            print line, 'PARSE ERROR', repr(w)
            # import pprint; pprint.pprint(words)
            import sys; sys.exit(1)
            return
        else:
            if vars['STATE'] == 0:
                execute(Frame([lit, n]))
            else:
                stack.push(n)
                comma(frame)
    else:
        flags = stack.pop()
        if flags & IMMED or vars['STATE'] == 0:
            definition = stack.pop()
            execute(Frame([definition]))
        else:
            comma(frame)

def find(frame):
    flags_definition = words.get(stack.pop())
    if flags_definition:
        flags, definition = flags_definition
        stack.push(definition)
        stack.push(flags)
    else:
        stack.push(None)

buffer = None

def key(frame):
    global buffer, input_stream

    if buffer is None:
        if input_stream.isatty():
            sys.stdout.write('? ')
            sys.stdout.flush()
        buffer = input_stream.readline()

        if buffer == '': # EOF
            if input_stream == sys.stdin:
                print 'bye'
                sys.exit(0)

            input_stream = sys.stdin
            execute(Frame(['QUIT']))

    if len(buffer) > 0:
        stack.push(buffer[0])
        buffer = buffer[1:]
    else:
        stack.push('\n')
        buffer = None

line = 1

def word(frame):
    global line
    w = ''
    inside_comment = False
    while True:
        key(frame)
        k = stack.pop()

        if inside_comment:
            if k == '\n':
                line += 1
                inside_comment = False
            continue

        if w == '' and k == '\\':
            inside_comment = True
            continue

        if k.isspace() or k == '\n':
            if k == '\n':
                line += 1

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
    n = frame.get_current_instruction()
    if stack.pop() == 0:
        frame.position += n
define('0BRANCH', 0, zbranch)

define('LIT', 0, lit)
define('DUP', 0, dup)
define('SWAP', 0, swap)
define('/MOD', 0, divmod_)
define('*', 0, binary(operator.mul))
define('+', 0, binary(operator.add))
define('-', 0, binary(operator.sub))
define('PRINT', 0, print_)
define('INTERPRET', 0, interpret)
define('QUIT', 0, ['R0', 'RSP!', 'INTERPRET', 'BRANCH', -4])
define('FIND', 0, find)
define('KEY', 0, key)
define('WORD', 0, word)

def nop(frame):
    pass

define(':', 0, ['WORD', 'CREATE', ']'])
define(';', IMMED, ['FINISH', '['])
define('\'', 0, ['WORD', 'FIND', 'DROP'])

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

# execute(Frame(compile(['LIT', 10, 'DOUBLE', 'PRINT'])))
args = sys.argv[1:]
if len(args) > 0 and args[0] == '-f':
    input_stream = open(args[1], 'r')
    args = args[2:]
    execute(Frame(compile(['QUIT'])))
else:
    input_stream = sys.stdin
    execute(Frame(compile(args if len(args) > 0 else ['QUIT'])))
