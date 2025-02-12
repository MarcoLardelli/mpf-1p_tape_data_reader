import wave
import pylab

DEBUG = False  # set to true to show lots of debug info

# signal levels for 0 or 1
THRESHOLD_1 = 40000  # min
THRESHOLD_0 = 20000  # max

EMPTY_SIGNAL_LENGTH = 500
SYNC_SIGNAL_LENGTH = 20

offset = 629776-10000 # start of signal
#offset = 0 # start of signal (optional. use if very long empty space on beginning)
amount = 1000000000 # set to very large value for ALL files

filename = '02 Side B - Mor2 Auto.wav'
#filename = '01 Side A - Simu Code Simu Reak Orge Mors Reak Clok Stop Simu Mors.wav'


# ------------ end of config ------------

# some important ASCII codes
NEW_LINE = 13
SPACE = 32

f = wave.open('audio/'+filename)


print('Channels:',f.getnchannels())
print('SampWidth:',f.getsampwidth())
print('#Frames:',f.getnframes())
framerate = f.getframerate()
print('Framerate:',framerate)
print('--------')

WAVELENGTH_1K = framerate / 1000
WAVELENGTH_1K_MIN = WAVELENGTH_1K - 4
WAVELENGTH_1K_MAX = WAVELENGTH_1K + 4

# next four lines from http://dabeaz.blogspot.com/2010/08/using-python-to-encode-cassette.html
rawdata = bytearray(f.readframes(f.getnframes()))
del rawdata[2::4]    # Delete the right stereo channel    
del rawdata[2::3]
wavedata = [a + (b << 8) for a,b in zip(rawdata[::2],rawdata[1::2])]


position = offset

def step(label):
    global position
    position += 1
    if DEBUG:
        print(label,position)


def wait_for_data(file_no):
    global position

    # ignore no signal data
    while position<len(wavedata) and (position < (offset+amount)):
        if wavedata[position] > THRESHOLD_1:
            break
        step('no signal')
       
    if DEBUG:
        print('#'+str(file_no)+': Starting at position:',position)
    
    # ignore lead sync
    bitcount = 0
    wave_length = WAVELENGTH_1K  # typical 1kHz
    while position<len(wavedata) and (position < (offset+amount)) and (wave_length>WAVELENGTH_1K_MIN and wave_length < WAVELENGTH_1K_MAX):
        length_1 = 0
        while position<len(wavedata) and (position < (offset+amount)):
            value = wavedata[position]
            if value < THRESHOLD_0:
                break
            step('ignore lead - wait for low')
            length_1 += 1

        length_0 = 0
        while position<len(wavedata) and (position < (offset+amount)) :
            value = wavedata[position]
            if value > THRESHOLD_1:
                break
            step('ignore lead - wait for high')
            length_0 += 1

        wave_length = length_1 + length_0 
        #print(length_1,length_0, wave_length)

        bitcount += 1

    sync_position = position
    if DEBUG:
        print('#'+str(file_no)+': Sync wave count:',bitcount)
        print('#'+str(file_no)+': Sync end position:',sync_position)


def read_data(file_no):
    global position

    # read data
    if DEBUG:
        print('#'+str(file_no)+': Reading data...')

    bitstream=[]
    cyclecount = 0

    kHz_1_count = 0
    last_wave_type = 2 # 2 khz
    while position<len(wavedata) and (position < (offset+amount)):
        length_1 = 0
        # wait for low signal
        while position<len(wavedata) and (position < (offset + amount)):
            value = wavedata[position]
            if value < THRESHOLD_0:
                break
            step('read data - wait for low')
            length_1 += 1

        length_0 = 0
        # wait for a high signal
        while position<len(wavedata) and (position < (offset + amount)):
            value = wavedata[position]
            if value > THRESHOLD_1:
                break
            step('ignore lead - wait for high')
            length_0 += 1
            if length_0 > EMPTY_SIGNAL_LENGTH:  #empty signal encountered
                return bitstream

        wave_length = length_1 + length_0 # total wave length
        # detect frequency
        if wave_length>35:
            wave_type = 1  # 1 kHz
            kHz_1_count += 1
        else:
            wave_type = 2 # 2 kHz

        if kHz_1_count>SYNC_SIGNAL_LENGTH: # sync signal encountered
            return bitstream # return what you have
        
        if wave_type==2 and last_wave_type==1:
            if kHz_1_count>3:
                bitstream.append(1)
            else:
                bitstream.append(0)
            kHz_1_count = 0
            
        last_wave_type = wave_type

        if DEBUG and cyclecount<300:
            print(length_1,length_0,wave_length,wave_type)

        cyclecount += 1

    return bitstream



# convert bitstream to bytes
def convert_bits(bitstream):
    bit_offset = 0
    start = bit_offset
    line = ''
    lines = []
    while len(bitstream)>(start+10):
        byte = bitstream[start:start+10]
        if byte[0]!=0 or byte[9]!=1:  # start or stop bit wrong
            if DEBUG:
                print('error at',start, byte)
            return '\n'.join(lines) # just return what you have so far
        byte = byte[1:-1]  # remove start and stop bits
        value = 0
        for j in range(7):  # 7 bit ascii code
            value += byte[j] * pow(2,j)
        #print(value,chr(value))
        if value!=NEW_LINE:
            if value==SPACE and len(line)>0 and line[0]!=' ':  # a label
                lines.append(line+":")
                line = ''
            line += chr(value)
        else: # newline
            lines.append(line)
            line = ''
        start += 10

    return '\n'.join(lines)

# main loop
file_no = 0
while position<len(wavedata):
    wait_for_data(file_no)
    bitstream = read_data(file_no)
    if len(bitstream)>0:
        if DEBUG:
            print(bitstream)
        bytes = convert_bits(bitstream)
        filename = bytes[0:4]
        asm_text = bytes[28:]
        print('-------',file_no+1,'('+filename+') pos:',position,'-------')
        with open('asm/program_'+str(file_no+1)+'_'+filename+'.asm', 'w') as f:
            f.write(asm_text)
        file_no +=1
    else:
        print('-------',file_no+1,'pos:',position,' (empty) -------')

print()
print('Done!')

#pylab.plot(wavedata[sync_position:sync_position+amount])
#pylab.plot(wavedata[position-1000:position+2000])
#pylab.show()