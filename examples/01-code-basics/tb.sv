// Testbench for acc. +TEST=basic adds, subtracts and clears with small
// values; +TEST=full also overflows an add and underflows a subtract.
// Every result is checked against a model; a mismatch ends the run with
// $fatal, which fails the test.
module tb;
  // verilator coverage_off
  // (the testbench's own code stays out of the coverage figures)
  localparam int W = 8;

  logic         clk = 0, rst_n = 0;
  logic [1:0]   op = 0;
  logic [W-1:0] din = 0, q;
  logic         sat;
  int           model = 0;

  acc #(.W(W)) dut (.*);

  always #5 clk = ~clk;

  // Drive on the falling edge, check after the rising edge.
  task automatic apply(logic [1:0] o, int d);
    @(negedge clk);
    op = o;
    din = W'(d);
    @(posedge clk);
    #1;
    case (o)
      1: model = (model + d > 255) ? 255 : model + d;
      2: model = (d > model) ? 0 : model - d;
      3: model = 0;
      default: ;
    endcase
    if (q !== W'(model) || sat !== (model == 255))
      $fatal(1, "op=%0d din=%0d: q=%0d sat=%0b, expected q=%0d", o, d, q, sat, model);
  endtask

  initial begin
    string test;
    if (!$value$plusargs("TEST=%s", test)) test = "basic";

    repeat (2) @(posedge clk);
    rst_n = 1;

    apply(1, 10);       // add
    apply(1, 20);
    apply(0, 0);        // hold
    apply(2, 5);        // subtract
    apply(3, 0);        // clear

    if (test == "full") begin
      apply(1, 200);
      apply(1, 100);    // overflows: saturates
      apply(2, 255);
      apply(1, 3);
      apply(2, 9);      // more than q: stops at zero
    end

    $display("tb: test %s passed", test);
    $finish;
  end
endmodule
