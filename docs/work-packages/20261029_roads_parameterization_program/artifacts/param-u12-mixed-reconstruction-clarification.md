# Clarification: the load difference bounded in the U12 terminal-band review

This addendum defines the state behind the derivative-forcing equation used in
the accepted U12 review. It changes no source, data, computed bound, acceptance
threshold, or executable. The phrase “raw-versus-clipped load discrepancy” must
not be read as the difference between two separately consistent load ODEs.

Let `G` be the deposition term evolved by DEPEQS from the raw polynomial, with
`v=x+q` and `Craw` including the existing normalization factor. On supported wet
coordinates its equation is:

```text
G' = -(phi+1) G/v + phi (Craw' - theta)/v.
```

DEPOS reconstructs a load using clipped capacity:

```text
Lm = Cclip - v G/phi,       Cclip = max(0, Craw).
```

Differentiating this actual mixed reconstruction gives:

```text
Lm' = G + theta + Cclip' - Craw'
    = phi (Cclip-Lm)/v + theta + Cclip' - Craw'.
```

Let `Lc` instead solve the consistent clipped-capacity load equation
`Lc' = phi(Cclip-Lc)/v + theta`, starting with the same load before the negative
band. The bounded **load** difference is `E=Lm-Lc`; therefore:

```text
E' + phi E/v = Cclip' - Craw'.
```

This is not a capacity-deficit variable. It is also not the difference between
consistent raw-capacity and clipped-capacity load solutions: that different
comparison would have a forcing proportional to `Craw-Cclip`, with sign set by
the subtraction order. The terminal audit bounds the mixed reconstruction
actually used by the native routines. Its damping proof, exact weighted
calculation, and independent quadrature remain unchanged.

The relevant source is `src/depeqs.for` and `src/depos.for` at accepted source
identity `b01a739957bef5aacf35b4a89bc13eddc9d94804`. The retained
[terminal audit](audit_param_terminal_matrix_u12.py) and
[final scientific acceptance](param-u12-scientific-acceptance.json) retain their
original hashes; this clarification does not replace them.
