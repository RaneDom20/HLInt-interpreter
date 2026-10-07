# HLInt: A Simple Interpreter for the HL Language

**Course project (CSS125P).** HLInt reads a program written in a small hypothetical language called **HL** and executes it.

**Team:** Marlon, Viggo, Dom
**Video explanation:** https://mymailmapuaedu-my.sharepoint.com/:v:/g/personal/drpgorre_mymail_mapua_edu_ph/IQBhDpmvziPmS57ks8Ks7Kt7AcrRqy0mRdEui-ayjqn7QsY?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=oJCodJ

## What HL supports

| Feature | Example |
|---|---|
| Variable declaration (`integer`, `double`) | `x:integer;` `y:double;` |
| Assignment | `x:=5;` `y:=2.35;` (`x = 3 + 2;` is also accepted) |
| Addition and subtraction (single-digit integers, doubles to 2 decimal places) | `y:=4+2.56;` |
| Output to screen | `output<<"hello";` `output<<x;` `output<<x+y;` |
| One-way `if` with `<`, `>`, `==`, `!=` (also `<=`, `>=`) | `if(x<5) output<<x;` |

## How to run

Requires Python 3. No extra libraries.

```
python HLInt.py PROG1.HL
python HLInt.py PROG2.HL
python HLInt.py PROG3.HL
```

## What it does

When HLInt runs, it opens the source file and goes through five stages:

1. **File ingestion**: reads the `.HL` file.
2. **Stream normalization**: removes all whitespace outside string literals using a two-state machine (an `in_string` flag toggled by double quotes) and writes the result to **`NOSPACES.TXT`**.
3. **Lexical analysis**: a tokenizer using the maximal-munch rule (one-character lookahead) separates `:` from `:=` and `<` from `<<`. Reserved words and symbols are written to **`RES_SYM.TXT`**.
4. **Syntax analysis**: a top-down recursive descent parser checks the grammar and builds an abstract syntax tree (AST).
5. **Evaluation**: a tree-walking interpreter with a symbol table (a dictionary) runs the AST.

The screen shows the program's output followed by `NO ERROR(S) FOUND`, or just `ERROR` if there is any syntax or semantic error (for example a missing semicolon or an undeclared variable).

## Sample programs and expected output

| File | Output |
|---|---|
| `PROG1.HL` | `5` then `NO ERROR(S) FOUND` |
| `PROG2.HL` | `4.25` then `NO ERROR(S) FOUND` |
| `PROG3.HL` | `3` then `NO ERROR(S) FOUND` |

`NOSPACES.TXT` and `RES_SYM.TXT` in this repo were generated from `PROG2.HL`.

## Extra tests (`tests/`)

| File | Expected result |
|---|---|
| `ERROR_missing_semicolon.HL` | `ERROR` |
| `ERROR_undeclared_variable.HL` | `ERROR` |
| `ERROR_two_digit_integer.HL` | `ERROR` |
| `IF_false_prints_nothing.HL` | only `NO ERROR(S) FOUND` |
| `IF_operators.HL` | `x is four`, `3`, `NO ERROR(S) FOUND` |
| `STRING_keeps_spaces.HL` | `hello world from HL` (spaces preserved) |
| `DOUBLE_math_and_equals_sign.HL` | `6.56`, `5`, `NO ERROR(S) FOUND` |

Run any of them with, for example: `python HLInt.py tests/STRING_keeps_spaces.HL`

## Files

```
HLInt.py          the interpreter
PROG1.HL          sample program 1
PROG2.HL          sample program 2
PROG3.HL          sample program 3
NOSPACES.TXT      sample output of stage 2
RES_SYM.TXT       sample output of stage 3
tests/            extra test programs
```
