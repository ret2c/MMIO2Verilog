import re

# Parse MMIO trace file
def parse_mmiotrace(file_path):
    mmio_operations = []
    pattern = r"(W|R)\s+(\d+)\s+([\d.]+)\s+(\d+)\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(\d+)"
    
    with open(file_path, 'r') as file:
        for line in file:
            match = re.match(pattern, line)
            if match:
                op_type = match.group(1)  # W/R
                address = int(match.group(5), 16)  # Address
                data = int(match.group(6), 16)  # Data
                mmio_operations.append((op_type, address, data))
    return mmio_operations

# Generate Verilog BAR controller logic
def generate_verilog_bar_controller(mmio_operations, bar_base):
    verilog_logic = []
    verilog_logic.append("if (drd_req_valid) begin")
    verilog_logic.append("    case (({drd_req_addr[31:24], drd_req_addr[23:16], drd_req_addr[15:08], drd_req_addr[07:00]} - (base_address_register & 32'hFFFFFFF0)) & 32'h00FF)")

    for op, address, data in mmio_operations:
        offset = address - bar_base
        if op == "R": # Script only supports Read operations
            verilog_logic.append(f"        16'h{offset:04X} : rd_rsp_data <= 32'h{data:08X};")

    verilog_logic.append("        default: rd_rsp_data <= 32'h00000000;")
    verilog_logic.append("    endcase")
    verilog_logic.append("end")

    return "\n".join(verilog_logic)

if __name__ == "__main__":
    mmio_trace_file = input("Enter filename of MMIO Trace log: ")
    bar_base = 0x00000000  # Replace with BAR from lspci (Region (X): 00000000) or Shadow CFG
    mmio_ops = parse_mmiotrace(mmio_trace_file)
    verilog_bar_controller = generate_verilog_bar_controller(mmio_ops, bar_base)

    output_file_path = "pcileech_tlps128_bar_controller.sv"
    with open(output_file_path, "w") as output_file:
        output_file.write(verilog_bar_controller)

    print(f"BAR controller logic generated and saved to {output_file_path}.")
