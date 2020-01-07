#!/usr/bin/env python

# Simulator for RISC240
# Written by Deanyone Su <deanyons@andrew.cmu.edu>
# Maintained by 18-240 Course Staff <ece240-staff@lists.andrew.cmu.edu>
# Adapted from python script by Neil Ryan <nryan@andrew.cmu.edu>
# Adapted from perl script by Paul Kennedy (version 1.21)
# Last updated 4/29/2019
#
# In Progress:
#   -It would be prudent to only get a random int when we lookup a memory
#    location, i.e. if mem location not defined in memory, give back randint()
#   -It would be cool if we could use labels for mem[]? commands
# Known Bugs:
# If any additional bugs are found, contact nryan@andrew.cmu.edu
from optparse import OptionParser
from getpass import getuser
from datetime import datetime
import sys
from re import match, IGNORECASE
from random import randint
import signal
import readline
import re

# supress .pyc file - speedup doesn't justify cleanup
sys.dont_write_bytecode = True;

# Globals
version = "3.0" # RISCV

transcript = ""; # holds transcript of every line printed

randomize_memory = True; # flag that randomizes the memory
run_only = False; # flag that just does "run, quit"
piping = False; # flag that reads list file from STDIN (pipe from as240)
transcript_fname = ""; # filename of transcript file, provided with -t flag
check_file = ""; # file to check state against in grading mode
quit_after_sim_file = False; # if -g is set and a sim file is provided,
                             # we quit after running the sim file

# Tab completion for user input
commands = ['labels', 'lsbrk', 'quit', 'exit', 'help', 'run', 'reset',
            'step', 'save', 'ustep', 'clear', 'load', 'check', 'break',
            'mem[']
def complete(text, state):
    for cmd in commands:
        if cmd.startswith(text):
            if not state:
                return cmd
            else:
                state -= 1

readline.parse_and_bind("tab: complete");
readline.set_completer(complete);
# end of tab completion

# Signal handler for SIGINTs
def sigint_handler(signal, frame):
   print("\nUnexpected input, did you forget to quit?");
   exit();

signal.signal(signal.SIGINT, sigint_handler);


wide_header = "Cycle STATE PC   IR   ZNCV MAR  MDR  R0   R1   R2   R3   R4   R5   R6   R7";

# print_per is a variable which determines when the simulator prints the state
# to the console.
# 'i' prints the state on every instruction. '
# 'u' prints the state on every microinstruction. '
# 'q' is for 'quiet'; it does not ever print
print_per = "i";

# first_print controls whether the first line is printed during a run
first_print = False;

cycle_num = 0; # global cycle counter

# a hash of microinstruction binary opcodes
uinst_str_keys = {
# Microcode operations (i.e., FSM states)
   'FETCH'  : '000_1001', # unknown, currently placeholders
   'FETCH1' : '000_1010',
   'FETCH2' : '000_1011',
   'DECODE' : '000_0111',
   'STOP'   : '111_1111',
   'STOP1'  : '100_0001',

# Reg-Reg (R-type) operations:
# ADD, AND, MV, NOT, OR, SLL, SLT, SRA, SRL, SUB, XOR
   'ADD'    : '000_0000',
   'AND'    : '100_1000',
   'MV'     : '001_0000',
   'NOT'    : '100_0000',
   'OR'     : '101_0000',
   'SLL'    : '110_0000',
   'SLT'    : '010_1000',
   'SLT1'   : '010_1101',
   'SRA'    : '111_1000',
   'SRL'    : '111_0000',
   'SUB'    : '000_1000',
   'XOR'    : '101_1000',

# Immediate (I-type) operations:
# ADDI/LI, LW, SLLI, SLTI, SRAI, SRLI
   'ADDI'   : '001_1000',
   'ADDI1'  : '001_1001',
   'ADDI2'  : '001_1010',
   'LW'     : '001_0100',
   'LW1'    : '001_0101',
   'LW2'    : '001_0110',
   'LW3'    : '001_0111',
   'LW4'    : '001_1011',
   'SLLI'   : '110_0001',
   'SLLI1'  : '110_0010',
   'SLLI2'  : '110_0011',
   'SLTI'   : '010_1001',
   'SLTI1'  : '010_1010',
   'SLTI2'  : '010_1011',
   'SLTI3'  : '010_1100',
   'SRAI'   : '111_1001',
   'SRAI1'  : '111_1010',
   'SRAI2'  : '111_1011',
   'SRLI'   : '111_0001',
   'SRLI1'  : '111_0010',
   'SRLI2'  : '111_0011',

# Store (S-type) operations:
# SW
   'SW'     : '001_1100',
   'SW1'    : '001_1101',
   'SW2'    : '001_1110',
   'SW3'    : '001_1111',
   'SW4'    : '010_0000',

# Branch (B-type) operations:
# BRA, BRC, BRN, BRNZ, BRV, BRZ
   'BRA'    : '111_1100',
   'BRA1'   : '111_1101',
   'BRA2'   : '111_1110',
   'BRC'    : '101_0100',
   'BRC1'   : '101_0101',
   'BRC2'   : '101_0110',
   'BRC3'   : '101_0111',
   'BRN'    : '100_1100',
   'BRN1'   : '100_1101',
   'BRN2'   : '100_1110',
   'BRN3'   : '100_1111',
   'BRNZ'   : '110_1100',
   'BRNZ1'  : '110_1101',
   'BRNZ2'  : '110_1110',
   'BRNZ3'  : '110_1111',
   'BRV'    : '101_1100',
   'BRV1'   : '101_1101',
   'BRV2'   : '101_1110',
   'BRV3'   : '101_1111',
   'BRZ'    : '110_0100',
   'BRZ1'   : '110_0101',
   'BRZ2'   : '110_0110',
   'BRZ3'   : '110_0111',
};

# we need to do a reverse lookup of the bits in IR when figuring out
# what control state to go into when in the DECODE state
uinst_bin_keys = dict((v, k) for k, v in uinst_str_keys.items());

# hash: keys are addresses in canonical hex format (uppercase 4 digit)
memory = {};

# all the regs in the processor
state = {
   'PC' : '0000',
   'SP' : '0000',
   'IR' : '0000',
   'MAR' : '0000',
   'MDR' : '0000',
   'regFile' : ['0000',
                '0000',
                '0000',
                '0000',
                '0000',
                '0000',
                '0000',
                '0000'],
   'Z' : '0',
   'N' : '0',
   'C' : '0',
   'V' : '0',
   'STATE' : 'FETCH',
};

# keys are label strings, values are addresses
labels = {};

# keys are addresses, value is always 1
breakpoints = {};

# keys are strings indicating menu option
# values are regex's which match the input for the corresponding menu option
menu = {
   'quit'    : '^\s*(q(uit)?|exit)\s*$',
   'help'    : '^\s*(\?|h(elp)?)\s*$',                         # ? ; h ; help
   'reset'   : '^\s*reset\s*$',
   'run'     : '^\s*r(un)?\s*(\d*)\s*([qiu])?\s*$',           # run ; run 5u ; r 6i
   'step'    : '^\s*s(tep)?$',                                 # s ; step
   'ustep'   : '^\s*u(step)?\s*$',                             # u ; ustep
   'break'   : '^\s*break\s+(\'?\w+\'?|\$[0-9a-f]{1,4})\s*$',    # break [addr/label]
   'clear'   : '^\s*clear\s+(\*|\'?\w+\'?|\$[0-9a-f]{1,4})\s*$', # clear [addr/label/*]
   'lsbrk'   : '^\s*lsbrk\s*$',
   'load'    : '^\s*load\s+([\w\.]+)\s*$',                     # load [file]
   'save'    : '^\s*save\s+([\w\.]+)\s*$',                     # save [file]
   'set_reg' : '^\s*(\*|pc|sp|ir|mar|mdr|z|c|v|n|r[0-7])\s*=\s*([0-9a-f]{1,4})$',
   'get_reg' : '^\s*(\*|pc|sp|ir|mar|mdr|z|c|v|n|state|r[0-7*])\s*\?$',
   'set_mem' : '^\s*m(em)?\[([0-9a-f]{1,4})\]\s*=\s*([0-9a-f]{1,4})$',   # m[10] = 0a10
   'get_mem' : '^\s*m(em)?\[([0-9a-f]{1,4})(:([0-9a-f]{1,4}))?\]\s*\?$', # m[50]? ; mem[10:20]?
   'check' : '^\s*check\s+([\w\.]+)\s*$', # check [state filename]
   'labels' : '^\s*labels\s*$',
};

# filehandles
list_fh = None;
sim_fh = None;

list_lines = [];

# Next state logic based on current state. Empty strings are states
# dependent on flags
# [alu_op, srcA, srcB, dest, load_CC, re, we, next_control_state]
nextState_logic = {

   'FETCH'  : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH1'],
   'FETCH1' : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'MEM_RD',   'NO_WR',    'FETCH2'],
   'FETCH2' : ['F_A',        'MDR', 'x',    'IR',    'NO_LOAD',    'NO_RD',    'NO_WR',    'DECODE'],

   'DECODE' : ['x',          'x',   'x',    'NONE',  'NO_LOAD',    'NO_RD',    'NO_WR',    ""], #IR state

   'STOP'   : ['x',          'x',   'x',    'NONE',  'NO_LOAD',    'NO_RD',    'NO_WR',    'STOP1'],
   'STOP1'  : ['x',          'x',   'x',    'NONE',  'NO_LOAD',    'NO_RD',    'NO_WR',    'STOP1'],

   'ADD'    : ['F_A_PLUS_B', 'REG', 'REG',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],
   'AND'    : ['F_A_AND_B',  'REG', 'REG',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],
   'MV'     : ['F_A',        'REG',   'x',  'REG',   'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],
   'NOT'    : ['F_A_NOT',    'REG',   'x',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],
   'OR'     : ['F_A_OR_B',   'REG', 'REG',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],
   'SLL'    : ['F_A_SHL',    'REG', 'REG',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],
   'SLT'    : ['F_A_MINUS_B','REG', 'REG',  'NONE',  'LOAD_CC',    'NO_RD',    'NO_WR',    'SLT1'],
   'SLT1'   : ['F_A_LT_B',   'REG', 'REG',  'REG',   'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],
   'SRA'    : ['F_A_ASHR',   'REG', 'REG',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],
   'SRL'    : ['F_A_LSHR',   'REG', 'REG',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],
   'SUB'    : ['F_A_MINUS_B','REG', 'REG',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],
   'XOR'    : ['F_A_XOR_B',  'REG', 'REG',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],

   'ADDI'   : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'ADDI1'],
   'ADDI1'  : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'MEM_RD',   'NO_WR',    'ADDI2'],
   'ADDI2'  : ['F_A_PLUS_B', 'REG', 'MDR',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],

   'LW'     : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'LW1'],
   'LW1'    : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'MEM_RD',   'NO_WR',    'LW2'],
   'LW2'    : ['F_A_PLUS_B', 'REG', 'MDR',  'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'LW3'],
   'LW3'    : ['x',          'x',   'x',    'x',     'NO_LOAD',    'MEM_RD',   'NO_WR',    'LW4'],
   'LW4'    : ['F_A',        'MDR', 'x',    'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],

   'SLLI'   : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'SLLI1'],
   'SLLI1'  : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'MEM_RD',   'NO_WR',    'SLLI2'],
   'SLLI2'  : ['F_A_SHL',    'REG', 'MDR',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],

   'SLTI'   : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'SLTI1'],
   'SLTI1'  : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'MEM_RD',   'NO_WR',    'SLTI2'],
   'SLTI2'  : ['F_A_MINUS_B','REG', 'MDR',  'NONE',  'LOAD_CC',    'NO_RD',    'NO_WR',    'SLTI3'],
   'SLTI3'  : ['F_A_LT_B',   'REG', 'MDR',  'REG',   'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],

   'SRAI'   : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'SRAI1'],
   'SRAI1'  : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'MEM_RD',   'NO_WR',    'SRAI2'],
   'SRAI2'  : ['F_A_ASHR',   'REG', 'MDR',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],

   'SRLI'   : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'SRLI1'],
   'SRLI1'  : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'MEM_RD',   'NO_WR',    'SRLI2'],
   'SRLI2'  : ['F_A_LSHR',   'REG', 'MDR',  'REG',   'LOAD_CC',    'NO_RD',    'NO_WR',    'FETCH'],

   'SW'     : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'SW1'],
   'SW1'    : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'MEM_RD',   'NO_WR',    'SW2'],
   'SW2'    : ['F_A_PLUS_B', 'REG', 'MDR',  'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'SW3'],
   'SW3'    : ['F_B',        'x',   'REG',  'MDR',   'LOAD_CC',    'NO_RD',    'NO_WR',    'SW4'],
   'SW4'    : ['x',          'x',   'x',    'x',     'NO_LOAD',    'NO_RD',    'MEM_WR',   'FETCH'],

   'BRA'    : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    'BRA1'],
   'BRA1'   : ['x',          'x',   'x',    'NONE',  'NO_LOAD',    'MEM_RD',   'NO_WR',    'BRA2'],
   'BRA2'   : ['F_A',        'MDR', 'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],

   'BRC'    : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    ""], #BRC_next
   'BRC1'   : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],
   'BRC2'   : ['x',          'x',   'x',    'NONE',  'NO_LOAD',    'MEM_RD',   'NO_WR',    'BRC3'],
   'BRC3'   : ['F_A',        'MDR', 'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],

   'BRN'    : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    ""], #BRN_next
   'BRN1'   : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],
   'BRN2'   : ['x',          'x',   'x',    'NONE',  'NO_LOAD',    'MEM_RD',   'NO_WR',    'BRN3'],
   'BRN3'   : ['F_A',        'MDR', 'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],

   'BRNZ'   : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    ""], #BRNZ_next
   'BRNZ1'  : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],
   'BRNZ2'  : ['x',          'x',   'x',    'NONE',  'NO_LOAD',    'MEM_RD',   'NO_WR',    'BRNZ3'],
   'BRNZ3'  : ['F_A',        'MDR', 'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],

   'BRV'    : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    ""], #BRV_next
   'BRV1'   : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],
   'BRV2'   : ['x',          'x',   'x',    'NONE',  'NO_LOAD',    'MEM_RD',   'NO_WR',    'BRV3'],
   'BRV3'   : ['F_A',        'MDR', 'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],

   'BRZ'    : ['F_A',        'PC',  'x',    'MAR',   'NO_LOAD',    'NO_RD',    'NO_WR',    ""], #BRZ_next
   'BRZ1'   : ['F_A_PLUS_2', 'PC',  'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],
   'BRZ2'   : ['x',          'x',   'x',    'NONE',  'NO_LOAD',    'MEM_RD',   'NO_WR',    'BRZ3'],
   'BRZ3'   : ['F_A',        'MDR', 'x',    'PC',    'NO_LOAD',    'NO_RD',    'NO_WR',    'FETCH'],
};

########################
# Main Subroutine
########################

def main():
   args = parseInput();

   tran("User: " + getuser() + "\n");
   tran("Date: " + datetime.now().strftime("%a %b %d %Y %I:%M:%S%p") + "\n");
   tran("Arguments: " + str(args) + "\n\n");

   global list_lines;
   if (piping): # reading list file from assembler
      while(True):
         try:
            line = raw_input();
            if (len(line) > 0): #reading will grab empty lines
               list_lines.append(line);
         except EOFError: break; # no more lines to read
   else:
      if (len(args) < 1): #args takes out flags and argv[0]
         usage();
      list_filename = args.pop(0);
      global list_fh;
      try:
         list_fh = open(list_filename, "r");
      except:
         print("Failed to open list_file");
         exit();
      # read all lines from list_fh, store in array,
      list_lines = list_fh.readlines();

   list_lines.pop(0); # remove 'addr data  label   opcode  operands'
   list_lines.pop(0); # remove '---- ----  -----   ------  --------'

   global sim_fh;
   global quit_after_sim_file;
   global run_only;
   # sim file is optional (read input from STDIN if not specified)
   if (len(args) > 0):
      sim_filename = args.pop(0);
      if (check_file):
         quit_after_sim_file = True; # makes it easier to grade en-masse
      try:
         sim_fh = open(sim_filename, "r");
      except:
         print("Failed to open sim_file\n");
         exit();
   elif (check_file): # no simulator file and grading, just run
      run_only = True;

   init();

   interface(sim_fh); #start taking input from user
   save_tran(); #save transcript

   if (sim_fh != None): sim_fh.close();
   if (list_fh != None): list_fh.close();

# parses the user supplied flags and sets globals
def parseInput():
   parser = OptionParser();
   parser.add_option("-v", "--version", action = "store_true",
                     dest = "get_version", default = False,
                     help="Prints the version, then exits");
   parser.add_option("-r", "--run", action = "store_true",
                     dest = "run_only", default = False,
                     help="Runs simulation, then exits");
   parser.add_option("-n", "--norandom", action = "store_false",
                     dest = "randomize_memory", default=True,
                     help="Initalizes memory to zeros, instead of random");
   parser.add_option("-t", "--transcript", action = "store",
                     dest = "transcript_fname", default = "", type = "str",
                     help="Stores transcipt of simulator in given file");
   parser.add_option("-q", "--quiet", action = "store_true",
                     dest = "quiet_mode", default = False,
                     help="Doesn't print output with step/ustep");
   parser.add_option("-g", "--grade", default = "", type = "str",
                     action = "store", dest = "check_file",
                     help="Runs simulation, checks state against file,\
                     then exits");
   parser.add_option("-i", default = False, dest = "pipe",
                     action = "store_true", help="Takes list file from STDIN.\
                     Use with as240's -o");

   (options, args) = parser.parse_args();
   if (options.get_version):
      print("risc240 " + str(version));
      exit();

   global run_only;
   run_only = options.run_only;

   global print_per;
   if (options.quiet_mode): print_per = "q";

   global check_file;
   if (options.check_file): #empty string (default) is false
      check_file = options.check_file;
      print_per = "q";

   global randomize_memory;
   randomize_memory = options.randomize_memory;

   global transcript_fname;
   transcript_fname = options.transcript_fname;

   global piping;
   piping = options.pipe;
   if (options.pipe and not (run_only or options.check_file)):
      print("Must use -r or -g flag when piping!");
      exit();

   return args;

# initalizes the simulator
def init():
   get_labels();

   init_p18240(); #put p18240 into a known state
   init_memory(); #initalize the memory

# prints usage for simulator
def usage():
   tran_print("./sim240 [list_file] [sim_file]");
   exit();

# Reads label from list file and adds them to the labels hash.
# Currently based on spacing format of list file.
def get_labels():
   #check each line for a label
   global labels;
   for line in list_lines:
      if (len(line) < 11): continue; #must not be a label on this line
      addr = line[0:4];
      line_start_at_label = line[11:];
      end_of_label = line_start_at_label.find(' '); #first space (label end)
      label = line_start_at_label[0:end_of_label].upper();
      labels[label] = addr;

# Interface Code
# Loop on user input executing commands until they quit
# Arguments:
#  * file handle for sim file.
# Return value:
#  * None
def interface(input_fh):
   done = False; # flag indicating user is done and wants to quit

   #take user input if reading from stdin
   taking_user_input = (input_fh == None);

   if (run_only):
      run("", "");
      if (check_file): check_state(check_file); # in grading mode, so grade
      done = True;

   while (not done):
      tran("> ");
      if (not taking_user_input): # we are reading from sim file
          line = input_fh.readline();
          if (len(line) == 0):
            taking_user_input = True;
            if (quit_after_sim_file):
               check_state(check_file);
               done = True;
            continue;
          if (not check_file): #in grading mode
            tran_print(line.rstrip("\n"));
      else:
         try: line = raw_input("> ");
         except EOFError:
            print("\nUnexpected input, did you forget to quit?");
            exit();
         tran(line);

      # assume user input is valid until discovered not to be
      valid = True;
      #line = line.upper(); #should be independent of case
      if (match(menu["quit"], line, IGNORECASE)):
         done = True;
      elif (match(menu["help"], line, IGNORECASE)):
         print_help();
      elif (match(menu["reset"], line, IGNORECASE)):
         init();
      elif (match(menu["run"], line, IGNORECASE)):
         matchObj = match(menu["run"], line, IGNORECASE);
         run(matchObj.group(2), matchObj.group(3));
      elif (match(menu["step"], line, IGNORECASE)):
         if (print_per == "i"): tran_print(wide_header);
         step();
         if (print_per == "i"): tran_print(get_state());
      elif (match(menu["ustep"], line, IGNORECASE)):
         if (print_per != "q"): tran_print(wide_header);
         cycle();
         if (print_per != "q"): tran_print(get_state());
      elif (match(menu["break"], line, IGNORECASE)):
         matchObj = match(menu["break"], line, IGNORECASE);
         set_breakpoint(matchObj.group(1));
      elif (match(menu["clear"], line, IGNORECASE)):
         matchObj = match(menu["clear"], line, IGNORECASE);
         clear_breakpoint(matchObj.group(1));
      elif (match(menu["lsbrk"], line, IGNORECASE)):
         list_breakpoints();
      elif (match(menu["load"], line, IGNORECASE)):
         matchObj = match(menu["load"], line, IGNORECASE);
         load(matchObj.group(1));
      elif (match(menu["save"], line, IGNORECASE)):
         matchObj = match(menu["save"], line, IGNORECASE);
         save(matchObj.group(1));
      elif (match(menu["set_reg"], line, IGNORECASE)):
         matchObj = match(menu["set_reg"], line, IGNORECASE);
         set_reg(matchObj.group(1), matchObj.group(2));
      elif (match(menu["get_reg"], line, IGNORECASE)):
         matchObj = match(menu["get_reg"], line, IGNORECASE);
         get_reg(matchObj.group(1));
      elif (match(menu["set_mem"], line, IGNORECASE)):
         matchObj = match(menu["set_mem"], line, IGNORECASE);
         set_memory(matchObj.group(2), matchObj.group(3), 1);
      elif (match(menu["get_mem"], line, IGNORECASE)):
         matchObj = match(menu["get_mem"], line, IGNORECASE);
         fget_memory({"lo" : matchObj.group(2),
                      "hi" : matchObj.group(4)});
      elif (match(menu["check"], line, IGNORECASE)):
         matchObj = match(menu["check"], line, IGNORECASE);
         check_state(matchObj.group(1));
      elif (match(menu["labels"], line, IGNORECASE)):
         print_labels();
      elif (match("^$", line, IGNORECASE)): # user just struck enter
         pass; # something needs to be here for python
      else:
         valid = False;

      if (not valid): tran_print("Invalid input. Type 'help' for help.");

# prints help message
def print_help():
   help_msg = '';
   help_msg += "\n";
   help_msg += "quit,q,exit             Quit the simulator.\n";
   help_msg += "help,h,?                Print this help message.\n";
   help_msg += "step,s                  Simulate one instruction.\n";
   help_msg += "ustep,u                 Simulate one micro-instruction.\n";
   help_msg += "run,r [n]               Simulate the next n instructions.\n";
   help_msg += "run u                   Same as above, but print ever ustep\n";
   help_msg += "break [addr/label]      Set a breakpoint at [addr] or [label].\n";
   help_msg += "lsbrk                   List all set breakpoints.\n";
   help_msg += "clear [addr/label/*]    Clear breakpoint at [addr]/[label], or clear all.\n";
   help_msg += "reset                   Reset the processor to initial state.\n";
   help_msg += "save [file]             Save the current state to a file.\n";
   help_msg += "load [file]             Load the state from a given file.\n";
   help_msg += "check [file]            Checks state against state described in file.\n";
   help_msg += "labels                  Prints the lables described in the .list file.\n";
   help_msg += "\n";
   help_msg += "You may set registers like so:          PC=100\n";
   help_msg += "You may view register contents like so: PC?\n";
   help_msg += "You may view the register file like so: R*?\n";
   help_msg += "You may view all registers like so:     *?\n";
   help_msg += "\n";
   help_msg += "You may set memory like so:  m[00A0]=100\n";
   help_msg += "You may view memory like so: m[00A0]? or with a range: m[0:A]?\n";
   help_msg += "\n";
   help_msg += "Note: All constants are interpreted as hexadecimal.";
   tran_print(help_msg);

# initalizes the processor (registers zeroed, state = FETCH)
def init_p18240():
   global cycle_num;
   cycle_num = 0;

   global state;
   for key in state:
      if (key == "regFile"):
         for i in xrange(8):
            state["regFile"][i];
      elif (match("[ZNCV]", key)):
         state[key] = "0";
      elif (key == "STATE"):
         state[key] = "FETCH";
      else:
         state[key] = "0000";

# initalizes the memory, sets memory locations in list file
def init_memory():
    global memory;
    memory = {};
    int_max = (1 << 16) - 1; # 16-bit ints
    global randomize_memory;
    for addr in xrange(0, 1 << 16, 2):
        data_num = randint(0, int_max) if randomize_memory else 0;
        data = to_4_digit_uc_hex(data_num);
        addr = to_4_digit_uc_hex(addr);
        set_memory(addr, data, 0);

    # memory is zero if not defined in dictionary
    global list_lines;
    for line in list_lines:
        arr = line.split(" ");
        if (len(arr) < 2):
            print("Fatal Error: File format not recognized");
            exit();
        addr = arr[0];
        data = arr[1];
        memory[addr] = [data.lower(),1];

# Run simulator for n instructions
# If n is undefined, run indefinitely
# In either case, the exception is to stop
# at breakpoints or the STOP microinstruction
# print_per_requested is how often state is printer (per U-instruction,
# per Instruction, Quiet)
def run(num, print_per_requested):
   num = int(num) if num else (1 << 32); # num = None if not defined

   global print_per;
   global first_print;
   old_print_per = print_per;
   if (print_per_requested):
      print_per = print_per_requested;
   if (print_per != "q"):
      tran_print(wide_header);

   if not first_print:
      if (print_per != "q"):
         tran_print(get_state());
      first_print = True;

   for i in xrange(num):
      step();
      if (print_per == "i"):
         tran_print(get_state());
      if (state["PC"] in breakpoints):
         tran_print("Hit breakpoint at $" + state["PC"] + ".\n");
         break;

      if (state["STATE"] == "STOP1"):
         break;

   print_per = old_print_per;

# Simulate one instruction
def step():
   global first_print;
   first_print = True;
   cycle(); # do-while in python
   if (print_per == "u"): tran_print(get_state());
   while (state["STATE"] != "FETCH" and state["STATE"] != "STOP1"):
      cycle();
      if (print_per == "u"): tran_print(get_state());

# Set a break point at a given address or label.
# Any thing which matches a hex value (e.g. a, 0B, etc) is interpreted
# as such *unless* it is surrounded by '' e.g. 'A' in which case it is
# interpreted as a label and looked up in the labels hash.
# Anything which does not match a hex value is also interpreted as a label
# with or without surrounding ''.
def set_breakpoint(arg):
   is_label = False;
   if (match("^'(\w+)'$", arg)):
      label = match("^'(\w+)'$", arg).group(1).upper();
      is_label = True;
   elif (match("^\$[0-9a-f]{1,4}$", arg, IGNORECASE)):
      addr = to_4_digit_uc_hex(int(arg[1:],16));
   else:
      is_label = True;
      label = arg.upper();

   if (is_label):
      if (label in labels):
         addr = labels[label];
      else:
         tran_print("Invalid label.");
         return;

   global breakpoints;
   breakpoints[addr] = 1;

# Clears a breakpoint at a given address or label
def clear_breakpoint(arg):
   clear_all = False;
   is_label = False;

   if (match("^'(\w+)'$", arg)):
      label = match("^'(\w+)'$", arg).group(1).upper();
      is_label = True;
   elif (match("^\$[0-9a-f]{1,4}$", arg, IGNORECASE)):
      addr = to_4_digit_uc_hex(int(arg[1:],16));
   elif (arg == "*"):
      clear_all = True;
   else:
      label = arg.upper();
      is_label = True;

   if (is_label):
      if (label in labels):
         addr = labels[label];
      else:
         tran_print("Invalid label.");
         return;

   global breakpoints;
   if (clear_all):
      breakpoints = {};
   else:
      if (addr in breakpoints):
         del breakpoints[addr];
      else: #no break point at that address
         if (is_label):
            tran_print("No breakpoint at " + label + ".");
         else:
            tran_print("No breakpoint at " + addr + ".");

# Print out all of the breakpoints and the addresses.
def list_breakpoints():
   for key in breakpoints:
      tran_print('$' + key);

# Loads state from a given state file (usually made by save).
def load(filename):
   tran_print("Loading from " + filename + "...");
   try:
      fh = open(filename, "r");
   except:
      tran_print("Unable to read from " + filename);
      return;
   lines = fh.readlines();
   lines.pop(0); #removes "Breakpoints"
   line = lines.pop(0);
   while (len(line) > 1): # breakpoints to add still
      set_breakpoint(line);
      line = lines.pop(0);
   lines.pop(0); # State:
   values = lines.pop(0).split();
   labels = wide_header.split();
   global state;
   for i in xrange(len(labels)): # load register values
      label = labels[i];
      if (label in state):
         state[label] = values[i];
      elif (match("^\s*R?\s*(\d*)?\s*$", label)):
         matchObj = match("^\s*R?\s*(\d*)?\s*$", label);
         reg_num = int(matchObj.group(1));
         state["regFile"][reg_num] = values[i];
      elif (label == "Cycle"):
         global cycle_num;
         cycle_num = int(values[i]);
      else: # ZNCV register
         flag_num = 0;
         for flag in ["Z", "N", "C", "V"]:
            state[flag] = values[i][flag_num];
            flag_num += 1;
   lines.pop(0); # newline
   lines.pop(0); # Memory:
   while (len(lines) > 0): # load memory values
      line = lines.pop(0);
      addr = line[4:8];
      value = line[16:20];
      set_memory(addr, value, 1);
   return;

# Save state of processor, memory, and breakpoints to a file. State
# file can be used to check against the current processor state, or can
# be loaded into simulation
def save(filename):
   tran_print("Saving to " + filename + "...");
   try:
      fh = open(filename, "w");
   except:
      tran_print("Unable to write to " + filename);
      return;
   fh.write("Breakpoints:\n");
   for key in breakpoints:
      fh.write(key + "\n");
   fh.write("\nState:\n");
   fh.write(get_state() + "\n\n");
   fh.write("Memory:\n");
   fget_memory({"fh" : fh,
                "lo" : '0',
                "hi" : "ffff",
                "zeros" : 0});
   fh.close();

# Sets the value of a register
def set_reg(reg_name, value):
   global state;
   reg_name = reg_name.upper(); #keys stored as uppercase
   value = to_4_digit_uc_hex(int(value,16));
   if (match('^R([1-7])$', reg_name, IGNORECASE)):
      matchObj = match('^R([1-7])$', reg_name, IGNORECASE);
      state["regFile"][int(matchObj.group(1))] = value;
   elif (match('^R0$', reg_name, IGNORECASE)):
      # do nothing: r0 is hard-wired to 0
      pass
   elif (match("^[ZNCV]$", reg_name)):
      if (match("^[01]$", reg_name)):
         state[reg_name] = value;
      else:
         tran_print("Value must be 0 or 1 for this register.");
   elif (match("^PC$", reg_name)):
      state[reg_name] = word_align(to_4_digit_uc_hex(int(value,16)));
   else:
      state[reg_name] = to_4_digit_uc_hex(int(value,16));

# Gets the value of a register
def get_reg(reg_name):
   reg_name = reg_name.upper();
   if (reg_name == "*"):
      tran_print(get_state());
   elif (reg_name == "R*"):
      print_regfile();
   elif (match("R([0-7])", reg_name, IGNORECASE)):
      reg_num = int(match("R([0-7])", reg_name, IGNORECASE).group(1));
      tran_print("r%d: %s" % (reg_num, state["regFile"][reg_num]));
   else:
      value = state[reg_name];
      tran_print("%s: %s" % (reg_name, value));

# Gets a string containing all the state information
def get_state():
   (Z,N,C,V) = (state["Z"], state["N"], state["C"], state["V"]);
   state_info = "%0.4d" % cycle_num;
   state_info += " " * (7 - len(state["STATE"]));
   state_info += "%s %s %s %s%s%s%s %s %s" % (state["STATE"], state["PC"],
                                            state["IR"], Z, N, C, V,
                                            state["MAR"], state["MDR"].upper());
   for reg in state["regFile"]:
      state_info += " " + reg;
   return state_info;

# prints the state of R0-R7
def print_regfile():
   for index in xrange(0,8,2):
      value = state["regFile"][index];
      reg_str = "r%d: %s \t" % (index, value);
      value = state["regFile"][index+1];
      reg_str += "r%d: %s" %(index+1, value);
      tran_print(reg_str);

# Sets a memory value. The valid bit specifies if it will be store in
# a save state file. By heuristic, memory is invalid until changed.
def set_memory(addr, value, valid):
   # enforce word-aligned memory accesses
   addr_aligned = word_align(addr);

   addr_hex = to_4_digit_uc_hex(int(addr_aligned,16));
   value_hex = to_4_digit_uc_hex(int(value,16));
   memory[addr_hex] = [value_hex, valid];

# Gets the state of a selection of memory, arguments are passed in a dict
# get_zeros specifies if zeros will be printed when they are reached
# lo - the inclusive lower bound of memory
# hi - the inclusive upper bound
# fh - file handle to write memory state to, default to STDOUT
def fget_memory(args):
   if ("zeros" in args):
      print_zeros = args["zeros"];
   else:
      print_zeros = True;
   lo = int(args["lo"], 16);
   if ("hi" in args and args["hi"] != None):
      hi = int(args["hi"],16);
   else:
      hi = lo;

   if (lo > hi):
      tran_print("Did you mean mem[%x:%x]?" % (hi,lo));
      return;

   # word-align memory lookup
   if (lo % 2) == 1:
      lo = lo - 1;

   for index in xrange(lo, hi+1, 2):
      addr = ("%.4x" % (index)).upper();
      addr_hi = ("%.4x" % (index + 1)).upper();
      value = (memory[addr][0]).upper() if (addr in memory) else "0000";
      # Value in memory location that we care about
      if (value != "0000" or print_zeros):
         value_no_regs = "%.4x" % (int(value,16) & 0xffc0);
         state_str = hex_to_state(value_no_regs);
         rd = bs(int(value,16), "8:6");
         rs1 = bs(int(value,16), "5:3");
         rs2 = bs(int(value,16), "2:0");
         mem_val = "mem[%s:%s]: %s %s %d %d %d" % (addr, addr_hi, value,
                                         state_str, rd, rs1, rs2);
         if ("fh" in args and memory[addr][1]): #only save used memory
            args["fh"].write(mem_val + "\n");
         elif ("fh" not in args):
            tran_print(mem_val);

# Checks the state of the processor and memory against a given state file
# Prints out differences. Registers set to XXXX/xxxx in state file are
# ignored for comparison. Memory not specified in state file is also ignored
# Breakpoints are always ignored.
def check_state(state_file):
    try:
        fh = open(state_file, "r");
    except:
        tran_print("Failed to open state file");
        return;
    has_diffs = False;
    lines = fh.readlines();
    while (not lines[0].startswith("State")): # skipping breakpoints
        lines.pop(0);
    lines.pop(0); # removes "State: line
    file_state = lines.pop(0).split();
    sim_state = get_state().split();
    labels = wide_header.split();
    dont_care = "^\s*x{1,4}\s*$";
    for i in xrange(len(file_state)):
        # register isn't a don't care and doesn't match the simulator
        if (not match(dont_care, file_state[i].upper(), IGNORECASE) and
                file_state[i] != sim_state[i]):
            has_diffs = True;
            tran_print(labels[i] + " differs: sim = " + sim_state[i]
                    + ", file = " + file_state[i]);
    lines.pop(0); # removes newline
    lines.pop(0); # removes "Memory:"
    for line in lines:
        # Line format:
        # mem[xxxx:xxxx]: xxxx INSTR x x x
        # We only care about the addr and the number
        mem_arr = re.split('[\[ :\]]', line)
        mem_arr = list(filter(None, mem_arr))
        if len(mem_arr) < 4:
            tran_print("Error parsing memory in state file")
            return
        addr_lo = mem_arr[1].upper()
        addr_hi = mem_arr[2].upper()
        file_val = mem_arr[3].upper()
        sim_val = memory[addr_lo][0].upper();
        if (file_val != sim_val):
            has_diffs = True;
            tran_print("Mem[{}:{}] differs: sim = {}, ref = {}".format(
                        addr_lo, addr_hi, sim_val, ref_val))
    if not has_diffs:
        tran_print("State matches reference file!")

# Prints all the labels associated with the given .list file
def print_labels():
   for key in labels:
      if (len(key) > 0): # ignores spuriously created labels
         tran_print(key + ": " + labels[key]);



########################
# Simulator Code
########################

# Simulate one cycle in the processor
def cycle():
   # Control Path ###
   cp_out = control();

   ### Start of ALU ###
   sel_rd = bs(int(state["IR"],16), "8:6");
   sel_rs1 = bs(int(state["IR"],16), "5:3");
   sel_rs2 = bs(int(state["IR"],16), "2:0");

   rs1_data = state["regFile"][sel_rs1]; #strings, since mux could select this
   rs2_data = state["regFile"][sel_rs2];

   inA = int(mux({"PC" : state["PC"], "MDR" : state["MDR"], "SP" : state["SP"],
              "REG" : rs1_data}, cp_out["srcA"]), 16);
   inB = int(mux({"PC" : state["PC"], "MDR" : state["MDR"], "SP" : state["SP"],
              "REG" : rs2_data}, cp_out["srcB"]), 16);

   alu_in = {"alu_op" : cp_out["alu_op"], "inA" : inA, "inB" : inB};
   alu_out = alu(alu_in);
   ### End of ALU ##

   ### Memory ###
   mem_data = memory_sim({"re" : cp_out["re"], "we" : cp_out["we"],
                      "data" : state["MDR"], "addr" : state["MAR"]});

   ### Sequential Logic ###
   dest = cp_out["dest"];

   if (dest != "NONE"):
      if (dest == "REG"):
         if(sel_rd != 0):
             state["regFile"][sel_rd] = alu_out["alu_result"];
      else:
         state[dest] = alu_out["alu_result"];

   # store memory output to MDR
   if (cp_out["re"] == "MEM_RD"):
      state["MDR"] = mem_data;

   # load condition codes
   if (cp_out["load_CC"] == "LOAD_CC"):
      for flag in ["Z", "N", "C", "V"]:
         state[flag] = alu_out[flag];


   state["STATE"] = cp_out["next_control_state"];

   global cycle_num;
   cycle_num += 1;

##################################################
############# CONTROL PATH CODE ##################
##################################################

# gets the micro instruction assocated with a given state,
# sets next state values that are dependent on flags
def control():

   # python is bad with globals
   nextState_logic["DECODE"][7] = hex_to_state(state["IR"]); #IR_STATE
   nextState_logic["BRN"][7] = "BRN2" if int(state["N"]) else "BRN1"; #BRN_NEXT
   nextState_logic["BRNZ"][7] = "BRNZ2" if (int(state["N"]) | int(state["Z"])) else "BRNZ1"; #BRNZ_NEXT
   nextState_logic["BRZ"][7] = "BRZ2" if int(state["Z"]) else "BRZ1"; #BRZ_NEXT
   nextState_logic["BRV"][7] = "BRV2" if int(state["V"]) else "BRV1"; #BRV_NEXT
   nextState_logic["BRC"][7] = "BRC2" if int(state["C"]) else "BRC1"; #BRC_NEXT
   curr_state = state["STATE"];

   if (curr_state not in nextState_logic):
      tran_print("PC points to undefined instruction, exiting...")
      exit();
   output = nextState_logic[curr_state];

   uinstr = {
      "alu_op" : output[0],
      "srcA" : output[1],
      "srcB" : output[2],
      "dest" : output[3],
      "load_CC" : output[4],
      "re" : output[5],
      "we" : output[6],
      "next_control_state" : output[7],
   };

   return uinstr;

# Simulates the P18240's ALU. Args values are ints, values are returned
# as strings.
def alu(args):
   opcode = args["alu_op"];
   inA = args["inA"];
   inB = args["inB"];

   Z = 0;
   C = 0;
   N = 0;
   V = 0;

   if (opcode == "F_A"):
      out = inA;
   elif (opcode == "F_A_PLUS_2"):
      out = bs(inA + 2, '15:0');
      C = bs(inA + 2, "16");
      V = ~bs(inA, "15") & bs(out, "15");
   elif (opcode == "F_A_PLUS_B"):
      out = bs(inA+inB, '15:0');
      C = bs(inA+inB, "16");
      V = (bs(inA,"15") & bs(inB,"15") & ~bs(out,"15")) | (~bs(inA,"15") & ~bs(inB,"15") & bs(out,"15"));
   elif (opcode == "F_A_MINUS_B"):
      out = bs(inA - inB,'15:0'); # A-B (set carry below)
      C = 1 if (inB >= inA) else 0;
      V = (bs(inA,"15") & ~bs(inB,"15") & ~bs(out,"15")) | (~bs(inA,"15") & bs(inB,"15") & bs(out,"15"));
   elif (opcode == "F_B"):
      out = inB;
   elif (opcode == "F_A_NOT"):
      out = bs(~inA, "15:0");
   elif (opcode == "F_A_AND_B"):
      out = inA & inB;
   elif (opcode == "F_A_OR_B"):
      out = inA | inB;
   elif (opcode == "F_A_XOR_B"):
      out = inA ^ inB;
   elif (opcode == "F_A_SHL"):
      out = bs(inA << bs(inB, "3:0"), "15:0");
   elif (opcode == "F_A_LSHR"):
      out = bs(inA >> bs(inB, "3:0"), "15:0"); # logical right shift
   elif (opcode == "F_A_ASHR"):
      sign_bit = inA & 0x8000;
      shifted = inA;
      for x in range(bs(inB, "3:0")):
         shifted = (shifted >> 1) | sign_bit;
      out = bs(shifted, "15:0");
   elif (opcode == "F_A_LT_B"):
      sign_bit_A = inA & 0x8000;
      sign_bit_B = inB & 0x8000;

      if (sign_bit_A and ~sign_bit_B):
         out = 1
      elif (~sign_bit_A and sign_bit_B):
         out = 0
      else:    # both are positive or both are negative
         if (sign_bit_A): #both are negative
            out = inB < inA
         else: # both are positive
            out = inA < inB;
      C = (inA - inB) & 0x8000;
      V = (((inA - inB) & 0x8000) == (inA & 0x8000));
   elif (opcode == "x"):
      out = 0;
   else:
      print("Error: invalid alu opcode $opcode");

   N = bs(out, "15");
   Z = 1 if (out == 0) else 0;

   rv = {
      "alu_result" : ("%.4x" % out).upper(),
      "Z" : str(Z),
      "N" : str(N),
      "C" : str(C),
      "V" : str(V),
   };

   return rv;

# Simulates a memory.
# Arguments are specified in a hash:
# If value for 're' key is 'MEM_RD', read from memory.
# If value for 'we' key is 'MEM_WR', write to memory.
# Reading and writing both use the value of the 'addr' key.
# Writing writes the value of the 'data_in' key.
# Return value:
# Returns the data stored at 'addr' when reading; 0000 otherwise.
def memory_sim(args):
   re = args["re"];
   we = args["we"];
   data_in = args["data"];
   addr = args["addr"];
   addr_aligned = word_align(addr);

   data_out = "0000"; # data_in would mimic bus more accurately...
   if (re == "MEM_RD") and (addr_aligned in memory):
      data_out = memory[addr_aligned][0];
   if (we == "MEM_WR"):
      memory[addr_aligned][0] = data_in;
      memory[addr_aligned][1] = 1;

   return data_out;

# Simulates a multiplexor. The inputs to be selected must be in a dict
def mux(inputs, sel):
   if (sel == "x"):
      return '0';

   return inputs[sel];


########################
# Supporting Subroutines
########################

# adds a new line to the transcript - line doesn't include \n
def tran(line):
   global transcript;
   if (transcript_fname):
      transcript += (line);

# add the string to the transcript and print to file
def tran_print(line):
   tran(line + "\n");
   print(line);

# Bitslice subroutine.
# First argument is a number, second argument is a string which indicates
# which bits you want to extract. This follows verilog format
# That is, '5' will extract bit 5, '5:2' will extract bits 5 to 2.
# The return value is shifted down so that the least significant selected
# bit moves down to the least significant position.
def bs(bits, indices):
   matchObj = match("(\d+):(\d+)", indices);
   if (matchObj != None):
      hi = int(matchObj.group(1));
      lo = int(matchObj.group(2));
      return (bits >> lo) & ((2 << (hi - lo)) - 1);
   else:
      index = int(match("(\d+)", indices).group(1));
      return (bits >> index) & 1;

# Takes a hexadecimal number in canonical form and outputs the
# string corresponding to that opcode.
def hex_to_state(hex_value):
   bin_val = bin(int(hex_value, 16));
   bin_val = bin_val[2:]; #removes starting '0b'
   while (len(bin_val) < 16): #adds starting zeros
      bin_val = "0" + bin_val;

   key = bin_val[0:3] + "_" + bin_val[3:7];
   state = uinst_bin_keys[key] if (key in uinst_bin_keys) else "UNDEF";

   return state;

# Saves the transcript to transcript.txt
def save_tran():
   if (transcript_fname):
      try:
         tran_fh = open(transcript_fname, "w");
      except:
         exit();
      tran_fh.write(transcript);
      tran_fh.close();

# Takes an integer as input and outputs a canonical form
# The canonical form is a 4 digit uppercase hexadecimal number
# Input can be 1 to 4 digits with any case.
#
# WARNING: If the number will take more than 4 hex digits, this function will
# return a number with more than 4 digits!
def to_4_digit_uc_hex(num):
   return ("%.4x" % num).upper();

# Takes a hexadecimal address string and returns the word-aligned
# address as a string
# If second is true, then the function returns the address of the
# second byte; otherwise, the function returns the address of the
# first byte
def word_align(addr, second = False):
   aligner_first = {
      "1": "0",
      "3": "2",
      "5": "4",
      "7": "6",
      "9": "8",
      "B": "A",
      "D": "C",
      "F": "E"
   }

   aligner_second = {
      "0": "1",
      "2": "3",
      "4": "5",
      "6": "7",
      "8": "9",
      "A": "B",
      "C": "D",
      "E": "F"
   }

   addrUp = addr.upper();
   alignedAddr = "";

   if second:
      alignedAddr = addrUp[:-1] + aligner_second.get(addrUp[-1], addrUp[-1]);
   else:
      alignedAddr = addrUp[:-1] + aligner_first.get(addrUp[-1], addrUp[-1]);

   return alignedAddr;

main();
