/*
 * File: alu.v
 * Created: 11/20/1998
 * Modules contained: ALU
 * 
 * Changelog:
 * 4/16/2001: Reverted to base code. (verBurg)
 * 5/6/2001: Fixed the overflow bug, made all the constants symbolic.
 * 11/30/01: Fixed the fix to the overflow bug. (cpa)
 * 03 October 2009: Cleaned up code formatting (mcbender)
 * 07 October 2009: Reformatted ALU entirely; note change to C flag in A-B-1 (mcbender)
 * 13 October 2009: Removed tabs and fixed spacing (mcbender)
 * 18 Oct 2009: Removed old ALU, changed constant names (mcbender)
 * 31 Oct 2009: Fixed naming style for ports & variables (mcbender)
 * 4 Nov 2009: Minor spacing modifications (mcbnender)
 * 13 Oct 2010: Updated always to always_comb and always_ff.Renamed to.sv(abeera) 
 * 17 Oct 2010: Updated to use enums instead of define's (iclanton)
 * 9  Mar 2019: Changed to fit RISC240 spec (pbannai)
 * 23 Apr 2019: Fixed shift to implement barrel shifting (pbannai)
*/

`include "constants.sv"


/*
 * module alu
 *
 * This is the ALU of the RISC240.  Depending on the opcode field it
 * performs a variety of operations.  (See constants.v for a listing
 * of the opcodes.)
 * The condition codes are ordered as ZCNV.
*/
module alu (
   output logic [15:0] out,
   output logic [3:0]  condCodes,
   input [15:0]      inA,
   input [15:0]      inB,
   input  alu_op_t      opcode);

   logic Z, C, N, V;
   
   always_comb begin
      Z = 0;
      C = 0;
      N = 0;
      V = 0;
      case (opcode)
         F_A_PLUS_B : begin
            {C, out} = inA + inB;                     // A+B 
            V = (inA[15] & inB[15] & ~out[15]) | (~inA[15] & ~inB[15] & out[15]);
         end
         F_A_MINUS_B : begin
            out = inA - inB;                          // A-B (set carry below)
            C = (inB >= inA);
            V = (inA[15] & ~inB[15] & ~out[15]) | (~inA[15] & inB[15] & out[15]);
         end
         F_A : begin
            out = inA;                                // Pass A
         end
         F_B : begin
            out = inB;                                // Pass B
         end
         F_A_PLUS_2 : begin
            {C, out} = inA + 2;                       // A+1 
            V = (inA[15] & ~out[15]);
         end
         F_A_LT_B: begin                              // A < B
            if (inA[15] == inB[15]) 
               out = inA < inB;
            else if(inA[15] && !inB[15]) // A neg, B pos
               out = 1;
            else 
               out = 0;
         end
         F_A_NOT : begin
            out = ~inA;                               // not A
         end
         F_A_AND_B : begin
            out = inA & inB;                          // A and B
         end
         F_A_OR_B : begin
            out = inA | inB;                          // A or B
         end
         F_A_XOR_B : begin
            out = inA ^ inB;                          // A xor B
         end
         F_A_SHL : begin
            out = inA << inB;
         end
         F_A_LSHR : begin
            out = inA >> inB;
         end
         F_A_ASHR : begin
            out = $signed(inA) >>> inB;
	 end
         default: out = inA;	
      endcase

      N = out[15];
      Z = (out === 16'h0000)?1:0;
    
      condCodes = {Z, C, N, V};
   end
endmodule
