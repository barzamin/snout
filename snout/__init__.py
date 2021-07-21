import struct
from dataclasses import dataclass

def rdr_unpack(fmt, rdr):
    size = struct.calcsize(fmt)
    buf = rdr.read(size)
    if len(buf) == 0 and size != 0:
        raise EOFError
    return struct.unpack(fmt, buf)

@dataclass
class SCDMeasurement:
    co2: float
    temp: float
    rh: float

    @classmethod
    def parse(cls, rdr):
        co2, temp, rh = rdr_unpack('<fff', rdr)
        return cls(co2=co2, temp=temp, rh=rh)

@dataclass
class SHTMeasurement:
    temp: float
    rh: float

    @classmethod
    def parse(cls, rdr):
        temp, rh = rdr_unpack('<ff', rdr)
        return cls(temp=temp, rh=rh)

@dataclass
class PM25Measurement:
    pm_std: dict[int, int]
    pm_env: dict[int, int]
    particle_count: dict[int, int]

    @classmethod
    def parse(cls, rdr):
        (
            pm10s, pm25s, pm100s,
            pm10e, pm25e, pm100e,
            pa03, pa05, pa10, pa25, pa50, pa100
        ) = rdr_unpack('HHHHHHHHHHHH', rdr)
        return cls(
            pm_std={10: pm10s, 25: pm25s, 100: pm100s},
            pm_env={10: pm10e, 25: pm25e, 100: pm100e},
            particle_count={3: pa03, 5: pa05, 10: pa10, 25: pa25, 50: pa50, 100: pa100},
        )

@dataclass
class Timestamp:
    secs: int

    @classmethod
    def parse(cls, rdr):
        secs, = rdr_unpack('<Lx', rdr)
        return cls(secs=secs)

def parse_packet(rdr):
    header, = rdr_unpack('B', rdr)
    if header == 0x74: # time
        return Timestamp.parse(rdr)
    elif header == 0x30: # SCD30
        return SCDMeasurement.parse(rdr)
    elif header == 0x40: # SHT40
        return SHTMeasurement.parse(rdr)
    elif header == 0x25:
        return PM25Measurement.parse(rdr)
    else:
        raise ValueError(f"{header:#x} isn't a known packet type")