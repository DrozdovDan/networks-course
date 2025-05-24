import random


def calculate_crc(data: bytes) -> int:
    crc = 0xFFFFFFFF
    polynomial = 0xEDB88320

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ polynomial
            else:
                crc >>= 1

    return crc ^ 0xFFFFFFFF


def introduce_error(data: bytes, num_errors: int = 1) -> bytes:
    data_list = list(data)
    data_len = len(data_list)
    for _ in range(num_errors):
        byte_index = random.randint(0, data_len - 1)
        bit_index = random.randint(0, 7)
        data_list[byte_index] ^= 1 << bit_index
    return bytes(data_list)


def process_text(text: str, packet_size: int = 5):
    bytes_data = text.encode()
    packets = [bytes_data[i:i + packet_size] for i in range(0, len(bytes_data), packet_size)]

    for i, packet in enumerate(packets):
        crc = calculate_crc(packet)
        encoded_packet = packet + crc.to_bytes(4, byteorder='big')
        print(f"Packet {i + 1} - Data: {packet}, Encoded: {encoded_packet}, CRC: {crc:08X}")


def test_main(packet_size: int = 5, num_errors: int = 1):
    text = "Hello, this is a test message to demonstrate CRC checking."
    bytes_data = text.encode()
    packets = [bytes_data[i:i + packet_size] for i in range(0, len(bytes_data), packet_size)]

    for i, packet in enumerate(packets):
        crc = calculate_crc(packet)
        encoded_packet = packet + crc.to_bytes(4, byteorder='big')

        if i % 2 == 0:
            packet_with_error = introduce_error(encoded_packet, num_errors)
            data_with_error = packet_with_error[:-4]
            assert calculate_crc(
                packet_with_error) != crc, f"CRC mismatch not detected. Data: {packet}. " \
                                           f"Data with error: {data_with_error}"


def test_crc_with_error():
    text = "Hello, World!"
    bytes_data = text.encode()
    packets = [bytes_data[i:i + 5] for i in range(0, len(bytes_data), 5)]

    for packet in packets:
        crc = calculate_crc(packet)
        packet_with_error = introduce_error(packet, 1)
        assert crc != calculate_crc(packet_with_error), "Failed to detect error in packet"


if __name__ == "__main__":
    input_text = "Hello, this is a test message to demonstrate CRC checking. GOIDA!!!"
    print("=" * 30 + "CRC CHECKING DEMONSTRATION" + "=" * 30)
    process_text(input_text)
    print("=" * 30 + "TESTS" + "=" * 30)
    test_crc_with_error()
    test_main()
    print("All tests passed!")
