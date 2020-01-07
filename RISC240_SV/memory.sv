/*
 * File: memory.sv
 * Created: 14 Nov 2014
 * Modules contained: memory
 */
 
 /*
 * module: memory
 *
 *  This is a full sized memory for the RISC240 and initialized with
 *  a memory.hex file.
 *
 */
module memory_simulation
  (input logic        clock, enable,
   input wr_enable_t  we_L,
   input rd_enable_t  re_L,
   inout wire  [15:0] data,
   input logic [15:0] address);
   
  logic [15:0] mem [16'hffff:16'h0000];
  
  assign data = (enable & (re_L === MEM_RD)) ? mem[address] : 16'bz;
    
  always @(posedge clock)
    if (enable & (we_L === MEM_WR))
      mem[address] <= data;
      
//  initial $readmemh("memory.hex", mem);
  /*
   * Let me explain why not $readmemh.
   * RISC240 memory is byte addressable, but all reads are 16-bits at a time.
   * Therefore, the memory array has to have a 16-bit data bus.  But, the 
   * memory.hex file has one line per 16-bit word (i.e. two bytes).
   * $readmemh will take the first line and put it at Mem[0] and the second 
   * line at Mem[1], etc.
   * We want the first lien at Mem[0] and the second line at Mem[2].
   * Therefore, custom memory loading code.
   */
  initial begin
    int fd, status;
    logic [14:0] addr;
    logic [15:0] value;
    fd = $fopen("memory.hex", "r");
    if (fd) begin
      addr = 16'h0;
      while (!$feof(fd)) begin
        status = $fscanf(fd,"%h", value);
        if (status == 1) begin
          mem[{addr, 1'b0}] = value;
          addr += 1;
        end
      end
    end else begin
      $display("File not found: memory.hex must be in the local directory");
      $fflush();
      $finish(2);
    end
    
    $fclose(fd);
  end

endmodule : memory_simulation

 
 /* 
 * module: memorySystem
 *
 * This is our data memory, with combinational read and synchronous write.
 * Each memory word is 16 bits, and there is a 16 bit address space.
 */
 
 `include "constants.sv"
 
module memorySystem (
   inout  [15:0]   data,
   input logic [15:0]   address,
   input wr_enable_t we_L,
   input rd_enable_t re_L,
   input logic          clock); 

`ifdef synthesis
   logic pmem_en, dmem_en;
   logic rden, wren;
   logic [15:0] d_data_out, p_data_out;

   // Address decoders to enable individual memory modules
   assign pmem_en = (address[15:10] == 6'h00);
   assign dmem_en = (address[15:10] == 6'h01);
   
   assign rden = (re_L === MEM_RD) ? pmem_en : 0;
   assign wren = (we_L === MEM_WR) ? pmem_en : 0;

   always_comb begin
     data = 16'bz;
     if (re_L === MEM_RD)
       if (pmem_en)
         data = p_data_out;
       else if (dmem_en)
         data = d_data_out;
   end
   
   // Memory Map: Program memory from $0000 to $03FF
   bram pmem(.clock,
             .rden,
             .wren,
             .data,
             .q(p_data_out),
             .address(address[9:0]));

   // Memory Map: Data memory from $0400 to $07FF
   memory1024x16 dmem(.clock,
                      .enable(dmem_en), 
                      .we_L,
                      .data_in(data),
                      .data_out(d_data_out),
                      .address(address[9:0]));
   
`else
  // full sized memory for simulation, initialized with memory.hex
  memory_simulation  mem(
                        .clock(clock), 
                        .enable(1'b1), 
                        .we_L(we_L), 
                        .re_L(re_L), 
                        .data(data), 
                        .address(address));
`endif

endmodule : memorySystem
