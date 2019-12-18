import binascii
from math import ceil
from .func import rotl, bytes_to_list
import struct

__all__ = [
    "sm3_hash",
    "sm3_hmac",
    "SM3"
]

IV = [
    1937774191, 1226093241, 388252375, 3666478592,
    2842636476, 372324522, 3817729613, 2969243214,
]

T_j = [
    2043430169, 2043430169, 2043430169, 2043430169, 2043430169, 2043430169,
    2043430169, 2043430169, 2043430169, 2043430169, 2043430169, 2043430169,
    2043430169, 2043430169, 2043430169, 2043430169, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042
]


def sm3_ff_j(x, y, z, j):
    if 0 <= j and j < 16:
        ret = x ^ y ^ z
    elif 16 <= j and j < 64:
        ret = (x & y) | (x & z) | (y & z)
    return ret


def sm3_gg_j(x, y, z, j):
    if 0 <= j and j < 16:
        ret = x ^ y ^ z
    elif 16 <= j and j < 64:
        # ret = (X | Y) & ((2 ** 32 - 1 - X) | Z)
        ret = (x & y) | ((~ x) & z)
    return ret


def sm3_p_0(x):
    return x ^ (rotl(x, 9 % 32)) ^ (rotl(x, 17 % 32))


def sm3_p_1(x):
    return x ^ (rotl(x, 15 % 32)) ^ (rotl(x, 23 % 32))


def sm3_cf(v_i, b_i):
    w = []
    for i in range(16):
        weight = 0x1000000
        data = 0
        for k in range(i * 4, (i + 1) * 4):
            data = data + b_i[k] * weight
            weight = int(weight / 0x100)
        w.append(data)

    for j in range(16, 68):
        w.append(0)
        w[j] = sm3_p_1(w[j - 16] ^ w[j - 9] ^ (rotl(w[j - 3], 15 % 32))) ^ (rotl(w[j - 13], 7 % 32)) ^ w[j - 6]
        str1 = "%08x" % w[j]
    w_1 = []
    for j in range(0, 64):
        w_1.append(0)
        w_1[j] = w[j] ^ w[j + 4]
        str1 = "%08x" % w_1[j]

    a, b, c, d, e, f, g, h = v_i

    for j in range(0, 64):
        ss_1 = rotl(
            ((rotl(a, 12 % 32)) +
             e +
             (rotl(T_j[j], j % 32))) & 0xffffffff, 7 % 32
        )
        ss_2 = ss_1 ^ (rotl(a, 12 % 32))
        tt_1 = (sm3_ff_j(a, b, c, j) + d + ss_2 + w_1[j]) & 0xffffffff
        tt_2 = (sm3_gg_j(e, f, g, j) + h + ss_1 + w[j]) & 0xffffffff
        d = c
        c = rotl(b, 9 % 32)
        b = a
        a = tt_1
        h = g
        g = rotl(f, 19 % 32)
        f = e
        e = sm3_p_0(tt_2)

        a, b, c, d, e, f, g, h = map(
            lambda x: x & 0xFFFFFFFF, [a, b, c, d, e, f, g, h])

    v_j = [a, b, c, d, e, f, g, h]
    return [v_j[i] ^ v_i[i] for i in range(8)]


def sm3_hash(in_msg):
    if isinstance(in_msg, (bytes, bytearray)):
        in_msg = list(in_msg)
    # print(msg)
    msg = in_msg[0:]
    len1 = len(msg)
    reserve1 = len1 % 64
    msg.append(0x80)
    reserve1 = reserve1 + 1
    # 56-64, add 64 byte
    range_end = 56
    if reserve1 > range_end:
        range_end = range_end + 64

    for i in range(reserve1, range_end):
        msg.append(0x00)

    bit_length = (len1) * 8
    bit_length_str = [bit_length % 0x100]
    for i in range(7):
        bit_length = int(bit_length / 0x100)
        bit_length_str.append(bit_length % 0x100)
    for i in range(8):
        msg.append(bit_length_str[7 - i])

    group_count = round(len(msg) / 64)

    B = []
    for i in range(0, group_count):
        B.append(msg[i * 64:(i + 1) * 64])

    V = []
    V.append(IV)
    for i in range(0, group_count):
        V.append(sm3_cf(V[i], B[i]))

    y = V[i + 1]
    result = ""
    for i in y:
        result = '%s%08x' % (result, i)
    return result

# key : bytes
# in_msg: bytes
def sm3_hmac(key, in_msg):
    ipad = [0x36 for i in range(64)]
    opad = [0x5c for i in range(64)]

    if len(key) > 64:
        key = bytes.fromhex(sm3_hash(key))

    for i in range(len(key)):
        ipad[i] = ipad[i] ^ key[i]
        opad[i] = opad[i] ^ key[i]

    h1 = sm3_hash(list(bytes(ipad) + in_msg))
    return sm3_hash(opad + list(bytes.fromhex(h1)))

class SM3():
    GROUP_BYTES = 64

    def __init__(self):
        self.B = []
        self.V = []
        self.msg = []
        self.msg_len = 0;
        self.V.append(IV)

    def _add_msg(self, msg=[]):
        # 连接
        self._extend_msg(msg)
        # 分组
        self._group_msg()
        # 计算
        self._calc_msg()

    def _extend_msg(self, msg):
        self.msg.extend(msg)
        self.msg_len += len(msg)

    def _group_msg(self):
        while len(self.msg) >= SM3.GROUP_BYTES:
            self.B.append(self.msg[0:SM3.GROUP_BYTES])
            self.msg = self.msg[SM3.GROUP_BYTES:]

    def _calc_msg(self):
        group_len = len(self.B)
        for i in range(0, group_len):
            self.V.append(sm3_cf(self.V[0], self.B[0]))
            self.V.pop(0)
            self.B.pop(0)

    def start(self, msg=[]):
        self.__init__()
        self._add_msg(msg)

    def update(self, msg):
        self._add_msg(msg)

    def finish(self, msg=[]):
        # 连接
        self._extend_msg(msg)
        # 填充
        len_total = self.msg_len
        reserve1 = len_total % 64
        self.msg.append(0x80)
        reserve1 = reserve1 + 1
        # 56-64, add 64 byte
        range_end = 56
        if reserve1 > range_end:
            range_end = range_end + 64

        for i in range(reserve1, range_end):
            self.msg.append(0x00)

        bit_length = (len_total) * 8
        bit_length_str = [bit_length % 0x100]
        for i in range(7):
            bit_length = int(bit_length / 0x100)
            bit_length_str.append(bit_length % 0x100)
        for i in range(8):
            self.msg.append(bit_length_str[7 - i])

        # 分组、计算
        self._group_msg()
        self._calc_msg()
        # 获取结果
        y = self.V[0]
        result = ""
        for i in y:
            result = '%s%08x' % (result, i)
        return result


def sm3_kdf(z, klen):  # z为16进制表示的比特串（str），klen为密钥长度（单位byte）
    klen = int(klen)
    ct = 0x00000001
    rcnt = ceil(klen / 32)
    zin = [i for i in bytes.fromhex(z.decode('utf8'))]
    ha = ""
    for i in range(rcnt):
        msg = zin + [i for i in binascii.a2b_hex(('%08x' % ct).encode('utf8'))]
        ha = ha + sm3_hash(msg)
        ct += 1
    return ha[0: klen * 2]

def sm3_kdf_ex(z, klen):  # z为16进制表示的比特串（str），klen为密钥长度（单位byte）
    klen = int(klen)
    ct = 0x00000001
    rcnt = ceil(klen / 32)
    ha = ""
    for i in range(rcnt):
        msg = z + struct.pack("!I", ct)
        ha = ha + sm3_hash(list(msg))
        ct += 1
    return ha[0: klen * 2]