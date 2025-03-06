import re, os, sys
from collections import defaultdict
import struct

def process_combined_sources(memory_dump_path, mmio_trace_path):
    if not os.path.isfile(memory_dump_path):
        print(f"BAR dump file not found: {memory_dump_path}")
        sys.exit(1)
    if not os.path.isfile(mmio_trace_path):
        print(f"MMIOTrace file not found: {mmio_trace_path}")
        sys.exit(1)
    
    static_values = {}
    with open(memory_dump_path, 'rb') as f:
        data = f.read()
        for offset in range(0, min(len(data), 0x1000), 4):
            value = struct.unpack('<I', data[offset:offset+4])[0]
            if value != 0:
                static_values[offset] = value

    read_patterns = defaultdict(list)
    write_patterns = defaultdict(list)
    
    pattern = r"(R|W)\s+4\s+([\d.]+)\s+2\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+0x0\s+0"
    
    with open(mmio_trace_path, 'r') as file:
        ### CHANGE THIS LINE ###
        bar_address = 0x00000000
        if bar_address == 0x00000000 or not (0x00000000 <= bar_address <= 0xFFFFFFFF):
            print("BAR address is invalid, please change it to your actual BAR address (line 28)")
            sys.exit(1)
        for line in file:
            match = re.match(pattern, line)
            if match:
                op_type = match.group(1)
                address = int(match.group(3), 16)
                data = int(match.group(4), 16)
                offset = address - bar_address
                
                if op_type == 'R':
                    read_patterns[offset].append(data)
                else:
                    # Writes usually aren't needed since it's handled by the driver (for the most part)
                    write_patterns[offset].append(data)

    sv_code = ["""module pcileech_bar_impl_combined(
    input               rst,
    input               clk,
    // incoming BAR writes:
    input [31:0]        wr_addr,
    input [3:0]         wr_be,
    input [31:0]        wr_data,
    input               wr_valid,
    // incoming BAR reads:
    input [87:0]        rd_req_ctx,
    input [31:0]        rd_req_addr,
    input               rd_req_valid,
    input [31:0]        base_address_register,
    // outgoing BAR read replies:
    output reg [87:0]   rd_rsp_ctx,
    output reg [31:0]   rd_rsp_data,
    output reg          rd_rsp_valid
);

    reg [87:0]      drd_req_ctx;
    reg [31:0]      drd_req_addr;
    reg             drd_req_valid;
    reg [31:0]      dwr_addr;
    reg [31:0]      dwr_data;
    reg             dwr_valid;"""]

    dynamic_regs = set()
    for offset in write_patterns.keys():
        if offset in read_patterns and len(set(read_patterns[offset])) > 1:
            dynamic_regs.add(offset)
            sv_code.append(f"    reg [31:0]      reg_{offset:04x};")

    sv_code.append("""
    always @ (posedge clk) begin
        if (rst) begin""")

    for offset in dynamic_regs:
        sv_code.append(f"            reg_{offset:04x} <= 32'h0;")

    sv_code.append("""        end else begin
            drd_req_ctx <= rd_req_ctx;
            drd_req_valid <= rd_req_valid;
            dwr_valid <= wr_valid;
            drd_req_addr <= rd_req_addr;
            rd_rsp_ctx <= drd_req_ctx;
            rd_rsp_valid <= drd_req_valid;
            dwr_addr <= wr_addr;
            dwr_data <= wr_data;

            if (drd_req_valid) begin
                case (({drd_req_addr[31:24], drd_req_addr[23:16], drd_req_addr[15:08], drd_req_addr[07:00]} - (base_address_register & 32'hFFFFFFF0)) & 32'h00FF)""")

    all_offsets = set(static_values.keys()) | set(read_patterns.keys())
    for offset in sorted(all_offsets):
        if offset in dynamic_regs:
            sv_code.append(f"                    16'h{offset:04X}: rd_rsp_data <= reg_{offset:04x};")
        elif offset in read_patterns:
            sv_code.append(f"                    16'h{offset:04X}: rd_rsp_data <= 32'h{read_patterns[offset][0]:08X};")
        elif offset in static_values:
            sv_code.append(f"                    16'h{offset:04X}: rd_rsp_data <= 32'h{static_values[offset]:08X};")

    sv_code.append("""                    default: rd_rsp_data <= 32'h00000000;
                endcase
            end else if (dwr_valid) begin
                case (({dwr_addr[31:24], dwr_addr[23:16], dwr_addr[15:08], dwr_addr[07:00]} - (base_address_register & 32'hFFFFFFF0)) & 32'h00FF)""")

    for offset in sorted(write_patterns.keys()):
        if offset in dynamic_regs:
            sv_code.append(f"                    16'h{offset:04X}: reg_{offset:04x} <= dwr_data;")

    sv_code.append("""                    default: ; // No operation for unknown addresses
                endcase
            end else begin
                rd_rsp_data <= 32'h00000000;
            end
        end
    end

endmodule""")

    return "\n".join(sv_code)

if __name__ == "__main__":
    print("MMIO2Verilog Script - Combine RWE & MMIOTrace dump")
    memory_dump_file = input("Enter filename of memory dump (.bin): ")
    mmio_trace_file = input("Enter filename of MMIO Trace log: ")
    
    verilog_code = process_combined_sources(memory_dump_file, mmio_trace_file)
    output_file = "pcileech_tlps128_bar_controller.sv"
    
    with open(output_file, "w") as f:
        f.write(verilog_code)
    print(f"Generated {output_file}")
