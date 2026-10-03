// 01-code-basics: a saturating accumulator.
//
// op 0 holds, 1 adds din, 2 subtracts din (stopping at zero), 3 clears.
// An add that overflows saturates q at all-ones and raises sat.
module acc #(parameter int W = 8) (
  input  logic         clk,
  input  logic         rst_n,
  input  logic [1:0]   op,
  input  logic [W-1:0] din,
  output logic [W-1:0] q,
  output logic         sat
);
  localparam logic [1:0] HOLD = 2'd0, ADD = 2'd1, SUB = 2'd2, CLEAR = 2'd3;

  logic [W:0] next;     // one extra bit catches an add's carry out

  always_comb begin
    case (op)
      ADD:     next = {1'b0, q} + din;
      SUB:     next = (din > q) ? '0 : {1'b0, q} - din;
      default: next = {1'b0, q};
    endcase
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n)
      q <= '0;
    else if (op == CLEAR)
      q <= '0;
    else if (op == ADD && next[W])
      q <= '1;                          // saturate
    else
      q <= next[W-1:0];
  end

  assign sat = (q == '1);
endmodule
