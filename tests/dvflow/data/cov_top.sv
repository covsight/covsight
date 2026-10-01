// Coverage test design: one small design that exercises every kind the
// coverage levels collect -- lines/branches (counter + if/else), an
// expression (&&), toggles, a two-state FSM, a covergroup with one hit and
// one unhit bin, and a cover property. Shared by the vlt and xzm tests.
module cov_top;
  logic       clk = 0;
  logic [3:0] count = 0;
  logic       flag = 0;

  typedef enum logic { IDLE, BUSY } state_e;
  state_e state = IDLE;

  always #5 clk = ~clk;

  always @(posedge clk) begin
    count <= count + 1;
    if (count[0] && count[1])
      flag <= 1;
    else
      flag <= 0;
  end

  always @(posedge clk) begin
    case (state)
      IDLE: if (count == 4'd3) state <= BUSY;
      BUSY: if (count == 4'd7) state <= IDLE;
    endcase
  end

  covergroup cg @(posedge clk);
    cp_flag : coverpoint flag {
      bins hit_low  = {0};
      bins hit_high = {1};
    }
    cp_count : coverpoint count {
      bins lo    = {[0:7]};
      bins never = {15};
    }
  endgroup
  cg cg_i = new;

  cover property (@(posedge clk) count == 4'd5);

  initial begin
    if ($test$plusargs("trace")) begin
      $dumpfile("waves.fst");
      $dumpvars(0, cov_top);
    end
    #100;
    $display("cov_top done count=%0d", count);
    $finish;
  end
endmodule
