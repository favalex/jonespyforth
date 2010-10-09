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

        self.position +=1

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

words['DOUBLE'] = ['DUP', '+']
words['DOUBLE2'] = ['LIT', 2, '*']

def lit(frame):
    stack.push(frame.get_current_instruction())
    frame.next()

def print_(frame):
    print stack.pop()

import operator

words['LIT'] = lit
words['DUP'] = dup
words['*'] = binary(operator.mul)
words['+'] = binary(operator.add)
words['PRINT'] = print_

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

execute(Frame(['LIT', 10, 'DOUBLE', 'PRINT']))
