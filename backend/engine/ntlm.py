"""Empreintes des mots de passe fictifs : MD4 (RFC 1320), NTOWFv1 (MS-NLMP).

Implémentation locale destinée au modèle de fichiers du jeu, sans dépendance ni
appel à un exécutable. Le chiffrement des tickets Kerberos reste simulé.
"""
import struct


def md4(data: bytes) -> bytes:
    length = len(data)
    data += b'\x80' + b'\0' * ((55 - length) % 64) + struct.pack('<Q', length * 8)
    state = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476]
    rounds = [(list(range(16)), (3,7,11,19), 0),
              ([0,4,8,12,1,5,9,13,2,6,10,14,3,7,11,15], (3,5,9,13), 0x5a827999),
              ([0,8,4,12,2,10,6,14,1,9,5,13,3,11,7,15], (3,9,11,15), 0x6ed9eba1)]
    for start in range(0,len(data),64):
        words = struct.unpack('<16I',data[start:start+64])
        registers = state.copy()
        for number,(order,shifts,constant) in enumerate(rounds):
            for i,k in enumerate(order):
                index = (-i) % 4
                b,c,d = (registers[(index+j)%4] for j in (1,2,3))
                mixed = ((b & c) | (~b & d)) if number == 0 else (((b & c) | (b & d) | (c & d)) if number == 1 else b ^ c ^ d)
                value = (registers[index] + mixed + words[k] + constant) & 0xffffffff
                shift = shifts[i%4]
                registers[index] = ((value << shift) | (value >> (32-shift))) & 0xffffffff
        state = [(a+b) & 0xffffffff for a,b in zip(state,registers)]
    return struct.pack('<4I',*state)


def nt_hash(password: str) -> str:
    return md4(password.encode('utf-16-le')).hex()
