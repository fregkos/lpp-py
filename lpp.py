import re
import sys
import getopt
import json
from numpy import array, squeeze, dot

"""
    Author
        Periklis Fregkos (https://github.com/Leajian)
    Program name
        Linear Problem Parser (lpp)
    Version
        2.1
"""


"""
--------------------------------------------------termRegex--------------------------------------------------
Explanation
    sign            consists of one or none symbol, if none we assume it's '+', thus the '?' qualifier.
    coefficient     is any number of zero or more length, if length is zero we assume it's the 1 coefficient,
                    thus the '*' qualifier.
    variable_name   consists of letter 'x' and a number identifier that MUST exist, thus the '+' qualifier.
Note that
    we don't care about whitespaces, we remove it all, thus we can assume these are the expected positions.
    But, we allow multiple occurances of a variable name with no sign, in case the user trys to parse
    a non-linear problem or simply omits the '+' at the beginning.
    For example, x1x2 + x3 = 0. We check it later on, on demand.
-------------------------------------------------------------------------------------------------------------
"""
termRe = re.compile('(?P<sign>[+-]?\s*)(?P<coefficient>\d*\s*)(?P<variable_name>[xX]{1}\d+\s*)')


def openLP(fileName):
    """
    Decription
        Opens the file which contains the linear problem description and splits
        it into segments so it can be parsed easier.
    Input
        string fileName    The file's relative name.
    Output
        A list of containing segments of the problem, splitted on keywords.
    """
    with open(fileName, 'r') as file:
        # Just note that read() function seeks until EOF,
        # so if it's called again, it has nothing.
        problem = file.read()

        # Simple sanity checks to avoid future problems and
        # also check if natural constraints are given.
        hasNaturalConstrains = sanityCheck(problem)

        # Cut the file into segments, from one keyword to another
        # (#1 max/min, #2 st, #optional with, #3 end).
        pattern = re.compile('s\.t\.|st|subject\s*to|with|end', re.IGNORECASE)
        segmentedList = pattern.split(problem)

        # Unless 'with' natural constraints are given indeed,
        # we must return 3 parts.
        if hasNaturalConstrains:
            return segmentedList[:3], hasNaturalConstrains

        # Otherwise, we return only the first 2 parts,
        # but from 2 and beyond include the part with "end" delimiter,
        # which might contain nothing, a new line character or more than that
        # We don't care about content past the "end" delimiter.
        # Any other whitespace character is managed when necessary.
        # If there is any gibberish, the corresponding extractor function
        # is responsible to figure it out.
        return segmentedList[:2]


def sanityCheck(problem):
    """
    Decription
        Checks for the existence of keywords and their correct corresponding positions.
        It also returns a boolean which states if "with" expression was used.
    Input
        problem opened with openLP
    Output
        A boolean which represents whether there are natural constraints or not.
    """
    hasNaturalConstrains = False
    keywordPattern = re.compile('max|min|s\.t\.|st|subject\s*to|with|end', re.IGNORECASE)
    keywords = re.findall(keywordPattern, problem)

    if re.match('max|min', keywords[0], re.IGNORECASE):
        if re.match('s\.t\.|st|subject\s*to', keywords[1], re.IGNORECASE):
            if len(keywords) == 3:
                print('WARNING! Expression "with" not found. Assuming all constraints are non-negative.')
                if not re.match('end', keywords[2], re.IGNORECASE):
                    raise Exception('Expression "end" not found, include it after you end the problem\'s description.')
            elif len(keywords) == 4:
                if re.match('with', keywords[2], re.IGNORECASE):
                    hasNaturalConstrains = True
                    if not re.match('end', keywords[3], re.IGNORECASE):
                        raise Exception('Expression "end" not found, include it after you end the problem\'s description.')
        else:
            raise Exception('Expression "s.t." or "st" or "subject to" not found, include it after you state the objective function.')
    else:
        raise Exception('Expression "min" or "max" not found, include it at the beginning of the problem\'s description.')

    return hasNaturalConstrains


def getMinMax(problem):
    """
    Decription
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


def cVectorExctactor(problem, vars):
    """
    Decription
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


def constrainsExtractor(problem, vars):
    """
    Decription
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
    # because it was '\n' before and split removed it.

    # We loop through the list without the last null string as mentioned above.
    for expression in expressions[:-1]:
        # Count the constraints.
        constraintNo += 1

        # Find all inequalities and append them to our list.
        constraint = re.findall('<=|=|>=', expression)
        EqinTemp.append(constraint)

        # If it was (or tried being) a constraint,
        # then check if it really was a valid one.
        if len(constraint) != 1:
            raise Exception('There was a problem parsing constraint No {}. Make sure you have one constraint per line. Is "{}" a constraint?' .format(constraintNo, expression))

        # Split each expression into two parts, using inequalities as delimiters.
        Ab = re.split('<=|=|>=', expression)

        # Extract the coefficients from the first part (0).
        leftPartCoefficients = coefficientsExtractor(Ab[0], vars)
        A.append(leftPartCoefficients)

        # Extract the constants from the second part (1).
        b.append(float(Ab[1]))

        # Check for each constraint if it's correctly defined.
        if len(leftPartCoefficients) < 1:
            # We explicitly want one constraint per line,
            # so if more than one is found or none, raise an exception.
            raise Exception('Constraint No {} has no left part and it\'s invalid.' .format(constraintNo))
        if len(Ab[1]) < 1:
            raise Exception('Constraint No {} has no right part and it\'s invalid.' .format(constraintNo))

    # Create a new list of Eqin containing inequalities in the format we want.
    for eq in EqinTemp:
        if eq[0] == '<=':
            Eqin.append(-1)
        elif eq[0] == '=':
            Eqin.append(0)
        elif eq[0] == '>=':
            Eqin.append(1)

    return array(A), array(Eqin).reshape(len(Eqin), 1), array(b).reshape(len(b), 1)


def coefficientsExtractor(expression, vars):
    """
    Decription
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


def naturalConstraintsExtractor(problem, vars, hasNaturalConstrains=False):
    """
    Decription
        Returns a list of coefficients as floats from an expression.
        It automatically takes care of omitted signs or singular coefficients.
        For example x-2x, will output [ 1. -2.].
    Input
        problem                 opened with openLP
        vars                    which is an ordered list of variable names
        hasNaturalConstrains    a boolean which represents if there are natural
                                constraints or not.
    Output
        An ordered list of parsed constraint types.
    """
    # If a natural constraint for a variable is not given, we assume it's x ≥ 0.
    naturalConstraints = dict(zip(vars, [1 for i in vars]))

    # If no natural constraints are specified,
    # then return prematurely with the assumption.
    if not hasNaturalConstrains:
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
        if constraint[0][0] in vars:
            if constraint[0][1] == '<=':
                nature = -1
            elif constraint[0][1] == '>=':
                nature = 1
            elif constraint[0][1].lower() == 'free':
                nature = 0
            # Place the natures of the corresponding variable to our dictionary.
            naturalConstraints[constraint[0][0]] = nature

        # If it was (or tried being) a natural constraint,
        # then check if it really was a valid one.
        if len(constraint) != 1:
            raise Exception('There was a problem parsing natural constraint No {}. Make sure you have one natural constraint per line. Is "{}" a natural constraint?' .format(constraintNo, expression))

    # Return an list of values, which came in order because of vars list.
    return [i for i in naturalConstraints.values()]


def writeLP2(MinMax, c, A, Eqin, b, naturalConstraints, inputFile, outputName=''):
    """
    Decription
        Writes the linear problem to a file in a presentable form.
    Input
        MinMax               problem type
        c                    objective function's coefficients numpy.array
        A                    constraints' coefficients numpy.array
        Eqin                 constraints' types numpy.array
        b                    constraints' constants numpy.array
        naturalConstraints   (optional) natural constraints' types numpy.array
        inputFile            input file name
        outputName           (optional) output file name
    Output
        A file which describes the problem in a presentable form.
    """
    if outputName == '':
        outputName = '(LP-2)' + inputFile
    with open(outputName, 'w+') as output:
        """
        if MinMax == 1:
            output.write('max\n')
        elif MinMax == -1:
            output.write('min\n')
        """
        output.write('MinMax = ' + str(MinMax) + '\n\n')
        output.write('c =\n' + str(array(c)) + '\n\n')  # 1 x n
        output.write('A =\n' + str(array(A)) + '\n\n')  # m x n
        output.write('Eqin =\n' + str(array(Eqin).reshape(len(Eqin), 1)) + '\n\n')  # m x 1
        output.write('b =\n' + str(array(b).reshape(len(b), 1)) + '\n\n')  # m x 1
        if naturalConstraints:
            output.write('naturalConstraints =\n' + str(naturalConstraints) + '\n\n')  # 1 x n


def writeLP2json(MinMax, c, A, Eqin, b, naturalConstraints, inputFile, outputName=''):
    """
    Decription
        Writes the linear problem to a file in a serializable form.
    Input
        MinMax               problem type
        c                    objective function's coefficients numpy.array
        A                    constraints' coefficients numpy.array
        Eqin                 constraints' types numpy.array
        b                    constraints' constants numpy.array
        naturalConstraints   (optional) natural constraints' types numpy.array
        inputFile            input file name
        outputName           (optional) output file name
    Output
        A file which describes the problem in a serializable form.
    """
    if outputName == '':
        outputName = '(LP-2)' + inputFile + '.json'
        problem = {
            'MinMax': MinMax,
            'c': {
                'array': c.tolist(),
                'dimensions': c.shape
                },
            'A': {
                'array': A.tolist(),
                'dimensions': A.shape
                },
            'Eqin': {
                'array': Eqin.tolist(),
                'dimensions': Eqin.shape
                },
            'b': {
                'array': b.tolist(),
                'dimensions': b.shape
                }
            }
        if naturalConstraints:
            problem['naturalConstraints'] = naturalConstraints

    with open(outputName, 'w+') as output:
        json.dump(problem, output, indent=4)


def loadLP2json(inputFile):
    """
    Decription
        Returns a list of all information required for the for the linear problem.
    Input
        An LP-2 file name, which contains a problem parsed and saved by this parser in JSON format.
    Output
        In a list
            As floats
                int     MinMax              containing constraints' coefficients
                list    c                   containing linear problem's coefficients array and its dimensions
                list    A                   containing constraints' coefficients array and its dimensions
                list    Eqin                containing constraints' inequalities array and its dimensions
                list    b                   containing constraints' constant parts array and its dimensions
                list    naturalConstraints  containing natural constraints
    """
    with open(inputFile, 'r') as input:
        problem = json.load(input)
    #return problem['MinMax'], problem['c'], problem['A'], problem['Eqin'], problem['b'], naturalConstraints
    return problem


def discoverVariables(list, varSet):
    """
    Decription
        Discovers and adds variable names to a set from a given list.
    Input
        A list with expressions and a set for variable names.
    Output
        Nothing, it just edits the given set.
    """
    for expression in list:
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
    Decription
        Discovers all diffirent variables from a given linear problem.
    Input
        a problem opened with openLP
    Output
        A sorted list with variable names.
    """

    # The first part (0) contains the c vectorand the problem type.
    c = problem[0]
    # problem[1] contains only the part of constraint(s), from s.t. keywords to (with keyword if it exists) end keyword.
    A = problem[1].split('\n')

    # A set of all discovered variables.
    varSet = set()

    discoverVariables(c, varSet)
    discoverVariables(A, varSet)

    return sorted(varSet)  # Returns an ordered list.


def primalToDual(MinMax, c, A, Eqin, b, naturalConstraints=[]):
    """
    Decription
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

    # If natural constraints are not given, we assume the are all x ≥ 0.
    if not naturalConstraints:
        naturalConstraints = [1 for i in Eqin]

    # Convert Min to Max and vice-versa.
    dualType = MinMax * -1

    # Proper transposing, numpy is weird, keep reading...
    dual_c = squeeze(b.reshape(1, len(b)))
    dual_b = c.reshape(len(c), 1)

    w = A.transpose()

    if dualType == 1:  # Min ↔ Max
        dualEqin = Eqin
        dualNaturalConstraints = [x * -1 for x in naturalConstraints]  # convert
    elif dualType == -1:  # Max ↔ Min
        dualEqin = dot(-1, Eqin)  # dot product to convert all values
        dualNaturalConstraints = naturalConstraints

    return dualType, dual_c, w, dualEqin, dual_b, dualNaturalConstraints


def main(argv):

    # Initialize varibales.
    inputFile = ''
    outputFile = ''
    exportAsJSON = False
    dual = False

    ## BUG: Can't use -o and -j together.
    try:
        opts, args = getopt.getopt(argv[1:], 'hji:o:d', ['input=', 'output='])
    except getopt.GetoptError:
        print('Usage: ' + argv[0] + ' -i <inputFile> [options]')
        print('For more options, type: ' + argv[0] + ' -h')
        sys.exit(1)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('Usage: ' + argv[0] + ' -i <inputFile> [options]')
            print('''
Options:
    -j, --json                : export problem in JSON format
    -o, --output <outputFile> : define output file name
                                (Default: '(LP-2)<inputFile>')
    -d, --dual                : convert the problem from primal to dual form
''')
            sys.exit()
        elif opt in ('-i', '--input'):
            inputFile = arg
        elif opt in ('-o', '--output'):
            outputFile = arg
        elif opt in ('-j', '--json'):
            outputFile = arg
            exportAsJSON = True
        elif opt in ('-d', '--dual'):
            dual = True
        else:
            print('Usage: ' + argv[0] + ' -i <inputFile> [options]')
            sys.exit(2)

    # Open the linear problem file.
    problem, hasNaturalConstrains = openLP(inputFile)
    # Discover the variable names.
    vars = discoverProblemVariables(problem)

    # Call order may matter, as all functions access the initial problem list.

    # Get problem type.
    MinMax = getMinMax(problem)
    # Extract objective function's coefficients.
    c = cVectorExctactor(problem, vars)
    # Extract constraints' coefficients, constraint types and their constants.
    A, Eqin, b = constrainsExtractor(problem, vars)
    # naturalConstraints will be an numpy.array containing 1 for all variables
    # if hasNaturalConstrains is False. Thus, it's always initialized.
    naturalConstraints = naturalConstraintsExtractor(problem, vars, hasNaturalConstrains)

    # If dual mode it selected, alter those variables to their dual form.
    if dual:
        MinMax, c, A, Eqin, b, naturalConstraints = primalToDual(MinMax, c, A, Eqin, b)

    """
    # For debugging reasons.
    print(MinMax)
    print(c)
    print(A)
    print(Eqin)
    print(b)
    print(naturalConstraints)
    """

    # Export in the desired format.
    if exportAsJSON:
        writeLP2json(MinMax, c, A, Eqin, b, naturalConstraints, inputFile, outputFile)
    else:
        print('WARNING! This output is not meant for parsing, it\'s unreliable.')
        print('It\'s only for demonstration purposes!\nUse --json for JSON format instead.')

        writeLP2(MinMax, c, A, Eqin, b, naturalConstraints, inputFile, outputFile)


if __name__ == '__main__':
    main(sys.argv)
