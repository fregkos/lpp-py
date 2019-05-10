# lpp-py
Linear problem parser in Python.

## Usage
```
lpp.py -i <inputFile> [options]
```
### Example usage:
```
python3 lpp.py -i LP01.LTX
```

## Options
```
    -j, --json                : export problem in JSON format
    -o, --output <outputFile> : define output file name
                                (Default: '(LP-2)<inputFile>')
    -d, --dual                : convert the problem from primal to dual form
```

## For help, use:
```
python3 lpp.py -h
```
or
```
python3 lpp.py --help
```
