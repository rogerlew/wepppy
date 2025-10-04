import enum

class AshType(enum.IntEnum):
    BLACK = 0
    WHITE = 1

    def __str__(self):
        if self == AshType.BLACK:
            return 'Black'
        elif self == AshType.WHITE:
            return 'White'
        else:
            raise ValueError(f'Unknown ash type {self}')

__all__ = [
    'AshType',
]
