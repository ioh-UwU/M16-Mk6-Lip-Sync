from os import listdir
from PIL import Image
from re import sub

# Comfortable maximum for generated FRAME_DATA for the Raspberry Pi Pico 2W. 
# This is equivalent to upwards of 300+ unique frames and should not need to be changed.
OUTPUT_FILE_MAX_KB = 150

VISEME_KEYS = ("Viseme_PP", "Viseme_FF", "Viseme_TH", "Viseme_SS", "Viseme_A", "Viseme_E", "Viseme_I", "Viseme_O", "Viseme_U")
SILENCE_KEYS = ("SIL", "BL")

N = 512
F = 18
THRESHOLD = 2
NIL = N

WIDTH = 64
HEIGHT = 16

def u16(n):
    return int(n).to_bytes(2, "big")

def u32(n):
    return int(n).to_bytes(4, "big", signed=False)

def wrap(payload: bytes) -> bytes:
    data = u16(len(payload)) + payload
    out = bytearray([0x01])

    for b in data:
        if 0x00 < b < 0x04:
            out += bytes([0x02, b ^ 0x04])
        else:
            out.append(b)

    out.append(0x03)
    return bytes(out)

def unwrap(packet: bytes) -> bytes:
    if packet and packet[0] == 0x01 and packet[-1] == 0x03:
        packet = packet[1:-1]

    out = bytearray()
    i = 0

    while i < len(packet):
        if packet[i] == 0x02 and i + 1 < len(packet):
            out.append(packet[i + 1] ^ 0x04)
            i += 2
        else:
            out.append(packet[i])
            i += 1

    return bytes(out[2:]) if len(out) >= 2 else bytes(out)

def crc32_coolledux(data: bytes) -> int:
    poly = 0x04C11DB7
    crc = 0xFFFFFFFF

    for b in data:
        for _ in range(8):
            crc_high = crc & 0x80000000
            data_high = b & 0x80
            crc = (crc << 1) & 0xFFFFFFFF

            if crc_high:
                crc ^= poly
            if data_high:
                crc ^= poly

            b = (b << 1) & 0xFF

    return crc & 0xFFFFFFFF

def xor_checksum(data: bytes) -> int:
    x = 0
    for b in data:
        x ^= b
    return x & 0xFF

def lzss_compress(src: bytes) -> bytes:
    text_buf = bytearray(N + F - 1)
    lson = [NIL] * (N + 1)
    rson = [NIL] * (N + 257)
    dad = [NIL] * (N + 1)

    match_position = 0
    match_length = 0

    def insert_node(r):
        nonlocal match_position, match_length

        p = text_buf[r] + N + 1
        lson[r] = NIL
        rson[r] = NIL
        match_length = 0
        cmp_val = 1

        while True:
            if cmp_val >= 0:
                if rson[p] != NIL:
                    p = rson[p]
                else:
                    rson[p] = r
                    dad[r] = p
                    return
            else:
                if lson[p] != NIL:
                    p = lson[p]
                else:
                    lson[p] = r
                    dad[r] = p
                    return

            i = 1

            while i < F:
                cmp_val = text_buf[r + i] - text_buf[p + i]
                if cmp_val != 0:
                    break
                i += 1

            if i > match_length:
                match_position = p
                match_length = i

                if i >= F:
                    dad[r] = dad[p]
                    lson[r] = lson[p]
                    rson[r] = rson[p]
                    dad[lson[p]] = r
                    dad[rson[p]] = r

                    if rson[dad[p]] == p:
                        rson[dad[p]] = r
                    else:
                        lson[dad[p]] = r

                    dad[p] = NIL
                    return

    def delete_node(p):
        if dad[p] == NIL:
            return

        if rson[p] == NIL:
            q = lson[p]
        elif lson[p] == NIL:
            q = rson[p]
        else:
            q = lson[p]

            if rson[q] != NIL:
                while rson[q] != NIL:
                    q = rson[q]

                rson[dad[q]] = lson[q]
                dad[lson[q]] = dad[q]
                lson[q] = lson[p]
                dad[lson[p]] = q

            rson[q] = rson[p]
            dad[rson[p]] = q

        dad[q] = dad[p]

        if rson[dad[p]] == p:
            rson[dad[p]] = q
        else:
            lson[dad[p]] = q

        dad[p] = NIL

    if not src:
        return b""

    for i in range(N + 1, N + 257):
        rson[i] = NIL

    for i in range(N):
        dad[i] = NIL

    out = bytearray()
    code_buf = bytearray(17)
    code_buf[0] = 0
    code_buf_ptr = 1
    mask = 1

    s = 0
    r = N - F
    src_pos = 0
    length = 0

    while length < F and src_pos < len(src):
        text_buf[r + length] = src[src_pos]
        length += 1
        src_pos += 1

    for i in range(1, F + 1):
        insert_node(r - i)

    insert_node(r)

    while True:
        if match_length > length:
            match_length = length

        if match_length <= THRESHOLD:
            match_length = 1
            code_buf[0] |= mask
            code_buf[code_buf_ptr] = text_buf[r]
            code_buf_ptr += 1
        else:
            code_buf[code_buf_ptr] = match_position & 0xFF
            code_buf[code_buf_ptr + 1] = ((match_position >> 4) & 0xF0) | (match_length - 3)
            code_buf_ptr += 2

        mask = (mask << 1) & 0xFF

        if mask == 0:
            out.extend(code_buf[:code_buf_ptr])
            code_buf = bytearray(17)
            code_buf[0] = 0
            code_buf_ptr = 1
            mask = 1

        last_match_length = match_length
        i = 0

        while i < last_match_length and src_pos < len(src):
            delete_node(s)
            c = src[src_pos]
            src_pos += 1

            text_buf[s] = c

            if s < F - 1:
                text_buf[s + N] = c

            s = (s + 1) & (N - 1)
            r = (r + 1) & (N - 1)

            insert_node(r)
            i += 1

        while i < last_match_length:
            delete_node(s)

            s = (s + 1) & (N - 1)
            r = (r + 1) & (N - 1)
            length -= 1

            if length > 0:
                insert_node(r)

            i += 1

        if length <= 0:
            break

    if code_buf_ptr > 1:
        out.extend(code_buf[:code_buf_ptr])

    return bytes(out)

def transfer(v):
    if v >= 238:
        return 15
    if v <= 47:
        return 0
    return ((v - 47) // 14) + 1

def rgb444(r, g, b):
    rr = transfer(r)
    gg = transfer(g)
    bb = transfer(b)
    return bytes([rr, (gg << 4) | bb])

def frame_to_native_bytes(img, width, height):
    img = img.convert("RGBA").resize((width, height), Image.Resampling.NEAREST)
    data = bytearray()

    for x in range(width):
        for y in range(height):
            r, g, b, a = img.getpixel((x, y))

            if a < 128:
                r = g = b = 0

            data += rgb444(r, g, b)

    return bytes(data)

def make_start_packet(program, index=0, count=1, show_count=1):
    payload = b"\x02"
    payload += u32(crc32_coolledux(program))
    payload += u32(len(program))
    payload += bytes([index, count, show_count])
    return wrap(payload)

def generate_frame_data(img:Image):
    inner = bytearray()
    inner += b"\x03\x01\x00\x00\x00\x00\x00\x00\x00"
    inner += u16(0) + u16(0)
    inner += u16(WIDTH) + u16(HEIGHT)
    inner += b"\x00"
    inner += u16(1)        # 1 Frame
    inner += u16(20)       # 20ms display time
    inner += frame_to_native_bytes(img, WIDTH, HEIGHT)

    content_block = u32(len(inner) + 4) + inner
    program = bytearray(b"\x00" * 8 + b"\x01\x00") + content_block
    compressed = lzss_compress(bytes(program))
    
    return make_start_packet(program, index=0), compressed

frame_data = {}
def preprocess_frame_data():
    # Idle silent and blinking frames
    # Should be formatted SIL_#.png and BL_#.png (sequential)
    for image in listdir("visemes/SIL"):
        if image.endswith(".png"):
            if image.startswith(SILENCE_KEYS):
                frame_data[f"{image}"[:-4]] = generate_frame_data(Image.open(f"visemes/SIL/{image}"))
            else:
                print(f"{image}'s file name is not formatted correctly. Skipped.")
        else:
            print(f"Non-PNG file found - {image}. Skipped.")

    # Speech frames
    # Should be formatted {key}.png
    for key in VISEME_KEYS:
        try:
            frame_data[key] = generate_frame_data(Image.open(f"visemes/{key}.png"))
        except:
            print(f"{key}.png not found, please ensure your viseme files are named correctly.")
            exit()
    print("Frame data created.")

    # Deduplication
    pointers = ""
    for ref_key, ref_value in frame_data.items():
        for key, value in frame_data.items():
            if value == ref_value and value and key != ref_key:
                frame_data[key] = None
                pointers += f'\nFRAME_DATA["{key}"] = FRAME_DATA["{ref_key}"]'

    dedup_frame_data = {k: v for k, v in frame_data.items() if v is not None}
    print("Deduplicated.")
    try:
        with open("frame_data.txt", "x") as f:
            
            data = ("FRAME_DATA = " + 
                # regex to put each dictionary item to a new, tabbed line
                sub(r"(([\"\'])[A-Za-z]+\_[A-Z0-9]+\2\:)", r"\n\t\1", repr(dedup_frame_data))[:-1]
                # Use double-quotes for consistency
                .replace("'", "\"") +
                # move final closing curly bracket to new line
                "\n}" +
                # Add pointers
                "\n# Deduplicate to save memory" + 
                pointers
            )
            if len(data) <= OUTPUT_FILE_MAX_KB * 1000:
                f.write(data)
            else:
                print("Output file too large. Please consolidate some of your animation frames!")
        print("Frame data code written to frame_data.txt. \nPaste it into the appropriate location in main.py.")
    except FileExistsError:
        print("frame_data.txt already exists. Please delete it first!")

def main():
    preprocess_frame_data()

if __name__ == "__main__":
    main()