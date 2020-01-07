#! /usr/bin/env python3
import random
import unittest
import as240
import os

FORMAT_1 = '{:4} {:4}  {:8}   {:6}  {:8}'

def hex_string4(num):
    s = hex(num)
    s = s[2:]
    s = '0000' + s
    s = s[-4:]
    s = s.upper()
    return s

class TestAsmLine(unittest.TestCase):    
    
    def test_ZeroOpcodes(self):
        a = as240.AsmLine(' STOP', line_number=10, mem_address=500)
        next_mem_address = a.next_mem_address()
        self.assertEqual(next_mem_address, 502)
        a.assemble()
        s = str(a)
        self.assertEqual(s, '01F4 FE00' + ' ' * 13 + 'STOP            ')
        
    def test_OneOpcode(self):
        a = as240.AsmLine(' BRA $2000', line_number=10, mem_address=502)
        self.assertEqual(a.next_mem_address(), 506)
        a.assemble()
        s = str(a)
        t = '01F6 F800' + ' ' * 13 + 'BRA' + ' ' * 13
        t += '\n'
        t += '01F8 2000' + ' ' * 21 + '$2000   '
        self.assertEqual(s, t)

    def test_TwoOpcodes(self):
        a = as240.AsmLine(' MV R7 , R0', line_number=10, mem_address=502)
        self.assertEqual(a.next_mem_address(), 504)
        a.assemble()
        s = str(a)
        t = '01F6 21C0' + ' ' * 13 + 'MV' + ' ' * 6 + 'R7 R0   '
        self.assertEqual(s, t)
        
    def test_ThreeOpcodes(self):
        a = as240.AsmLine(' ADD R2,R4,R1', line_number=10, mem_address=504)
        self.assertEqual(a.next_mem_address(), 506)
        a.assemble()
        s = str(a)
        t = '01F8 00A1' + ' ' * 13 + 'ADD' + ' ' * 5 + 'R2 R4 R1'
        self.assertEqual(s, t)
      
    def test_SyntaxError(self):
        with self.assertRaises(as240.SyntaxError):
            a = as240.AsmLine(' BRA R1, R2', line_number=11, mem_address=502) 
          
    def test_LabelZeroOpcodes(self):
        a = as240.AsmLine('aLabel STOP', line_number=10, mem_address=500)
        self.assertEqual(a.next_mem_address(), 502)
        a.assemble()
        s = str(a)
        t = '01F4 FE00  ALABEL' + ' ' * 5 + 'STOP' + ' ' * 12
        self.assertEqual(s, t)
        mem_val = as240.SymbolTable.lookup_label('ALABEL', line_number=10) 
        self.assertEqual(mem_val, 500)

    def test_LabelOneOpcode(self):
        a = as240.AsmLine('bLabel BRA $3000', line_number=10, mem_address=502)
        self.assertEqual(a.next_mem_address(), 506)
        a.assemble()
        s = str(a)
        t = '01F6 F800  BLABEL' + ' ' * 5 + 'BRA' + ' ' * 13
        t += '\n'
        t += '01F8 3000' + ' ' * 21 + '$3000   '
        self.assertEqual(s, t)
        mem_val = as240.SymbolTable.lookup_label('BLABEL', line_number=10) 
        self.assertEqual(mem_val, 502)

    def test_LabelTwoOpcodes(self):
        a = as240.AsmLine('cLabel LI R1,$1234', line_number=10, mem_address=506)
        self.assertEqual(a.next_mem_address(), 510)
        a.assemble()
        s = str(a)
        t = '01FA 3040  CLABEL' + ' ' * 5 + 'LI' + ' ' * 6 + 'R1      '
        t += '\n'
        t += '01FC 1234' + ' ' * 21 + '$1234   '
        self.assertEqual(s, t)
        mem_val = as240.SymbolTable.lookup_label('CLABEL', line_number=10) 
        self.assertEqual(mem_val, 506)
 
    def test_LabelThreeOpcodes(self):
        a = as240.AsmLine('dLabel LW R7 , R0 , $1234', line_number=10, mem_address=508)
        self.assertEqual(a.next_mem_address(), 512)
        a.assemble()
        s = str(a)
        t = '01FC 29C0  DLABEL' + ' ' * 5 + 'LW' + ' ' * 6 + 'R7 R0   '
        t += '\n'
        t += '01FE 1234' + ' ' * 21 + '$1234   '
        self.assertEqual(s, t)
        mem_val = as240.SymbolTable.lookup_label('DLABEL', line_number=10) 
        self.assertEqual(mem_val, 508)
        
    def test_EQU(self):
        a = as240.AsmLine('LBL_EQU1 .EQU $1987', line_number=10, mem_address=508)
        self.assertEqual(a.next_mem_address(),508)  # EQU doesn't take up memory
        a.assemble()
        self.assertEqual(str(a), '')  #EQU doesn't show up in the listing
        mem_val = as240.SymbolTable.lookup_label('LBL_EQU1', line_number=10)
        self.assertEqual(mem_val, 6535)
        
    def test_EQU_NEG1(self):
        with self.assertRaises(as240.SyntaxError):
            as240.AsmLine(' .EQU $1987', line_number=11, mem_address=502) 
              
    def test_EQU_NEG2(self):
        with self.assertRaises(as240.SyntaxError):
            as240.AsmLine('LBL_EQU2 .EQU R1', line_number=11, mem_address=502) 
        
    def test_EQU_NEG3(self):
        with self.assertRaises(as240.SyntaxError):
            as240.AsmLine('LBL_EQU3 .EQU ', line_number=11, mem_address=502) 
        
    def test_EQU_NEG4(self):
        with self.assertRaises(as240.SyntaxError):
            as240.AsmLine('LBL_EQU4 .EQU $1987, $200', line_number=11, mem_address=502) 
        
    def test_EQU_NEG5(self):
        with self.assertRaises(as240.SyntaxError):
            as240.AsmLine('LBL_EQU5 .EQU $1987, $200, $100', line_number=11, mem_address=502) 
        
    def test_ORG(self):
        a = as240.AsmLine(' .ORG $1987', line_number=10, mem_address=None)
        self.assertEqual(a.next_mem_address(),6535)  
        a.assemble()
        self.assertEqual(str(a), '')  #ORG doesn't show up in the listing

    def test_ORG_NEG1(self):
        with self.assertRaises(as240.SyntaxError):
            as240.AsmLine('LBL_ORG1 .ORG $1987', line_number=11, mem_address=502) 
                
    def test_ORG_NEG2(self):
        with self.assertRaises(as240.SyntaxError):
            as240.AsmLine(' .ORG R1', line_number=11, mem_address=502) 
                
    def test_ORG_NEG3(self):
        with self.assertRaises(as240.SyntaxError):
            as240.AsmLine(' .ORG $1987, $200', line_number=11, mem_address=502) 
                
    def test_ORG_NEG4(self):
        with self.assertRaises(as240.SyntaxError):
            as240.AsmLine(' .ORG $1987,$200,$300', line_number=11, mem_address=502) 
                
    def test_DW(self):
        a = as240.AsmLine('LBL_DW1 .DW $1987', line_number=10, mem_address=502)
        self.assertEqual(a.next_mem_address(),504)  
        a.assemble()
        t = FORMAT_1.format('01F6', '1987', 'LBL_DW1', '.DW', '$1987')
        self.assertEqual(str(a), t)  
        mem_val = as240.SymbolTable.lookup_label('LBL_DW1', line_number=10)
        self.assertEqual(mem_val, 502)
        locs = a.mem_locs()
        self.assertTupleEqual((502, 6535), locs[0])

    def test_DW2(self):
        a = as240.AsmLine(' .DW $2000', line_number=10, mem_address=504)
        self.assertEqual(a.next_mem_address(),506)  
        a.assemble()
        t = FORMAT_1.format('01F8', '2000', '', '.DW', '$2000')
        self.assertEqual(str(a), t)  
        locs = a.mem_locs()
        self.assertTupleEqual((504, 8192), locs[0])

    def test_DW3(self):
        ''' The operand for a .DW can be a label. '''
        e = as240.AsmLine('LBL_DW5 .EQU $1987', line_number=9, mem_address=510)
        e.assemble()
        a = as240.AsmLine('LBL_DW6 .DW LBL_DW5', line_number=10, mem_address=510)
        a.assemble()
        locs = a.mem_locs()
        self.assertTupleEqual((510, 0x1987), locs[0])

    def test_DW_NEG1(self):
        with self.assertRaises(as240.SyntaxError):
            a = as240.AsmLine('LBL_DW2 .DW %EAX', line_number=11, mem_address=502) 
                
    def test_DW_NEG2(self):
        with self.assertRaises(as240.SyntaxError):
            a = as240.AsmLine('LBL_DW3 .DW $2000, $200', line_number=11, mem_address=502) 
                
    def test_DW_NEG3(self):
        with self.assertRaises(as240.SyntaxError):
            a = as240.AsmLine('LBL_DW4 .DW $2000, $200, $300', line_number=11, mem_address=502) 
                
    def test_ADD(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_ADD1 ADD R1,R2,R7', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'0057','L_ADD1','ADD','R1 R2 R7')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_ADD1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0x57), locs[0])

    def test_ADDI(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_ADDI1 ADDI R1,R2,$1000', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'3050','L_ADDI1','ADDI','R1 R2')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),'1000','','','$1000')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_ADDI1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0x3050), locs[0])

    def test_AND(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_AND1 AND R3,R1,R6', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'90CE','L_AND1','AND','R3 R1 R6')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_AND1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0x90CE), locs[0])

    def test_BRA(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        dst_address = random.randrange(0, 0x8000) * 2
        dst_string = hex_string4(dst_address)
        dst_string_dollar = '$' + dst_string
        asm_string = 'L_BRA1 BRA ${}'.format(dst_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'F800','L_BRA1','BRA','')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),dst_string,'','',dst_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_BRA1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0xF800), locs[0])
        self.assertTupleEqual((mem_address+2, dst_address), locs[1])
 
    def test_BRC(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        dst_address = random.randrange(0, 0x8000) * 2
        dst_string = hex_string4(dst_address)
        dst_string_dollar = '$' + dst_string
        asm_string = 'L_BRC1 BRC ${}'.format(dst_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'A800','L_BRC1','BRC','')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),dst_string,'','',dst_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_BRC1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0xA800), locs[0])
        self.assertTupleEqual((mem_address+2, dst_address), locs[1])
 
    def test_BRN(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        dst_address = random.randrange(0, 0x8000) * 2
        dst_string = hex_string4(dst_address)
        dst_string_dollar = '$' + dst_string
        asm_string = 'L_BRN1 BRN ${}'.format(dst_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'9800','L_BRN1','BRN','')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),dst_string,'','',dst_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_BRN1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0x9800), locs[0])
        self.assertTupleEqual((mem_address+2, dst_address), locs[1])
 
    def test_BRNZ(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        dst_address = random.randrange(0, 0x8000) * 2
        dst_string = hex_string4(dst_address)
        dst_string_dollar = '$' + dst_string
        asm_string = 'L_BRNZ1 BRNZ ${}'.format(dst_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'D800','L_BRNZ1','BRNZ','')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),dst_string,'','',dst_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_BRNZ1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0xD800), locs[0])
        self.assertTupleEqual((mem_address+2, dst_address), locs[1])
 
    def test_BRV(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        dst_address = random.randrange(0, 0x8000) * 2
        dst_string = hex_string4(dst_address)
        dst_string_dollar = '$' + dst_string
        asm_string = 'L_BRV1 BRV ${}'.format(dst_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'B800','L_BRV1','BRV','')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),dst_string,'','',dst_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_BRV1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0xB800), locs[0])
        self.assertTupleEqual((mem_address+2, dst_address), locs[1])
 
    def test_BRZ(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        dst_address = random.randrange(0, 0x8000) * 2
        dst_string = hex_string4(dst_address)
        dst_string_dollar = '$' + dst_string
        asm_string = 'L_BRZ1 BRZ ${}'.format(dst_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'C800','L_BRZ1','BRZ','')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),dst_string,'','',dst_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_BRZ1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0xC800), locs[0])
        self.assertTupleEqual((mem_address+2, dst_address), locs[1])

    def test_LI(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        imm = random.randrange(0, 0x8000) * 2
        imm_string = hex_string4(imm)
        imm_string_dollar = '$' + imm_string
        asm_string = 'L_LI1 LI R3,${}'.format(imm_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'30C0','L_LI1','LI','R3')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),imm_string,'','',imm_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_LI1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0x30C0), locs[0])
        self.assertTupleEqual((mem_address+2, imm), locs[1])
 
    def test_LW(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        imm = random.randrange(0, 0x8000) * 2
        imm_string = hex_string4(imm)
        imm_string_dollar = '$' + imm_string
        asm_string = 'L_LW1 LW R7,R4,${}'.format(imm_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'29E0','L_LW1','LW','R7 R4')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),imm_string,'','',imm_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_LW1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0x29E0), locs[0])
        self.assertTupleEqual((mem_address+2, imm), locs[1])
 
    def test_LW_ZERO(self):
        ''' Check when an immediate is set to zero. '''
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        asm_string = 'L_LW2 LW R1,R7,$00'
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'2878','L_LW2','LW','R1 R7')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),'0000','','','$00')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_LW2', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b0010_100_001_111_000), locs[0])
        self.assertTupleEqual((mem_address+2, 0x0000), locs[1])
 
    def test_MV(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        asm_string = 'L_MV1 MV R5,R4'
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'2160','L_MV1','MV','R5 R4')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_MV1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0x2160), locs[0])
 
    def test_NOT(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        asm_string = 'L_NOT1 NOT R7,R7'
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'81F8','L_NOT1','NOT','R7 R7')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_NOT1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b1000_000_111_111_000), locs[0])
 
    def test_OR(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_OR1 OR R6,R1,R6', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'A18E','L_OR1','OR','R6 R1 R6')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_OR1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b1010000_110_001_110), locs[0])

    def test_SLL(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_SLL1 SLL R2,R3,R1', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'C099','L_SLL1','SLL','R2 R3 R1')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_SLL1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b1100000_010_011_001), locs[0])

    def test_SLLI(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        shamt = random.randrange(0, 0x10)
        shamt_string = hex_string4(shamt)
        shamt_string_dollar = '$' + shamt_string
        asm_string = 'L_SLLI1 SLLI R4, R2,${}'.format(shamt_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'C310','L_SLLI1','SLLI','R4 R2')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),shamt_string,'','',shamt_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_SLLI1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b1100001_100_010_000), locs[0])
        self.assertTupleEqual((mem_address+2, shamt), locs[1])
 
    def test_SLT(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_SLT1 SLT R1,R6,R2', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'5072','L_SLT1','SLT','R1 R6 R2')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_SLT1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b0101_000_001_110_010), locs[0])

    def test_SLTI(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        imm = random.randrange(0, 0x8000) * 2
        imm_string = hex_string4(imm)
        imm_string_dollar = '$' + imm_string
        asm_string = 'L_SLTI1 SLTI R4, R7,${}'.format(imm_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'5338','L_SLTI1','SLTI','R4 R7')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),imm_string,'','',imm_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_SLTI1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b0101_001_100_111_000), locs[0])
        self.assertTupleEqual((mem_address+2, imm), locs[1])
 
    def test_SRA(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_SRA1 SRA R6,R4,R7', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'F1A7','L_SRA1','SRA','R6 R4 R7')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_SRA1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b1111_000_110_100_111), locs[0])

    def test_SRAI(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        shamt = random.randrange(0, 0x10)
        shamt_string = hex_string4(shamt)
        shamt_string_dollar = '$' + shamt_string
        asm_string = 'L_SRAI1 SRAI R4, R7,${}'.format(shamt_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'F338','L_SRAI1','SRAI','R4 R7')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),shamt_string,'','',shamt_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_SRAI1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b1111_001_100_111_000), locs[0])
        self.assertTupleEqual((mem_address+2, shamt), locs[1])
 
    def test_SRL(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_SRL1 SRL R1,R2,R3', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'E053','L_SRL1','SRL','R1 R2 R3')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_SRL1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b1110_000_001_010_011), locs[0])

    def test_SRLI(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        shamt = random.randrange(0, 0x10)
        shamt_string = hex_string4(shamt)
        shamt_string_dollar = '$' + shamt_string
        asm_string = 'L_SRLI1 SRLI R4, R5,${}'.format(shamt_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'E328','L_SRLI1','SRLI','R4 R5')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),shamt_string,'','',shamt_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_SRLI1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b1110_001_100_101_000), locs[0])
        self.assertTupleEqual((mem_address+2, shamt), locs[1])
 
    def test_STOP(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_STOP1 STOP ', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'FE00','L_STOP1','STOP','')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_STOP1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b1111_111_000_000_000), locs[0])

    def test_SUB(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_SUB1 SUB R6,R7,R0', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'11B8','L_SUB1','SUB','R6 R7 R0')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_SUB1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b0001_000_110_111_000), locs[0])

    def test_SW(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        imm = random.randrange(0, 0x8000) * 2
        imm_string = hex_string4(imm)
        imm_string_dollar = '$' + imm_string
        asm_string = 'L_SW1 SW R5, R7,${}'.format(imm_string)
        a = as240.AsmLine(asm_string, line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+4)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'382F','L_SW1','SW','R5 R7')
        t += '\n'
        t += FORMAT_1.format(hex_string4(mem_address+2),imm_string,'','',imm_string_dollar)
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_SW1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b0011_100_000_101_111), locs[0])
        self.assertTupleEqual((mem_address+2, imm), locs[1])
 
    def test_XOR(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine('L_XOR1 XOR R6,R4,R3', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address),'B1A3','L_XOR1','XOR','R6 R4 R3')
        self.assertEqual(str(a), t)
        mem_val = as240.SymbolTable.lookup_label('L_XOR1', line_number)
        self.assertEqual(mem_val, mem_address)
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0b1011_000_110_100_011), locs[0])
        
##### Testing argument parsing in preparation for changing to argparse (12 Jun 2019, WAN)
class TestCmdLineParsing(unittest.TestCase):
    
    def setUp(self):
        r_string = str(random.randrange(0, 1000000))
        self.asm_file_basename = f'tmp_{r_string}'
        self.asm_filename = self.asm_file_basename + '.asm'
        self.asm_file_contents = '   .ORG $1000'
        with open(self.asm_filename, 'w') as f:
            print(self.asm_file_contents, file=f)
    
    def tearDown(self):
        import glob, os
        to_delete = glob.glob(self.asm_file_basename + '.*')
        for f in to_delete:
            os.remove(f)
      
    def test_bad_asmfilename(self):
        from unittest.mock import patch
        with patch(target='sys.argv', new=['bad_asm_filename.py', 'asmfilename.asm']):
            with self.assertRaises(SystemExit):
                (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
                
    def test_good_asmfile(self):
        from unittest.mock import patch
        with patch(target='sys.argv', new=['good_asmfile.py', self.asm_filename]):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, self.asm_file_basename + '.list')
            self.assertEqual(file_mem.name, 'memory.hex')
            self.assertEqual(file_sym.name, '/dev/null')
            self.assertEqual(file_mif.name, 'memory.mif')
            file_asm.close()
            file_list.close()
            file_mem.close()
            file_sym.close()
            file_mif.close()
            
    def test_specify_memfile_short(self):
        rand_string = str(random.randrange(0, 100000))
        rand_name = f'tmp_{rand_string}'
        from unittest.mock import patch
        command_line = ['specify_memfile_short.py', self.asm_filename, '-m', rand_name]
        with patch(target='sys.argv', new=command_line):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, self.asm_file_basename + '.list')
            self.assertEqual(file_mem.name, rand_name)
            self.assertEqual(file_sym.name, '/dev/null')
            self.assertEqual(file_mif.name, 'memory.mif')
            file_asm.close()
            file_list.close()
            file_mem.close()
            file_sym.close()
            file_mif.close()    

    def test_specify_memfile_long(self):
        rand_string = str(random.randrange(0, 100000))
        rand_name = f'tmp_{rand_string}'
        from unittest.mock import patch
        command_line = ['specify_memfile_long.py', self.asm_filename, '--mfile', rand_name]
        with patch(target='sys.argv', new=command_line):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, self.asm_file_basename + '.list')
            self.assertEqual(file_mem.name, rand_name)
            self.assertEqual(file_sym.name, '/dev/null')
            self.assertEqual(file_mif.name, 'memory.mif')
            file_asm.close()
            file_list.close()
            file_mem.close()
            file_sym.close()
            file_mif.close()    
            
    def test_specify_listfile_short(self):
        rand_string = str(random.randrange(0, 100000))
        rand_name = f'tmp_{rand_string}'
        from unittest.mock import patch
        command_line = ['specify_listfile_short.py', self.asm_filename, '-l', rand_name]
        with patch(target='sys.argv', new=command_line):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, rand_name)
            self.assertEqual(file_mem.name, 'memory.hex')
            self.assertEqual(file_sym.name, '/dev/null')
            self.assertEqual(file_mif.name, 'memory.mif')
            file_asm.close()
            file_list.close()
            file_mem.close()
            file_sym.close()
            file_mif.close()    

    def test_specify_listfile_long(self):
        rand_string = str(random.randrange(0, 100000))
        rand_name = f'tmp_{rand_string}'
        from unittest.mock import patch
        command_line = ['specify_listfile_long.py', self.asm_filename, '--listfile', rand_name]
        with patch(target='sys.argv', new=command_line):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, rand_name)
            self.assertEqual(file_mem.name, 'memory.hex')
            self.assertEqual(file_sym.name, '/dev/null')
            self.assertEqual(file_mif.name, 'memory.mif')
            file_asm.close()
            file_list.close()
            file_mem.close()
            file_sym.close()
            file_mif.close()    
            
    def test_specify_symfile_short(self):
        rand_string = str(random.randrange(0, 100000))
        rand_name = f'tmp_{rand_string}'
        from unittest.mock import patch
        command_line = ['specify_symfile_short.py', self.asm_filename, '-s', rand_name]
        with patch(target='sys.argv', new=command_line):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, self.asm_file_basename + '.list')
            self.assertEqual(file_mem.name, 'memory.hex')
            self.assertEqual(file_sym.name, rand_name)
            self.assertEqual(file_mif.name, 'memory.mif')
            file_asm.close()
            file_list.close()
            file_mem.close()
            file_sym.close()
            file_mif.close()    

    def test_specify_symfile_long1(self):
        rand_string = str(random.randrange(0, 100000))
        rand_name = f'tmp_{rand_string}'
        from unittest.mock import patch
        command_line = ['specify_symfile_long1.py', self.asm_filename, '--symfile', rand_name]
        with patch(target='sys.argv', new=command_line):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, self.asm_file_basename + '.list')
            self.assertEqual(file_mem.name, 'memory.hex')
            self.assertEqual(file_sym.name, rand_name)
            self.assertEqual(file_mif.name, 'memory.mif')
            file_asm.close()
            file_list.close()
            file_mem.close()
            file_sym.close()
            file_mif.close()    
            
    def test_specify_symfile_long2(self):
        rand_string = str(random.randrange(0, 100000))
        rand_name = f'tmp_{rand_string}'
        from unittest.mock import patch
        command_line = ['specify_symfile_long2.py', self.asm_filename, '--symbolfile', rand_name]
        with patch(target='sys.argv', new=command_line):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, self.asm_file_basename + '.list')
            self.assertEqual(file_mem.name, 'memory.hex')
            self.assertEqual(file_sym.name, rand_name)
            self.assertEqual(file_mif.name, 'memory.mif')
            file_asm.close()
            file_list.close()
            file_mem.close()
            file_sym.close()
            file_mif.close()    
            
    def test_specify_miffile(self):
        rand_string = str(random.randrange(0, 100000))
        rand_name = f'tmp_{rand_string}'
        from unittest.mock import patch
        command_line = ['specify_miffile.py', self.asm_filename, '--miffilename', rand_name]
        with patch(target='sys.argv', new=command_line):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, self.asm_file_basename + '.list')
            self.assertEqual(file_mem.name, 'memory.hex')
            self.assertEqual(file_sym.name, '/dev/null')
            self.assertEqual(file_mif.name, rand_name)
            file_asm.close()
            file_list.close()
            file_mem.close()
            file_sym.close()
            file_mif.close()    
            
    def test_specify_stdout_listonly(self):
        from unittest.mock import patch
        command_line = ['stdout_listonly.py', self.asm_filename, '-o']
        with patch(target='sys.argv', new=command_line):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, '<stdout>')
            self.assertEqual(file_mem.name, '/dev/null')
            self.assertEqual(file_sym.name, '/dev/null')
            self.assertEqual(file_mif.name, '/dev/null')
        file_asm.close()
        file_list.close()
        file_mem.close()
        file_sym.close()
        file_mif.close()    

    def test_specify_stdout_plusall(self):
        rand_string = str(random.randrange(0, 100000))
        rand_name = f'tmp_{rand_string}'
        from unittest.mock import patch
        command_line = ['specify_stdout_plusall.py', self.asm_filename, '-o',
                        '-m', rand_name + '.mem', '-s', rand_name + '.sym',
                        '--miffilename', rand_name + '.mif']
        with patch(target='sys.argv', new=command_line):
            (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
            self.assertEqual(file_asm.name, self.asm_filename)
            self.assertEqual(file_list.name, '<stdout>')
            self.assertEqual(file_mem.name, rand_name + '.mem')
            self.assertEqual(file_sym.name, rand_name + '.sym')
            self.assertEqual(file_mif.name, rand_name + '.mif')
            file_asm.close()
            file_list.close()
            file_mem.close()
            file_sym.close()
            file_mif.close()  
            
    def test_numArgs_too_few(self):
        from unittest.mock import patch
        with patch(target='sys.argv', new=['numArgs_too_few.py']):
            with self.assertRaises(SystemExit):
                (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
                
    def test_numArgs_too_many(self):
        from unittest.mock import patch
        with patch(target='sys.argv', new=['numArgs_too_many.py', self.asm_filename, 'bad.asm']):
            with self.assertRaises(SystemExit):
                (file_asm, file_list, file_mem, file_sym, file_mif) = as240.parse_command_line()
                
##### Tests created because of bugs discoverd
class TestAsmLine_Bugs(unittest.TestCase):    
    def test_DW_zero_bug(self):
        mem_address = random.randrange(0, 0x8000) * 2
        line_number = 10
        a = as240.AsmLine(' .DW $0000', line_number, mem_address)
        self.assertEqual(a.next_mem_address(), mem_address+2)
        a.assemble()
        t = FORMAT_1.format(hex_string4(mem_address), '0000', '', '.DW', '$0000')
        self.assertEqual(str(a), t)  
        locs = a.mem_locs()
        self.assertTupleEqual((mem_address, 0), locs[0])


if __name__ == '__main__':
    unittest.main()