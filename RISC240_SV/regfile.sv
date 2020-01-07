/*
 * File: regfile.sv
 * Created: 23 October 2009
 * Modules contained: reg_file
 *
 * Update History:
 * 17 November 2009: Minor modification to facilitate synthesis (mcbender)
 * 4 November 2009: Minor spacing modifications (mcbender)
 * 23 October 2009: Moved to its own file (mcbender)
 * 12 October 2009: Fixed typo.
 * 7 October 2009: Added demux and updated architecture accordingly
 * 3 October 2009: Removed output port C, cleaned up style a little
 * 9 June 1999 : Added 4 remaining registers 
 * 13 Oct 2010: Updated always to always_comb and always_ff.Renamed to.sv(abeera) 
 * 17 Oct 2010: Updated to use enums instead of define's (iclanton)
 * 17 April 2013: Made output multiplexers into explicit components (wnace)
 * 8 Mar 2019: Changed to fit RISC240 spec (pbannai)
 * 3 Apr 2019: Hard-wired r0 to 0 (saugatag)
*/

/* 
 * module: reg_file
 *
 * The RISC240's register file, which currently consists of eight (8)
 * 16-bit registers.  (It has at some points had fewer due to lack of
 * space on various FPGAs.)
 *
 * This register file has three outputs, the two registers A and B used
 * by the processor itself, and a third port for viewing purposes during
 * debugging.
*/
module reg_file(
   output logic [15:0] outRS1,
   output logic [15:0] outRS2,
   output logic [127:0] outView,
   input [15:0]      in,
   input [2:0]       selRD,
   input [2:0]       selRS1,
   input [2:0]       selRS2,
   input             load_L, 
   input             reset_L,
   input             clock);
   
   logic [15:0] r0, r1, r2, r3, r4, r5, r6, r7;
   logic [7:0]  reg_enable_lines_L;
   
   assign r0 = 16'b0;
   register #(.WIDTH(16)) reg1(.out(r1), .in(in), .load_L(reg_enable_lines_L[1]),
                               .clock(clock), .reset_L(reset_L));
   register #(.WIDTH(16)) reg2(.out(r2), .in(in), .load_L(reg_enable_lines_L[2]),
                               .clock(clock), .reset_L(reset_L));
   register #(.WIDTH(16)) reg3(.out(r3), .in(in), .load_L(reg_enable_lines_L[3]),
                               .clock(clock), .reset_L(reset_L));
   register #(.WIDTH(16)) reg4(.out(r4), .in(in), .load_L(reg_enable_lines_L[4]),
                               .clock(clock), .reset_L(reset_L));
   register #(.WIDTH(16)) reg5(.out(r5), .in(in), .load_L(reg_enable_lines_L[5]),
                               .clock(clock), .reset_L(reset_L));
   register #(.WIDTH(16)) reg6(.out(r6), .in(in), .load_L(reg_enable_lines_L[6]),
                               .clock(clock), .reset_L(reset_L));
   register #(.WIDTH(16)) reg7(.out(r7), .in(in), .load_L(reg_enable_lines_L[7]),
                               .clock(clock), .reset_L(reset_L));

   demux #(.OUT_WIDTH(8), .IN_WIDTH(3), .DEFAULT(1))
         reg_en_decoder (.in(load_L), .sel(selRD), .out(reg_enable_lines_L));

   mux8to1 #(.WIDTH(16)) muxRS1(.inA(r0), .inB(r1), .inC(r2), .inD(r3), .inE(r4), .inF(r5), .inG(r6), .inH(r7), 
                              .out(outRS1), .sel(selRS1));

   mux8to1 #(.WIDTH(16)) muxRS2(.inA(r0), .inB(r1), .inC(r2), .inD(r3), .inE(r4), .inF(r5), .inG(r6), .inH(r7), 
                              .out(outRS2), .sel(selRS2));

   assign outView = {r7, r6, r5, r4, r3, r2, r1, r0};
                   
endmodule : reg_file
