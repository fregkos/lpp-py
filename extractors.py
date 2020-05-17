import re
from numpy import array, sum


"""
--------------------------------------------------termRegex--------------------------------------------------
Explanation
    sign            consists of one or none symbol, if none we assume it's '+', thus the '?' qualifier.
    coefficient     is any number of zero or more length, if length is zero we assume it's the 1 coefficient,
                    thus the '*' qualifier.
    variable_name   consists of letter 'x' and a number identifier that MUST exist, thus the '+' qualifier.
Note that
    we don't care about whitespaces, we remove it all, thus we can assume these are the expected positions.
    But, we allow multiple occurances of a variable name with no sign, in case the user tries to parse
    a non-linear problem or simply omits the '+' at the beginning.
    For example, x1x2 + x3 = 0. We check it later on, on demand.
-------------------------------------------------------------------------------------------------------------
"""

termRe = re.compile('(?P<sign>[+-]?\s*)(?P<coefficient>\d*\s*)(?P<variable_name>[xX]{1}\d+\s*)')


def coefficientsExtractor(expression, vars):
    """
    Description
        Returns a list of coefficients as floats from an expression.
        It automatically takes care of omitted signs or singular coefficients.
        For example x-2x, will output [ 1. -2.].
    Input
        expression of a problem opened with openLP
    Output
        A list of parsed coefficients as floats.
    """
    # Remove any kind of whitespace [ \t\n\r\f\v] from the expression.
    clean = re.sub('\s+', '', expression)

    # Make a list of each term (see termRegex for explanation).
    terms = termRe.findall(clean)

    # Initialize final dicitonary. If a variable exists, it's not zero.
    signedCoefficients = dict(zip(vars, [0 for i in vars]))

    for term in terms:
        # The only reason for sign to be omitted is
        # (the first term) at the beginning, otherwise it is a term
        # multiplied by another, in other words, it's not linear.
        if term != terms[0] and term[0] == '':
            raise Exception('Expression {} is non-linear. Fix term {}.' .format(''.join(clean), ''.join(term)))

        # Create a list of strings containing [sign, value],
        # so that we can append it as a casted float.
        aTerm = [term[0], term[1]]

        # Special case where 1 coefficient is omiitted.
        if term[1] == '':
            aTerm[1] = '1'

        # Casting takes care for omitted sign of the number.
        signedCoefficients[term[2]] = (float(aTerm[0] + aTerm[1]))

    # Return a list of the values of the dictionary.
    # For example {'x1': 1.4, 'x2': 0, 'x3': -4.0},
    # returns [ 1.4, 0, -4.0 ].
    return list(signedCoefficients.values())

def constraintsExtractor(problem, vars):
    """
    Description
        Returns 3 lists as floats describing the problem's constraints details.
    Input
        problem opened with openLP
    Output
        As floats
            numpy.array A containing constraints' coefficients
            numpy.array Eqin containing constraints' inequalities
            numpy.array b containing constraints' constant parts
    """
    A = []
    b = []

    EqinTemp = []
    Eqin = []

    constraintNo = 0

    # Remove excessive occurances of the newline character, because it's
    # our delimiter for every constraint.
    problem[1] = re.sub('\n+', '\n', problem[1])
    # Also remove the newline at the beginning, if it exists.
    if problem[1][0] == '\n':
        problem[1] = problem[1][1:]

    # problem[1] contains only the part of constraint(s).
    expressions = problem[1].split('\n')

    # Since we split with a new line character as a delimiter,
    # the last element of our expressions list is always a null string,
    # because it was '\n' before and split removed it. The last '\n'
    # comes from the necessery '\nend' keyword.

    # We loop through the list without the last null string as mentioned above.
    for expression in expressions[:-1]:
        # Count the constraints.
        constraintNo += 1

        # Find all inequalities and append them to our list.
        constraint = re.findall('<=|=|>=', expression)
        EqinTemp.append(constraint)

        # If it was (or tried being) a constraint,
        # then check if it really was a valid one.
        # That can occur if user accidentally types extra <=, = ,>= characters,
        # because we break each expression/line using them as delimiters.
        if len(constraint) != 1:
            raise Exception('There was a problem parsing constraint No {}. Make sure you have one constraint per line. Is "{}" a constraint?' .format(constraintNo, expression))

        # Split each expression into two parts, using inequalities as delimiters.
        Ab = re.split('<=|=|>=', expression)

        # Extract the coefficients from the first part (0).
        leftPartCoefficients = coefficientsExtractor(Ab[0], vars)
        
        ## Checks for correct definition of each constraint.

        # We assume left part is invalid
        invalidLeftPart = True
        # We check if that is true for every coefficient.
        for coeff in leftPartCoefficients:
            
            # If at least one coefficient is non-zero, that means there is no problem.
            if coeff != 0:
                invalidLeftPart = False

        # Remember, every expression's left part is initiallized as a zero matrix,
        # thus if none found, every coefficient is zero and invalid.
        # For example if that line has only '<=5'. Then we get A = [0 0 0] for that line
        # assuming we have 3 variables and the b = [5], with Eqin = [-1].
        # We can't simply check the sum of the array, because there are multiple ways
        # for a zero sum, i.e. A = [ 1 0 -1], which is a valid left part.
        if invalidLeftPart:
            raise Exception('Constraint No {} has no left part and it\'s invalid.' .format(constraintNo))

        A.append(leftPartCoefficients)
        
        if Ab[1] == '':
            raise Exception('Constraint No {} has no right part and it\'s invalid.' .format(constraintNo))

        # Extract the constants from the second part (1).
        b.append(float(Ab[1]))

    # Create a new list of Eqin containing inequalities in the format we want.
    for eq in EqinTemp:
        if eq[0] == '<=':
            Eqin.append(-1)
        elif eq[0] == '=':
            Eqin.append(0)
        elif eq[0] == '>=':
            Eqin.append(1)

    return array(A), array(Eqin).reshape(len(Eqin), 1), array(b).reshape(len(b), 1)

def naturalConstraintsExtractor(problem, vars, hasNaturalConstraints=False):
    """
    Description
        Returns a list of coefficients as floats from an expression.
        It automatically takes care of omitted signs or singular coefficients.
        For example x-2x, will output [ 1. -2.].
    Input
        problem                 opened with openLP
        vars                    which is an ordered list of variable names
        hasNaturalConstraints    a boolean which represents if there are natural
                                constraints or not.
    Output
        An ordered list of parsed constraint types.
    """
    # If a natural constraint for a variable is not given, we assume it's x ≥ 0.
    naturalConstraints = dict(zip(vars, [1 for i in vars]))

    # If no natural constraints are specified,
    # then return prematurely with the assumption.
    if not hasNaturalConstraints:
        return [i for i in naturalConstraints.values()]

    # Initialize constraints' counter.
    constraintNo = 0

    # Remove excessive occurances of the newline character,
    # because it's our delimiter for every constraint.
    problem[2] = re.sub('\n+', '\n', problem[2])
    # Also remove the newline at the beginning, if it exists.
    if problem[2][0] == '\n':
        problem[2] = problem[2][1:]

    # problem[2] contains only the part of natural constraint(s).
    expressions = problem[2].split('\n')

    # Since we split with a new line character as a delimiter,
    # the last element of our expressions list is always a null string,
    # because it was '\n' before and split removed it.

    # We loop through the list without the last null string as mentioned above.
    for expression in expressions[:-1]:
        # Count the constraints
        constraintNo += 1

        # Find all natures.
        constraintRe = re.compile('\s*(\w*)\s*(<=|>=|free).*', re.IGNORECASE)
        constraint = re.findall(constraintRe, expression)

        # If the natural constraint is about a known variable, check it.
        # Any unknown is ignored. We are planning ahead as always (hopefully).
        if constraint[0][0].lower() in vars:
            if constraint[0][1] == '<=':
                nature = -1
            elif constraint[0][1] == '>=':
                nature = 1
            elif constraint[0][1].lower() == 'free':
                nature = 0
            # Place the natures of the corresponding variable to our dictionary.
            naturalConstraints[constraint[0][0].lower()] = nature

        # If it was (or tried being) a natural constraint,
        # then check if it really was a valid one.
        if len(constraint) != 1:
            raise Exception('There was a problem parsing natural constraint No {}. Make sure you have one natural constraint per line. Is "{}" a natural constraint?' .format(constraintNo, expression))

    # Return a list of values, which came in order because of vars list.
    return [i for i in naturalConstraints.values()]

def cVectorExctactor(problem, vars):
    """
    Description
        Returns a list of objective function's coefficients as floats.
    Input
        problem opened with openLP
    Output
        A numpy.array of floats containing objective function's coefficients
    """

    # From the problem part (0), which contains the objective function,
    # we use as delimiter the type of problem to split it into 2 parts.
    # This is necessary because there might be noise from gibberish input.
    segmentedList = re.compile('max|min', re.IGNORECASE).split(problem[0])

    # With the above method, we only take the second part (1),
    # which contains information described after the min/max keyword
    # that is our objective function. From now on, it's coefficientsExtractor
    # function's responsibility to determine more input errors,
    # which are more specific and beyond this function's job.
    return array(coefficientsExtractor(segmentedList[1], vars))

def MinMaxExtractor(problem):
    """
    Description
        Returns the type of problem (1 = maximize, -1 = minimize).
    Input
        problem opened with openLP
    Output
        1 if it's a maximization problem
        -1 if it's a minimization problem
    """
    if re.search('max', problem[0], re.IGNORECASE):
        return 1
    elif re.search('min', problem[0], re.IGNORECASE):
        return -1
    else:
        raise Exception('Could not determine problem type.')

"""
Variables discovery
"""

def discoverVariables(aList, varSet):
    """
    Description
        Discovers and adds variable names to a set from a given list.
    Input
        A list with expressions and a set for variable names.
    Output
        Nothing, it just edits the given set.
    """
    for expression in aList:
        # Remove any kind of whitespace [ \t\n\r\f\v] from the expression.
        clean = re.sub('\s+', '', expression)

        # Make a list of each term (see termRegex for explanation).
        terms = termRe.findall(clean)

        for term in terms:
            # The only reason for sign to be omitted is
            # (the first term) at the beginning, otherwise it is a term
            # multiplied by another, in other words, it's not linear.
            if term != terms[0] and term[0] == '':
                raise Exception('Expression {} is non-linear. Fix term {}.' .format(''.join(clean), ''.join(term)))

            # Add any newly discovered variable to the set.
            varSet.add(term[2])

def discoverProblemVariables(problem):
    """
    Description
        Discovers all diffirent variables from a given linear problem.
    Input
        a problem opened with openLP
    Output
        A sorted list with variable names.
    """

    # The first part (0) contains the c vector and the problem type.
    c = problem[0]
    # problem[1] contains only the part of constraint(s), from s.t. keywords to (with keyword if it exists) end keyword.
    A = problem[1].split('\n')

    # A set of all discovered variables.
    varSet = set()

    discoverVariables(c, varSet)
    discoverVariables(A, varSet)

    return sorted(varSet)  # Returns an ordered list.
