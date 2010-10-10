#! /usr/bin/env python

class Stack(list):
    def push(self, x):
        self.append(x)

    def peek(self):
        return self[-1]

    def dump(self, indent=0):
        for n, value in enumerate(self):
            print ' '*indent, '%d:' % n, repr(value)

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

def define(name, flags, definition):
    words[name] = (flags, compile(definition))

def dup(frame):
    stack.push(stack.peek())

def drop(frame):
    stack.pop()
define('DROP', 0, drop)

def binary(operator):
    def word(frame):
        stack.push(operator(stack.pop(), stack.pop()))

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

def interpret(frame):
    # execute(Frame(raw_input('> ').split()))
    word(frame)
    find(frame)

def find(frame):
    stack.push(words.get(stack.pop()))

buffer = ''

def key(frame):
    global buffer

    if not buffer:
        buffer = raw_input('? ')

    stack.push(buffer[0])
    buffer = buffer[1:]

def word(frame):
    w = ''
    while True:
        key(frame)
        k = stack.pop()
        if k.isspace() or k == '\n':
            stack.push(w)
            break
        w += k

import operator

define('R0', 0, rz)
define('RSP!', 0, rspstore)
define('BRANCH', 0, branch)
define('LIT', 0, lit)
define('DUP', 0, dup)
define('*', 0, binary(operator.mul))
define('+', 0, binary(operator.add))
define('PRINT', 0, print_)
define('INTERPRET', 0, interpret)
define('QUIT', 0, ['R0', 'RSP!', 'INTERPRET', 'BRANCH', -4])
define('FIND', 0, find)
define('KEY', 0, key)
define('WORD', 0, word)

def nop(frame):
    pass

define(':', 0, nop)
define(';', 0, nop)

def getenv(frame):
    import os
    stack.push(os.getenv(stack.pop()))
define('GETENV', 0, getenv)

def random_(frame):
    import random
    stack.push(random.randint(0, 1000))
define('RANDOM', 0, random_)

def execute(frame):
    indent = 0
    print 'entering frame', id(frame)

    while True:
        frame.dump(indent)

        try:
            instruction = frame.next()
        except IndexError:
            print ' '*indent, 'exiting frame', id(frame)
            indent -= 2
            try:
                frame = return_stack.pop()
            except IndexError:
                stack.dump(indent)
                return

            continue

        if callable(instruction):
            instruction(frame)
            stack.dump(indent)
        else:
            return_stack.push(frame)
            frame = Frame(instruction)
            indent += 2
            print ' '*indent, 'entering frame', id(frame)

define('DOUBLE', 0, ['DUP', '+'])
define('DOUBLE2', 0, ['LIT', 2, '*'])

# execute(Frame(compile(['LIT', 10, 'DOUBLE', 'PRINT'])))
import sys
execute(Frame(compile(sys.argv[1:] if len(sys.argv) > 1 else ['QUIT'])))
