import re
import sys
import getopt

from extractors import *
from lpIO import *
from converters import *

"""
    Author
        Periklis Fregkos (https://github.com/Leajian)
    Program name
        Linear Problem Parser (lpp)
    Version
        2.2
"""


def main(argv):

    # Initialize varibales.
    inputFile = ''
    outputFile = ''
    loadJSON = False
    exportType = 'default'
    dual = False
    justPrint = False

    ## BUG: Can't use -o and -j together.
    try:
        opts, args = getopt.getopt(argv[1:], 'hjpsi:o:dl:', ['input=', 'output=', 'load='])
    except getopt.GetoptError:
        print('Usage: ' + argv[0] + ' -i <inputFile> [options]')
        print('For more options, type: ' + argv[0] + ' -h')
        sys.exit(1)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('Usage: ' + argv[0] + ' -i <inputFile> [options]')
            print('''
Options:
    -i, --input  <inputFile>  : define input file name (mutually exclusive with -l)
    -l, --load   <inputFile>  : define input JSON file name to load
    -j, --json                : export problem in JSON format
    -o, --output <outputFile> : define output file name
                                (Default: '(LP-2)<inputFile>')
    -p, --print               : print the human readable output in the console
    -s, --simple              : export the simple human readable format
    -d, --dual                : convert the problem from primal to dual form
''')
            sys.exit()
        elif opt in ('-i', '--input'):
            inputFile = arg
        elif opt in ('-o', '--output'):
            outputFile = arg
        elif opt in ('-j', '--json'):
            outputFile = arg
            exportType = 'json'
        elif opt in ('-l', '--load'):
            inputFile = arg
            loadJSON = True
        elif opt in ('-d', '--dual'):
            dual = True
        elif opt in ('-p', '--print'):
            justPrint = True
        elif opt in ('-s', '--simple'):
            exportType = 'human'
        else:
            print('Usage: ' + argv[0] + ' -i <inputFile> [options]')
            sys.exit(2)

    if not loadJSON:
        
        # Open the linear problem file.
        problem, hasNaturalConstraints = openLP(inputFile)

        # Discover the variable names.
        vars = discoverProblemVariables(problem)

        # Call order may matter, as all functions access the initial problem list.

        # Get problem type.
        MinMax = MinMaxExtractor(problem)
        # Extract objective function's coefficients.
        c = cVectorExctactor(problem, vars)
        # Extract constraints' coefficients, constraint types and their constants.
        A, Eqin, b = constraintsExtractor(problem, vars)
        # If hasNaturalConstraints is False, then naturalConstraints will be a
        # numpy.array containing 1 for all variables. Thus, it's always initialized.
        naturalConstraints = naturalConstraintsExtractor(problem, vars, hasNaturalConstraints)
    
    else:
        MinMax, c, A, Eqin, b, naturalConstraints = loadLP2json(inputFile)

    # If dual mode it selected, alter those variables to their dual form.
    if dual:
        MinMax, c, A, Eqin, b, naturalConstraints = primalToDual(MinMax, c, A, Eqin, b, naturalConstraints)
    
    # Just save the data or print it.
    if not justPrint:
        # Export in the desired format.
        if exportType == 'json':
            writeLP2json(MinMax, c, A, Eqin, b, naturalConstraints, inputFile, outputFile)
        elif exportType == 'human':
            print('WARNING! This output is not meant for parsing, it\'s unreliable.')
            print('It\'s only for demonstration purposes!\nUse --json for JSON format instead.')

            writeLP2HumanReadable(MinMax, c, A, Eqin, b, naturalConstraints, inputFile, outputFile)
        else:
            print('WARNING! This output is not meant for parsing, it\'s unreliable.')
            print('It\'s only for demonstration purposes!\nUse --json for JSON format instead.')

            writeLP2(MinMax, c, A, Eqin, b, naturalConstraints, inputFile, outputFile)
        
    else:

        if MinMax == 1:
            print('max', end='\t')
        elif MinMax == -1:
            print('min', end='\t')
        for i, coeff in enumerate(c, start=1):
            # Ignore those with 0 coefficient
            if coeff == 0.0:
                print('\t', end='')
                continue

            # Put back the plus sign, unless it's the first term
            if str(coeff)[0] != '-' and i != 1:
                coeff = '+' + str(coeff)

            print(str(coeff) +'x' + str(i), end='\t')
        print('')

        print('s.t.', end='')

        # For each row
        for i in zip(A, Eqin, b):
            print('\t', end='')

            # Enumarate each coefficient so we can name them
            for j, coeff in enumerate(i[0], start=1):
                # Ignore those with 0 coefficient
                if coeff == 0.0:
                    print('\t', end='')
                    continue

                # Put back the plus sign, unless it's the first term
                if str(coeff)[0] != '-' and j != 1:
                    coeff = '+' + str(coeff)
                
                # Printing each term
                print(str(coeff) + 'x' + str(j), end='\t')

            # Mapping the signs
            signs = {'0': '= ', '1':'>=', '-1':'<='}
            
            print(signs[str(squeeze(i[1]))] + ' ' + str(squeeze(i[2])), end='\n')

        # Mapping the signs
        signs = {'0': 'free', '1':'>= 0', '-1':'<= 0'}
        for i, constr in enumerate(naturalConstraints, start=1):
            # Printing each constraint
            print('x' + str(i) + ' ' + signs[str(squeeze(constr))], end='')
            if i != len(naturalConstraints):
                print(', ', end='')
        print('\n')


if __name__ == '__main__':
    main(sys.argv)
