from numpy import squeeze, dot

def primalToDual(MinMax, c, A, Eqin, b, naturalConstraints=[]):
    """
    Description
        Uses information of the primal LP to convert it to its dual.
    Input
        MinMax               problem type
        c                    objective function's coefficients numpy.array
        A                    constraints' coefficients numpy.array
        Eqin                 constraints' types numpy.array
        b                    constraints' constants numpy.array
        naturalConstraints   (optional) natural constraints' types numpy.array
    Output
        dualType                 dual problem type
        dual_c                   dual objective function's coefficients numpy.array
        w                        dual constraints' coefficients numpy.array
        dualEqin                 dual constraints' types numpy.array
        dual_b                   dual constraints' constants numpy.array
        dualNaturalConstraints   dual natural constraints' types numpy.array
    """

    # Natural constraints legend:
    #   0   means   Free
    #   1   means   x ≥ 0
    #  -1   means   x ≤ 0

    # Convert Min to Max and vice-versa.
    dualType = MinMax * -1

    # Proper transposing of one-dimensionals, numpy is weird, keep reading...
    dual_c = squeeze(b.reshape(1, len(b)))
    dual_b = c.reshape(len(c), 1)

    w = A.transpose()

    if dualType == 1:  # Min ↔ Max
        dualEqin = dot(-1, naturalConstraints) # dot product to convert all values
        dualNaturalConstraints = Eqin # they stay the same, just switching
    elif dualType == -1:  # Max ↔ Min
        dualEqin = naturalConstraints # they stay the same, just switching
        dualNaturalConstraints = dot(-1, Eqin)  # dot product to convert all values

    return dualType, dual_c, w, dualEqin, dual_b, dualNaturalConstraints