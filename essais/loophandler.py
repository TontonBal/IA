import fileinput
import sys
import os
from subprocess import Popen, PIPE, STDOUT


p = Popen(['rasa', 'shell'], stdout=PIPE, stdin=PIPE, stderr=PIPE)


for outline in p.stdout:
    print(outline.rstrip())
    outline = p.stdout