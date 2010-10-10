#! /usr/bin/env python

class Stack(list):
    def push(self, x):
        self.append(x)

    def peek(self):
        return self[-1]

    def dump(self, indent=0):
        for n, value in enumerate(self):
            print ' '*indent, '%d:' % n, value

def inverse(s):
    return '\033[7m' + s + '\033[27m'

class Frame(object):
    def __init__(self, definition):
        self.definition = definition
        self.position = 0

    def dump(self, indent=0):
        if self.position == len(self.definition):
            return

        print ' '*indent,
        for n, word in enumerate(self.definition):
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

words = {}

stack = Stack()
return_stack = Stack()

def dup(frame):
    stack.push(stack.peek())

def binary(operator):
    def word(frame):
        stack.push(operator(stack.pop(), stack.pop()))

    return word

def rspstore(frame):
    global return_stack
    return_stack = return_stack[:stack.pop()]

def rspfetch(frame):
    stack.push(len(return_stack))

def rz(frame):
    stack.push(0)

def branch(frame):
    n = frame.get_current_instruction()
    frame.position += n

words['DOUBLE'] = ['DUP', '+']
words['DOUBLE2'] = ['LIT', 2, '*']

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

words['R0'] = rz
words['RSP!'] = rspstore
words['BRANCH'] = branch
words['LIT'] = lit
words['DUP'] = dup
words['*'] = binary(operator.mul)
words['+'] = binary(operator.add)
words['PRINT'] = print_
words['INTERPRET'] = interpret
words['QUIT'] = ['R0', 'RSP!', 'INTERPRET', 'BRANCH', -4]
words['FIND'] = find
words['KEY'] = key
words['WORD'] = word

def nop(frame):
    pass

words[':'] = nop
words[';'] = nop

def getenv(frame):
    import os
    stack.push(os.getenv(stack.pop()))

words['GETENV'] = getenv

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

        definition = words[instruction]

        if callable(definition):
            definition(frame)
            stack.dump(indent)
        else:
            return_stack.push(frame)
            frame = Frame(definition)
            indent += 2
            print ' '*indent, 'entering frame', id(frame)

# execute(Frame(['LIT', 10, 'DOUBLE', 'PRINT']))
execute(Frame(['QUIT']))
