# MMIO2Verilog
Python script for converting mmiotrace logs (/sys/kernel/debug/tracing/trace_marker) to a functional BAR controller to handle driver <-> firmware communication for the PCILeech FPGA base.

⚠️ Using this tool in its current state will most likely cause a kernel panic or drvscan fail to some degree.

Currently only handles read operations (rd_rsp_data).

Sample input:
```
R 4 2456.033280 2 0xf7801000 0x53920223 0x0 0
R 4 2456.033290 2 0xf7800580 0x81f0883f 0x0 0
R 4 2456.033292 2 0xf7800580 0x81f0883f 0x0 0
W 4 2456.033294 2 0xf7800580 0xc000883f 0x0 0
R 4 2456.033296 2 0xf7800580 0xc000883f 0x0 0
```

Sample output:
```sv
if (drd_req_valid) begin
    case (({drd_req_addr[31:24], drd_req_addr[23:16], drd_req_addr[15:08], drd_req_addr[07:00]} - (base_address_register & 32'hFFFFFFF0)) & 32'h00FF)
        16'h-EF000 : rd_rsp_data <= 32'h53920223;
        16'h-EFA80 : rd_rsp_data <= 32'h81F0883F;
        16'h-EFA80 : rd_rsp_data <= 32'h81F0883F;
        16'h-EFA80 : rd_rsp_data <= 32'hC000883F;
        16'h-EFA80 : rd_rsp_data <= 32'h80008821;
```
