import numpy as np
import matplotlib.pyplot as plt

# https://chatgpt.com/share/689688e1-f3b4-8009-bc94-ffdcdca8e71f

"""
Exponential saturation model for ground cover change with mulch application.

Calibrated Hill-type (saturating) model with L=100%
Derived from constraints: for G0=30, G(1)=60 and G(2)=80

                Validation data
------------------+--------+--------+-------
Initial Cover (%) |  m=0.5 |  m=1.0 |  m=2.0
------------------+--------+--------+-------
                0 |   18.4 |   42.9 |   71.4
               10 |   26.5 |   48.6 |   74.3
               30 |   42.9 |  *60.0 |  *80.0
               60 |   67.3 |   77.1 |   88.6
               85 |   87.8 |   91.4 |   95.7
------------------+--------+--------+-------
* = calibration points
"""

__all__ = [
    'ground_cover_change',
]

L = 100.0
a = 0.8473653284334487
b = 1.7369655941662063

def ground_cover_change(initial_ground_cover_pct: float, mulch_tonperacre: float,
                        L: float = L, a: float = a, b: float = b) -> float:
    """
    Saturating response model:
        G(m) = L - (L - G0) / (1 + (a*m)^b)
    Ensures:
      - G(0) = G0
      - G(m) -> L as m -> infinity
      - For the calibration G0=30, matches G(1)=60 and G(2)=80 with L=100.
    """
    G0 = float(initial_ground_cover_pct)
    m = float(mulch_tonperacre)
    v = L - (L - G0) / (1.0 + (a * m) ** b)

    assert 0 <= v <= L, f"Ground cover {v} out of bounds [0, {L}]"
    return v

if __name__ == "__main__":
    # Plot for specified initial covers
    initial_covers = [0, 10, 30, 60, 85]
    m_vals = np.linspace(0, 2, 401)

    plt.figure(figsize=(7, 5))
    for G0 in initial_covers:
        preds = [ground_cover_change(G0, m) for m in m_vals]
        plt.plot(m_vals, preds, label=f"G0={G0}%")

    plt.xlabel("Mulch application (tons/acre)")
    plt.ylabel("Ground cover (%)")
    plt.title("Predicted ground cover vs. mulch application (L=100)")
    plt.ylim(0, 100)
    plt.xlim(0, 2)
    plt.legend()
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.show()

    # ASCII table for m = 0.5, 1.0, 2.0
    test_m = [0.5, 1.0, 2.0]

    # Build table rows
    rows = []
    header = ["Initial Cover (%)"] + [f"m={m:.1f}" for m in test_m]
    rows.append(header)
    for G0 in initial_covers:
        row = [f"{G0:>3}"]
        for m in test_m:
            val = ground_cover_change(G0, m)
            row.append(f"{val:6.1f}")
        rows.append(row)

    # Print ASCII table
    col_widths = [max(len(str(cell)) for cell in col) for col in zip(*rows)]
    def format_row(r):
        return " | ".join(str(cell).rjust(w) for cell, w in zip(r, col_widths))

    print(format_row(rows[0]))
    print("-+-".join("-" * w for w in col_widths))
    for r in rows[1:]:
        print(format_row(r))
