import re, sys, getopt, json
from numpy import array, shape, reshape

"""
    Author
        Periklis Fregkos (https://github.com/Leajian)
    Program name
        Linear Problem Parser (lpp)
    Creation Date
        22/3/2019
"""


"""
--------------------------------------------------termRegex--------------------------------------------------
Explanation
    sign consists of one or none symbol, if none we assume it's '+', thus the '?' qualifier.
    coefficient is any number of zero or more length, if length is zero we assume it's the 1 coefficient,
                thus the '*' qualifier.
    variable_name consists of letter 'x' and a number identifier that MUST exist, thus the '+' qualifier.
Note that
    we don't care about whitespaces, we remove it all, thus we can assume these are the expected positions.
    But, we allow multiple occurances of a variable name with no sign, in case the user trys to parse
    a non-linear problem or simply omits the '+' at the beginning.
    For example, x1x2 + x3 = 0. We check it later on, on demand.
-------------------------------------------------------------------------------------------------------------
"""
termRe = re.compile('(?P<sign>[+-]?\s*)(?P<coefficient>\d*\s*)(?P<variable_name>[xX]{1}\d+\s*)')

def openLP(fileName):
    with open(fileName, 'r') as file:
        #Just note that read() function seeks until EOF, so if it's called again, it has nothing.
        problem = file.read()

        #Simple sanity checks to avoid future problems
        if not re.search('max|min', problem, re.IGNORECASE):
            raise Exception('Expression "min" or "max" not found, include it in the beginning of problem\'s description.')
        if not re.search('s\.t\.|st|subject\s*to', problem, re.IGNORECASE):
            raise Exception('Expression "s.t." or "st" or "subject to" not found, include it after you state objective function.')
        if not re.search('end', problem, re.IGNORECASE):
            raise Exception('Expression "end" not found, include it after you end problem\'s description.')

        #Cut the file in 2 segments (#1 max/min - st, #2 st - end).
        segmentedList = re.compile('s\.t\.|st|subject\s*to|end', re.IGNORECASE).split(problem)

        #We return only the first 2 parts, the other ones (from 2 and beyond) include the one with "end" delimiter,
        #which might contain nothing, a new line character or more than that. We don't care about content
        #past the "end" delimiter. Any other whitespace character is managed when necessary.
        #The first part has the objective function (and possibly whitespace, but we don't mind).
        #If there is any gibberish, the corresponding extractor function is responsible to figure it out.
        return segmentedList[:2]

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

def cVectorExctactor(problem):
    """
    Decription
        Returns a list of objective function's coefficients as floats.
    Input
        problem opened with openLP
    Output
        A numpy.array of floats
    """

    #From the problem part (0), which contains the objective function, we use as delimiter
    #the type of problem to split it into 2 parts. This is necessary because there might
    #be noise from gibberish input.
    segmentedList = re.compile('max|min', re.IGNORECASE).split(problem[0])

    #With the above method,we only take the second part (1), which contains information
    #described after the min/max keyword that is our objective function. From now on,
    #it's coefficientsExtractor function's responsibility to determine more input errors,
    #which are more specific and beyond this function's job.
    return array(coefficientsExtractor(segmentedList[1]))

def constrainsExtractor(problem):
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

    #problem[1] contains only the part of constraint(s), from s.t. keywords to end keyword.
    #We could only pass that part as arguement, but readability counts.
    expressions = problem[1].split('\n')

    #Since we split with a new line character as a delimiter, the last element of our expressions list is
    #always a null string, because it was '\n' before and split removed it.
    #We are sure that this came clean and in this format, because openLP gave it that way.


    #We loop without the last null string as mentioned above.
    for expression in expressions[:-1]:
        #Count the constraints
        constraintNo += 1

        #Find all inequalities and append them to our list.
        constraint = re.findall('<=|=|>=', expression)
        EqinTemp.append(constraint)

        #We explicitly want one constraint per line, so if more than one is found or none, raise Exception.
        if len(constraint) != 1:
            raise Exception('There was a problem parsing constraint No {}. Make sure you have one constraint per line.'.format(constraintNo))

        #Split each expression into two parts, using inequalities as delimiters.
        Ab = re.split('<=|=|>=', expression)
        #Extract the coefficients from the first part (0).
        leftPartCoefficients = coefficientsExtractor(Ab[0])
        A.append(leftPartCoefficients)
        #Extract the constants from the second part (1).
        b.append(float(Ab[1]))

        #Check for each constraint if it's correctly defined
        if len(leftPartCoefficients) < 1:
            raise Exception('Constraint No {} has no left part and it\'s invalid.'.format(constraintNo))
        if len(Ab[1]) < 1:
            raise Exception('Constraint No {} has no right part and it\'s invalid.'.format(constraintNo))

    #Create a new list of Eqin containing inequalities in the format we want.
    for eq in EqinTemp:
        if eq[0] == '<=':
            Eqin.append(-1)
        elif eq[0] == '=':
            Eqin.append(0)
        elif eq[0] == '>=':
            Eqin.append(1)

    return array(A), array(Eqin).reshape(len(Eqin), 1), array(b).reshape(len(b), 1)

def coefficientsExtractor(expression):
    """
    Decription
        Returns a list of coefficients as floats from an expression. It automatically takes care
        of omitted signs or singular coefficients. For example x-2x, will output [ 1. -2.].
    Input
        expressions of a problem opened with openLP
    Output
        a list of parsed coefficients as floats
    """
    #Remove any kind of whitespace [ \t\n\r\f\v] from the expression.
    clean = re.sub('\s+', '', expression)

    #Make a list of each term (see termRegex for explanation).
    terms = termRe.findall(clean)

    #Initialize final list.
    signedCoefficients = []
    #signedCoefficients = {}

    for term in terms:
        #The only reason for sign to be omitted is at the beginning (the first term), otherwise it is
        #a term multiplied by another, in other words, it's not linear.
        if term != terms[0] and term[0] == '':
            raise Exception('expression {} is non-linear. Fix term {}.' .format(''.join(clean), ''.join(term)))

        #Create a list of strings containing [sign, value], so that we can append it as a casted float.
        aTerm = [term[0], term[1]]

        #Special case where 1 coefficient is omiitted
        if term[1] == '':
            aTerm[1] = '1'

        #optional: Return a dictionary like {'x1': 1.0, 'x2': 1.0, 'x3': -4.0}
        #signedCoefficients[term[2]] = (float(aTerm[0] + aTerm[1]))

        #Casting takes care for omitted sign of the number.
        signedCoefficients.append(float(aTerm[0] + aTerm[1]))

    #print(signedCoefficients)
    return signedCoefficients

def writeLP2(MinMax, c, A, Eqin, b, inputFile, outputName=''):
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
        output.write('c =\n' + str(array(c)) + '\n\n') # 1 x n
        output.write('A =\n' + str(array(A)) + '\n\n') # m x n
        output.write('Eqin =\n' + str(array(Eqin).reshape(len(Eqin), 1)) + '\n\n') #m x 1
        output.write('b =\n' + str(array(b).reshape(len(b), 1))) #m x 1

def writeLP2json(MinMax, c, A, Eqin, b, inputFile, outputName=''):
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
    with open(outputName, 'w+') as output:
        json.dump(problem, output)

def loadLP2json(inputFile):
    """
    Decription
        Returns a list of coefficients as floats from an expression. It automatically takes care
        of omitted signs or singular coefficients. For example x-2x, will output [ 1. -2.].
    Input
        An LP-2 file name, which contains a problem parsed and saved by this parser in JSON format.
    Output
        In a list
            As floats
                int     MinMax  containing constraints' coefficients
                list    c       containing linear problem's coefficients array and its dimensions
                list    A       containing constraints' coefficients array and its dimensions
                list    Eqin    containing constraints' inequalities array and its dimensions
                list    b       containing constraints' constant parts array and its dimensions
    """
    with open(inputFile, 'r') as input:
        problem = json.load(input)
    #return problem['MinMax'], problem['c'], problem['A'], problem['Eqin'], problem['b']
    return problem

def main(argv):

    inputFile = ''
    outputFile = ''
    exportAsJSON = False

    try:
        opts, args = getopt.getopt(argv[1:], 'hji:o:', ['input=', 'output='])
    except getopt.GetoptError:
        print('Usage: ' + argv[0] + ' -i <inputFile> [options]')
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('Usage: ' + argv[0] + ' -i <inputFile> [options]')
            print('''
    Options:
        -j <json>        : export problem in JSON format
        -o <outputFile>  : define output file name (Default: '(LP-2)<inputFile>')
            ''')
            sys.exit()
        elif opt in ('-i', '--input'):
            inputFile = arg
        elif opt in ('-o', '--output'):
            outputFile = arg
        elif opt in ('-j', '--json'):
            outputFile = arg
            exportAsJSON = True
        else:
            print('Usage: ' + argv[0] + ' -i <inputFile> [options]')
            sys.exit(2)


    problem = openLP(inputFile)
    MinMax = getMinMax(problem)
    c = cVectorExctactor(problem)
    A, Eqin, b = constrainsExtractor(problem)

    """
    print(MinMax)
    print(A)
    print(Eqin)
    print(b)
    print(c)
    """

    if exportAsJSON:
        writeLP2json(MinMax, c, A, Eqin, b, inputFile, outputFile)
    else:
        writeLP2(MinMax, c, A, Eqin, b, inputFile, outputFile)


if __name__ == '__main__':
    main(sys.argv)
