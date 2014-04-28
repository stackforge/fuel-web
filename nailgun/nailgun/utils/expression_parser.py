#    Copyright 2014 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from nailgun.errors import errors
import ply.lex
import ply.yacc
import tempfile

tokens = (
    'NUMBER', 'STRING', 'TRUE', 'FALSE', 'AND', 'OR', 'NOT', 'MODELPATH',
    'EQUALS', 'NOT_EQUALS', 'LPAREN', 'RPAREN'
)


def t_NUMBER(t):
    r'-?\d+'
    t.value = int(t.value)
    return t


def t_STRING(t):
    r'(?P<openingquote>["\']).*?(?P=openingquote)'
    t.value = t.value[1:-1]
    return t


def t_TRUE(t):
    r'true'
    t.value = True
    return t


def t_FALSE(t):
    r'false'
    t.value = False
    return t


t_AND = r'and'
t_OR = r'or'
t_NOT = r'not'
t_EQUALS = r'=='
t_NOT_EQUALS = r'!='
t_LPAREN = r'\('
t_RPAREN = r'\)'

t_ignore = ' \t\r\n'


def t_error(t):
    errors.ParseError("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


ply.lex.lex()

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('left', 'EQUALS', 'NOT_EQUALS'),
    ('left', 'NOT'),
)


def p_statement_expr(p):
    """statement : expression
    """
    print(p[1])


def p_expression_binop(p):
    """expression : expression EQUALS expression
                  | expression NOT_EQUALS expression
                  | expression OR expression
                  | expression AND expression
    """
    if p[2] in ('==', '!=', 'or', 'and'):
        p[0] = p[1] == p[3]


def p_not_expression(p):
    """expression : NOT expression
    """
    p[0] = not p[2]


def p_expression_group(p):
    """expression : LPAREN expression RPAREN
    """
    p[0] = p[2]


def p_expression_scalar(p):
    """expression : NUMBER
                  | STRING
                  | TRUE
                  | FALSE
    """
    p[0] = p[1]


def p_error(p):
    raise errors.ParseError("Syntax error at '%s'" % getattr(p, 'value', ''))


parser = ply.yacc.yacc(debug=False, outputdir=tempfile.gettempdir())
