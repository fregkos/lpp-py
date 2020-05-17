import re
import json
from numpy import array, squeeze


def sanityCheck(problem):
    hasNaturalConstraints = False
    keywordPattern = re.compile('max|min|s\.?t\.?|subject\s*to|with|end', re.IGNORECASE)
    keywords = re.findall(keywordPattern, problem)

    if re.match('max|min', keywords[0], re.IGNORECASE):
        if len(keywords) >= 2 and re.match('s\.?t\.?|subject\s*to', keywords[1], re.IGNORECASE):

            if len(keywords) == 4 and re.match('with', keywords[2], re.IGNORECASE):
                hasNaturalConstraints = True
                    
                if not re.match('end', keywords[3], re.IGNORECASE):
                    raise Exception('Expression "end" not found, include it after you end the problem\'s description.')

            if len(keywords) == 3:
                print('WARNING! Expression "with" not found. Assuming all constraints are non-negative.')

                if not re.match('end', keywords[2], re.IGNORECASE):
                    raise Exception('Expression "end" not found, include it after you end the problem\'s description.')
                     
        else:
            raise Exception('Expression "s.t." or "st" or "subject to" not found, include it after you state the objective function.')
    else:
        raise Exception('Expression "min" or "max" not found, include it at the beginning of the problem\'s description.')

    return hasNaturalConstraints

def openLP(fileName, hasNaturalConstraints=False):
    """
    Description
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
        hasNaturalConstraints = sanityCheck(problem)

        # Cut the file into segments, from one keyword to another
        # (#1 max/min, #2 st, #optional with, #3 end).
        pattern = re.compile('s\.?\s*t\.?|subject\s*to|with|end', re.IGNORECASE)
        segmentedList = pattern.split(problem)

        # Unless 'with' natural constraints are given indeed,
        # we must return 3 parts.
        if hasNaturalConstraints:
            return segmentedList[:3], hasNaturalConstraints

        # Otherwise, we return only the first 2 parts,
        # but from 2 and beyond include the part with "end" delimiter,
        # which might contain nothing, a new line character or more than that
        # We don't care about content past the "end" delimiter.
        # Any other whitespace character is managed when necessary.
        # If there is any gibberish, the corresponding extractor function
        # is responsible to figure it out.
        return segmentedList[:2], hasNaturalConstraints

def writeLP2(MinMax, c, A, Eqin, b, naturalConstraints, inputFile, outputName=''):
    """
    Description
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
        outputName = '(LP-2) ' + inputFile
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
        output.write('naturalConstraints =\n' + str(squeeze(array(naturalConstraints).reshape(1, len(naturalConstraints))).tolist()) + '\n\n')  # 1 x n

def writeLP2HumanReadable(MinMax, c, A, Eqin, b, naturalConstraints, inputFile, outputName=''):
    """
    Description
        Writes the linear problem to a file in a human readable form.
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
        A file which describes the problem in a human readable form.
    """
    if outputName == '':
        outputName = '(LP-2) ' + inputFile
    with open(outputName, 'w+') as output:

        if MinMax == 1:
            output.write('max\t')
        elif MinMax == -1:
            output.write('min\t')

        # Enumarate each coefficient so we can name them
        for i, coeff in enumerate(c, start=1):
            # Ignore those with 0 coefficient
            if coeff == 0:
                output.write('\t')
                continue

            # Put back the plus sign, unless it's the first term
            if str(coeff)[0] != '-' and i != 1:
                coeff = '+' + str(coeff)

            output.write(str(coeff) +'x' + str(i) + '\t')
        output.write('\n')

        output.write('s.t.')

        # For each row
        for i in zip(A, Eqin, b):
            output.write('\t')

            # Enumarate each coefficient so we can name them
            for j, coeff in enumerate(i[0], start=1):
                # Ignore those with 0 coefficient
                if coeff == 0.0:
                    output.write('\t')
                    continue

                # Put back the plus sign, unless it's the first term
                if str(coeff)[0] != '-' and j != 1:
                    coeff = '+' + str(coeff)
                
                # Writting each term
                output.write(str(coeff) + 'x' + str(j) + '\t')
            
            # Mapping the signs
            signs = {'0': '= ', '1':'>=', '-1':'<='}
            
            output.write(signs[str(squeeze(i[1]))] + ' ' + str(squeeze(i[2])) + '\n')

        # Mapping the signs
        signs = {'0': 'free', '1':'>= 0', '-1':'<= 0'}
        for i, constr in enumerate(naturalConstraints, start=1):
            # Writting each constraint
            
            output.write('x' + str(i) + ' ' + signs[str(squeeze(constr))])
            if i != len(naturalConstraints):
                output.write(', ')
        output.write('\n')

"""
JSON-related
"""

def writeLP2json(MinMax, c, A, Eqin, b, naturalConstraints, inputFile, outputName=''):
    """
    Description
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
        outputName = '(LP-2) ' + inputFile + '.json'
    problem = {
        'MinMax': MinMax,
        'c': c.tolist(),
        'A': A.tolist(),
        'Eqin': Eqin.tolist(),
        'b': b.tolist(),
        'naturalConstraints': naturalConstraints
        }

    with open(outputName, 'w+') as output:
        json.dump(problem, output, indent=1)

def loadLP2json(inputFile):
    """
    Description
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
    with open(inputFile, 'r') as f:
        problem = json.load(f)

    MinMax = problem['MinMax']
    c = array(problem['c'])
    A = array(problem['A'])
    Eqin = array(problem['Eqin'])
    b = array(problem['b'])
    naturalConstraints = problem['naturalConstraints']
    
    return MinMax, c, A, Eqin, b, naturalConstraints
