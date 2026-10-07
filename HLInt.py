"""
HLInt.py - A simple interpreter for the hypothetical language "HL".

Usage:
    python HLInt.py <FILENAME.HL>

Pipeline (one stage per section below):
    1. File ingestion
    2. Stream normalization (whitespace stripping)  -> NOSPACES.TXT
    3. Lexical analysis (maximal-munch tokenizer)    -> RES_SYM.TXT
    4. Syntax analysis (recursive descent parser -> AST)
    5. Evaluation (tree-walking interpreter with a symbol table)

The program prints "ERROR" if any stage fails, otherwise it prints the
program's output followed by "NO ERROR(S) FOUND".
"""

import sys
import os


# ==============================================================================
# STAGE 2: STREAM NORMALIZATION & TWO-STATE WHITESPACE STRIPPING
# ==============================================================================
def normalize_stream(raw_text: str) -> str:
    """
    Two-state machine: strips spaces, tabs and newlines outside of string
    literals, but keeps everything inside double quotes exactly as written.
    The state is a boolean flag called in_string, toggled by each double quote.
    """
    in_string = False
    cleaned_chars = []

    for char in raw_text:
        if char == '"':
            in_string = not in_string
            cleaned_chars.append(char)
        elif in_string:
            # Preserve every character inside a string literal verbatim
            cleaned_chars.append(char)
        else:
            # Discard whitespace outside string literals
            if char not in (' ', '\t', '\r', '\n'):
                cleaned_chars.append(char)

    return "".join(cleaned_chars)


# ==============================================================================
# STAGE 3: LEXICAL SCANNING (MAXIMAL-MUNCH TOKENIZER)
# ==============================================================================
RESERVED_WORDS = {"integer", "double", "if", "output"}


class Token:
    def __init__(self, token_type: str, value: str):
        self.type = token_type
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)})"


def tokenize(source_code: str):
    """
    Scans the normalized character stream with maximal munch (1-character
    lookahead) to tell apart ':' vs ':=', '<' vs '<<' vs '<=', etc.

    Returns (tokens, res_and_symbols_log). The log holds the reserved words and
    symbols in order of appearance and is written to RES_SYM.TXT.
    Returns (None, None) on a lexical error.
    """
    tokens = []
    res_and_symbols_log = []
    i = 0
    n = len(source_code)

    while i < n:
        ch = source_code[i]

        # 1. String literal
        if ch == '"':
            start = i
            i += 1
            while i < n and source_code[i] != '"':
                i += 1
            if i >= n:
                return None, None  # Unterminated string literal
            i += 1  # include closing quote
            str_val = source_code[start:i]
            tokens.append(Token("STRING_LITERAL", str_val[1:-1]))
            continue

        # 2. Identifiers and reserved words
        if ch.isalpha() or ch == '_':
            start = i
            while i < n and (source_code[i].isalnum() or source_code[i] == '_'):
                i += 1
            ident = source_code[start:i]
            lower_ident = ident.lower()
            if lower_ident in RESERVED_WORDS:
                tokens.append(Token("RESERVED_WORD", lower_ident))
                res_and_symbols_log.append(lower_ident)
            else:
                tokens.append(Token("IDENTIFIER", ident))
            continue

        # 3. Numeric literals (integers and doubles)
        if ch.isdigit():
            start = i
            while i < n and source_code[i].isdigit():
                i += 1
            if i < n and source_code[i] == '.':
                i += 1
                while i < n and source_code[i].isdigit():
                    i += 1
                tokens.append(Token("DOUBLE_LITERAL", source_code[start:i]))
            else:
                tokens.append(Token("INT_LITERAL", source_code[start:i]))
            continue

        # 4. Multi-character and single-character symbols (maximal munch)
        if ch == ':':
            if i + 1 < n and source_code[i + 1] == '=':
                tokens.append(Token("ASSIGN", ":="))
                res_and_symbols_log.append(":=")
                i += 2
            else:
                tokens.append(Token("COLON", ":"))
                res_and_symbols_log.append(":")
                i += 1
            continue

        if ch == '<':
            if i + 1 < n and source_code[i + 1] == '<':
                tokens.append(Token("OUTPUT_OP", "<<"))
                res_and_symbols_log.append("<<")
                i += 2
            elif i + 1 < n and source_code[i + 1] == '=':
                tokens.append(Token("REL_OP", "<="))
                res_and_symbols_log.append("<=")
                i += 2
            else:
                tokens.append(Token("REL_OP", "<"))
                res_and_symbols_log.append("<")
                i += 1
            continue

        if ch == '>':
            if i + 1 < n and source_code[i + 1] == '=':
                tokens.append(Token("REL_OP", ">="))
                res_and_symbols_log.append(">=")
                i += 2
            else:
                tokens.append(Token("REL_OP", ">"))
                res_and_symbols_log.append(">")
                i += 1
            continue

        if ch == '=':
            if i + 1 < n and source_code[i + 1] == '=':
                tokens.append(Token("REL_OP", "=="))
                res_and_symbols_log.append("==")
                i += 2
            else:
                # The spec also shows assignment written as: x = 3 + 2;
                tokens.append(Token("ASSIGN", "="))
                res_and_symbols_log.append("=")
                i += 1
            continue

        if ch == '!':
            if i + 1 < n and source_code[i + 1] == '=':
                tokens.append(Token("REL_OP", "!="))
                res_and_symbols_log.append("!=")
                i += 2
            else:
                return None, None  # Lone '!' is invalid
            continue

        # Single-character arithmetic and punctuation
        if ch in ('+', '-', ';', '(', ')'):
            token_map = {
                '+': 'ADD_OP',
                '-': 'SUB_OP',
                ';': 'SEMICOLON',
                '(': 'LPAREN',
                ')': 'RPAREN',
            }
            tokens.append(Token(token_map[ch], ch))
            res_and_symbols_log.append(ch)
            i += 1
            continue

        # Unrecognized character -> lexical error
        return None, None

    return tokens, res_and_symbols_log


# ==============================================================================
# STAGE 4: TOP-DOWN RECURSIVE DESCENT PARSER (AST CONSTRUCTION)
# ==============================================================================
class ASTNode:
    pass


class ProgramNode(ASTNode):
    def __init__(self, statements):
        self.statements = statements


class DeclarationNode(ASTNode):
    def __init__(self, var_name, var_type):
        self.var_name = var_name
        self.var_type = var_type


class AssignmentNode(ASTNode):
    def __init__(self, var_name, expr):
        self.var_name = var_name
        self.expr = expr


class OutputNode(ASTNode):
    def __init__(self, target):
        self.target = target  # expression node or StringLiteralNode


class StringLiteralNode(ASTNode):
    def __init__(self, value):
        self.value = value


class BinaryOpNode(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right


class VariableNode(ASTNode):
    def __init__(self, name):
        self.name = name


class NumberNode(ASTNode):
    def __init__(self, value, is_double):
        self.value = value
        self.is_double = is_double


class IfNode(ASTNode):
    def __init__(self, left, op, right, body_statement):
        self.left = left
        self.op = op
        self.right = right
        self.body_statement = body_statement


class Parser:
    """
    Grammar (informal EBNF):
        program     = { statement } ;
        statement   = declaration | assignment | output | if ;
        declaration = IDENT ":" ( "integer" | "double" ) ";" ;
        assignment  = IDENT ( ":=" | "=" ) expression ";" ;
        output      = "output" "<<" ( STRING | expression ) ";" ;
        if          = "if" "(" expression RELOP expression ")" statement ;
        expression  = term { ( "+" | "-" ) term } ;
        term        = INT | DOUBLE | IDENT ;
    Each rule is implemented as one method.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current_token(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def match(self, expected_type, expected_val=None):
        tok = self.current_token()
        if tok and tok.type == expected_type:
            if expected_val is None or tok.value.lower() == expected_val.lower():
                self.pos += 1
                return tok
        return None

    def expect(self, expected_type, expected_val=None):
        tok = self.match(expected_type, expected_val)
        if not tok:
            raise SyntaxError(
                f"Expected {expected_type} {expected_val}, got {self.current_token()}"
            )
        return tok

    def parse_program(self):
        statements = []
        while self.pos < len(self.tokens):
            statements.append(self.parse_statement())
        return ProgramNode(statements)

    def parse_statement(self):
        tok = self.current_token()
        if not tok:
            raise SyntaxError("Unexpected end of tokens.")

        if tok.type == "RESERVED_WORD" and tok.value == "if":
            return self.parse_if_statement()

        if tok.type == "RESERVED_WORD" and tok.value == "output":
            return self.parse_output_statement()

        if tok.type == "IDENTIFIER":
            # Look at the next token to choose declaration vs assignment
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == "COLON":
                return self.parse_declaration_statement()
            elif self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == "ASSIGN":
                return self.parse_assignment_statement()
            else:
                raise SyntaxError("Malformed statement starting with identifier.")

        raise SyntaxError(f"Unrecognized statement starting with {tok}")

    def parse_declaration_statement(self):
        ident_tok = self.expect("IDENTIFIER")
        self.expect("COLON")
        type_tok = self.expect("RESERVED_WORD")
        if type_tok.value not in ("integer", "double"):
            raise SyntaxError("Invalid data type specifier.")
        self.expect("SEMICOLON")
        return DeclarationNode(ident_tok.value, type_tok.value)

    def parse_assignment_statement(self):
        ident_tok = self.expect("IDENTIFIER")
        self.expect("ASSIGN")
        expr = self.parse_expression()
        self.expect("SEMICOLON")
        return AssignmentNode(ident_tok.value, expr)

    def parse_output_statement(self):
        self.expect("RESERVED_WORD", "output")
        self.expect("OUTPUT_OP", "<<")
        tok = self.current_token()
        if tok and tok.type == "STRING_LITERAL":
            self.pos += 1
            target = StringLiteralNode(tok.value)
        else:
            target = self.parse_expression()
        self.expect("SEMICOLON")
        return OutputNode(target)

    def parse_if_statement(self):
        self.expect("RESERVED_WORD", "if")
        self.expect("LPAREN")
        left = self.parse_expression()
        rel_tok = self.expect("REL_OP")
        right = self.parse_expression()
        self.expect("RPAREN")
        body = self.parse_statement()
        return IfNode(left, rel_tok.value, right, body)

    def parse_expression(self):
        left = self.parse_term()
        while True:
            tok = self.current_token()
            if tok and tok.type in ("ADD_OP", "SUB_OP"):
                self.pos += 1
                right = self.parse_term()
                left = BinaryOpNode(left, tok.value, right)
            else:
                break
        return left

    def parse_term(self):
        tok = self.current_token()
        if not tok:
            raise SyntaxError("Unexpected end of expression.")

        if tok.type == "INT_LITERAL":
            # Spec: integers are single digit
            if len(tok.value) > 1:
                raise SyntaxError(f"Integer literal '{tok.value}' must be single digit.")
            self.pos += 1
            return NumberNode(int(tok.value), is_double=False)

        if tok.type == "DOUBLE_LITERAL":
            # Spec: doubles have a precision of 2 decimal places
            self.pos += 1
            return NumberNode(round(float(tok.value), 2), is_double=True)

        if tok.type == "IDENTIFIER":
            self.pos += 1
            return VariableNode(tok.value)

        raise SyntaxError(f"Expected number or identifier, got {tok}")


# ==============================================================================
# STAGE 5: EVALUATION ENGINE & TREE-WALKING INTERPRETER
# ==============================================================================
class Interpreter:
    def __init__(self):
        # var_name -> {'type': 'integer' | 'double', 'value': int | float}
        self.symbol_table = {}
        self.output_buffer = []

    def evaluate_expression(self, node):
        """Returns (value, is_double)."""
        if isinstance(node, NumberNode):
            return node.value, node.is_double

        if isinstance(node, VariableNode):
            var_name = node.name.lower()
            if var_name not in self.symbol_table:
                raise RuntimeError(f"Variable '{node.name}' not declared before use.")
            entry = self.symbol_table[var_name]
            return entry['value'], (entry['type'] == 'double')

        if isinstance(node, BinaryOpNode):
            l_val, l_is_double = self.evaluate_expression(node.left)
            r_val, r_is_double = self.evaluate_expression(node.right)
            is_double = l_is_double or r_is_double

            if node.op == '+':
                res = l_val + r_val
            elif node.op == '-':
                res = l_val - r_val
            else:
                raise RuntimeError(f"Unsupported operator {node.op}")

            if is_double:
                res = round(float(res), 2)
            return res, is_double

        raise RuntimeError("Invalid expression node.")

    def execute(self, node):
        if isinstance(node, ProgramNode):
            for stmt in node.statements:
                self.execute(stmt)

        elif isinstance(node, DeclarationNode):
            var_name = node.var_name.lower()
            # Default initial values: 0 for integer, 0.00 for double
            init_val = 0 if node.var_type == "integer" else 0.00
            self.symbol_table[var_name] = {'type': node.var_type, 'value': init_val}

        elif isinstance(node, AssignmentNode):
            var_name = node.var_name.lower()
            if var_name not in self.symbol_table:
                raise RuntimeError(f"Cannot assign to undeclared variable '{node.var_name}'.")
            val, _ = self.evaluate_expression(node.expr)
            if self.symbol_table[var_name]['type'] == 'integer':
                self.symbol_table[var_name]['value'] = int(val)
            else:
                self.symbol_table[var_name]['value'] = round(float(val), 2)

        elif isinstance(node, OutputNode):
            if isinstance(node.target, StringLiteralNode):
                self.output_buffer.append(node.target.value)
            else:
                val, is_double = self.evaluate_expression(node.target)
                # Doubles are always shown with exactly 2 decimal places
                self.output_buffer.append(f"{val:.2f}" if is_double else str(val))

        elif isinstance(node, IfNode):
            l_val, _ = self.evaluate_expression(node.left)
            r_val, _ = self.evaluate_expression(node.right)
            truth = {
                '<': l_val < r_val,
                '>': l_val > r_val,
                '==': l_val == r_val,
                '!=': l_val != r_val,
                '<=': l_val <= r_val,
                '>=': l_val >= r_val,
            }.get(node.op, False)
            if truth:
                self.execute(node.body_statement)


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def main():
    if len(sys.argv) < 2:
        print("Usage: python HLInt.py <FILENAME.HL>")
        sys.exit(1)

    # Stage 1: file ingestion
    source_filepath = sys.argv[1]
    if not os.path.exists(source_filepath):
        print("ERROR")
        sys.exit(1)
    try:
        with open(source_filepath, 'r') as f:
            raw_source = f.read()
    except Exception:
        print("ERROR")
        sys.exit(1)

    # Stage 2: whitespace stripping -> NOSPACES.TXT
    normalized_code = normalize_stream(raw_source)
    with open("NOSPACES.TXT", "w") as f:
        f.write(normalized_code)

    # Stage 3: tokenizing -> RES_SYM.TXT
    tokens, res_sym_log = tokenize(normalized_code)
    if tokens is None:
        print("ERROR")
        return
    with open("RES_SYM.TXT", "w") as f:
        for item in res_sym_log:
            f.write(f"{item}\n")

    # Stage 4: syntax analysis
    try:
        ast = Parser(tokens).parse_program()
    except SyntaxError:
        print("ERROR")
        return

    # Stage 5: execution
    interpreter = Interpreter()
    try:
        interpreter.execute(ast)
    except Exception:
        print("ERROR")
        return

    for out in interpreter.output_buffer:
        print(out)
    print("NO ERROR(S) FOUND")


if __name__ == "__main__":
    main()
