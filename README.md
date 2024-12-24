# MMIO2Verilog
Python script for converting mmiotrace logs (/sys/kernel/debug/tracing/trace_marker) to a functional BAR controller to handle driver <-> firmware communication for the PCILeech FPGA base. Part of this script borrows functionality from [zelz69's Bar2Verilog](https://github.com/zelz69/Bar2Verilog) repository.

Ensure your MMIOTrace is verbose enough, use the device as intended while debugging to produce the most results.

⚠️ This tool generates a static BAR dump for reads, and attempts to identify dynamic relationship(s) between reads & writes. In its current state, it would most likely cause a drvscan fail and trigger a warning within Device Manager. Please review the output and make changes based on your own testing.

### Constraints
- Only supports a single BAR
- No MAC randomization support
- Identified relationships between memory addresses may be invalid

Sample MMIO input:
```
R 4 2456.105919 2 0xf780010c 0x4c02 0x0 0
R 4 2456.130642 2 0xf7800114 0x1 0x0 0
R 4 2456.132390 2 0xf7800200 0x0 0x0 0
R 4 2456.137697 2 0xf7800204 0x7804 0x0 0
...
R 4 2550.265744 2 0xf7807010 0xff001f 0x0 0
R 4 2456.132385 2 0xf7807014 0xffffff03 0x0 0
```

Sample output:
```sv
if (drd_req_valid) begin
    case (({drd_req_addr[31:24], drd_req_addr[23:16], drd_req_addr[15:08], drd_req_addr[07:00]} - (base_address_register & 32'hFFFFFFF0)) & 32'h00FF)
        16'h010C : rd_rsp_data <= 32'h00004C02;
        16'h0114 : rd_rsp_data <= 32'h00000001;
        16'h0200 : rd_rsp_data <= 32'h00000000;
        16'h0204 : rd_rsp_data <= 32'h00007800;
        ...
        16'h7010 : rd_rsp_data <= 32'h00FF001F;
        16'h7014 : rd_rsp_data <= 32'hFFFFFF03;
        default: rd_rsp_data <= 32'h00000000;
    endcase
end
```
