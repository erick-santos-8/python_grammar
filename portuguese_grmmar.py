# PEG grammar for Python



# ========================= START OF THE GRAMMAR =========================

# General grammatical elements and rules:
#
# * Strings with double quotes (") denote SOFT KEYWORDS
# * Strings with single quotes (') denote KEYWORDS
# * Upper case names (NAME) denote tokens in the Grammar/Tokens file
# * Rule names starting with "invalid_" are used for specialized syntax errors
#     - These rules are NOT used in the first pass of the parser.
#     - Only if the first pass fails to parse, a second pass including the invalid
#       rules will be executed.
#     - If the parser fails in the second phase with a generic syntax error, the
#       location of the generic failure of the first pass will be used (this avoids
#       reporting incorrect locations due to the invalid rules).
#     - The order of the alternatives involving invalid rules matter
#       (like any rule in PEG).
#
# Grammar Syntax (see PEP 617 for more information):
#
# rule_name: expression
#   Optionally, a type can be included right after the rule name, which
#   specifies the return type of the C or Python function corresponding to the
#   rule:
# rule_name[return_type]: expression
#   If the return type is omitted, then a void * is returned in C and an Any in
#   Python.
# e1 e2
#   Match e1, then match e2.
# e1 | e2
#   Match e1 or e2.
#   The first alternative can also appear on the line after the rule name for
#   formatting purposes. In that case, a | must be used before the first
#   alternative, like so:
#       rule_name[return_type]:
#            | first_alt
#            | second_alt
# ( e )
#   Match e (allows also to use other operators in the group like '(e)*')
# [ e ] or e?
#   Optionally match e.
# e*
#   Match zero or more occurrences of e.
# e+
#   Match one or more occurrences of e.
# s.e+
#   Match one or more occurrences of e, separated by s. The generated parse tree
#   does not include the separator. This is otherwise identical to (e (s e)*).
# &e
#   Succeed if e can be parsed, without consuming any input.
# !e
#   Fail if e can be parsed, without consuming any input.
# ~
#   Commit to the current alternative, even if it fails to parse.
# &&e
#   Eager parse e. The parser will not backtrack and will immediately 
#   fail with SyntaxError if e cannot be parsed.
#

# REGRAS INCIAIS
# ==============

arquivo: [instruções] FIM 
modo_interativo: instrução_novalinha 
sequencia_expressões: expressões NOVALINHA* FIM 
tipo_função: '(' [tipo_expressões] ')' '->' expressão NOVALINHA* FIM 

# INSTRUÇÕES GERAIS (STATEMENTS)
# ==================

instruções: instrução+ 

instrução: instrução_composta  | instruções_simples 

instrução_novalinha:
    | instrução_composta NOVALINHA 
    | instrução_simples
    | NOVALINHA 
    | FIM 

instruções_simples:
    | instrução_simples !';' NOVALINHA  # Not needed, there for speedup
    | ';'.instrução_simples+ [';'] NOVALINHA 

# NOTE: assignment MUST precede expression, else parsing a simple assignment
# will throw a SyntaxError.
instrução_simples:
    | atribuição
    | tipo_alias
    | expressões_estrela 
    | retorno_instrução
    | importar_instrução
    | lançar_instrução
    | 'pass' 
    | deletar_instrução
    | yield_instrução
    | assert_instrução #?
    | 'break' # interromper 
    | 'continue' #continuar
    | global_instrução
    | naolocal_instrução

instrução_composta:
    | defininir_função
    | se_instrução
    | definir_classe
    | with_stmt # com_instrução
    | for_stmt # laço_instrução
    | tentar_instrução 
    | enquanto_instrução
    | match_stmt # ?

# SIMPLE STATEMENTS
# =================

# NOTE: annotated_rhs may start with 'yield'; yield_expr must start with 'yield'
atribuição:
    | NOME ':' expressão ['=' annotated_rhs ]  #annotated_rhs é uma expressão anotada com tipo ou uma expressão que pode envolver yield. Talvez anotação_rhs?
    | ('(' alvo_unico ')' 
         | alvo_unico_subscrito_atributo) ':' expressão ['=' annotated_rhs ] 
    | (alvo_estrela '=' )+ (yield_expressão | expressões_estrela) !'=' [TYPE_COMMENT]  #TYPE_COMMENT = Tipo de comentário?
    | single_target augassign ~ (yield_expressão | expressões_estrela) 

annotated_rhs: yield_expressão | expressões_estrela

atribuição_reduzida: #augassing
    | '+=' 
    | '-=' 
    | '*=' 
    | '@=' 
    | '/=' 
    | '%=' 
    | '&=' 
    | '|=' 
    | '^=' 
    | '<<=' 
    | '>>=' 
    | '**=' 
    | '//=' 

retorno_instrução:
    | 'retornar' [expressões_estrela] 

lançar_instrução:
    | 'lançar' expressão ['de' expressão ] 
    | 'lançar' 

global_instrução: 'global' ','.NOME+ 

naolocal_instrução: 'naolocal' ','.NOME+ 

deletar_instrução:
    | 'deletar' deletar_alvos &(';' | NOVALINHA) 

yield_instrução: yield_expressão 

assert_instrução: 'assert' expressão [',' expressão ] 

importar_instrução:
    | importar_nome
    | importar_de

# Import instruções
# -----------------

importar_nome: 'importar' nomes_com_pontos #dotted_as_names = modulos ou pacotes
# note below: the ('.' | '...') is necessary because '...' is tokenized as ELLIPSIS
importar_de:
    | 'de' ('.' | '...')* nome_pontuado 'importar' importar_dos_alvos #import_from_targets 
    | 'de' ('.' | '...')+ 'importar' importar_dos_alvos #import_from_targets 
importar_dos_alvos:
    | '(' importar_de_como_nomes [','] ')' 
    | importar_de_como_nomes !','
    | '*' 
importar_de_como_nomes:
    | ','.importar_de_como_nome+ 
importar_de_como_nome:
    | NOME ['como' NOME ] 
nomes_com_pontos:
    | ','.nome_com_pontos+ 
nome_com_pontos:
    | nome_pontuado ['como' NOME ] 
nome_pontuado:
    | nome_pontuado '.' NOME 
    | NOME

# COMPOUND STATEMENTS
# ===================

# Common elements
# ---------------

bloco_codigo: #block
    | NOVALINHA ESPAÇAR instruções RECUAR 
    | instruções_simples

decoradores: ('@' expressão_nomeada NOVALINHA )+  

# Class definitions
# -----------------

definir_classe:
    | decoradores definir_classe_sintaxe #class_def_raw 
    | definir_classe_sintaxe

definir_classe_sintaxe:
    | 'classe' NOME [tipos_lista_parâmetros] ['(' [argumentos] ')' ] ':' bloco_codigo 

# Function definitions
# --------------------

defininir_função:
    | decoradores definir_função_sintaxe #function_def_raw 
    | definir_função_sintaxe

definir_função_sintaxe:
    | 'definir' NOME [tipos_lista_parâmetros] '(' [lista_parâmetros] ')' ['->' expressão ] ':' [funcão_type_comment] bloco_codigo #type_comment 
    | 'assíncrono' 'definir' NOME [tipos_lista_parâmetros] '(' [lista_parâmetros] ')' ['->' expressão ] ':' [função_type_comment] bloco_codigo 

# Function parameters
# -------------------

lista_parâmetros:
    | parâmetros

parâmetros:
    | posição_sem_padrão parâmetro_sem_padrão* parâmetro_com_padrão* [estrela_etc] #slash_no_default param_no_default* param_with_default* [star_etc] 
    | posição_com_padrão parâmetro_com_padrão* [estrela_etc] 
    | parâmetro_sem_padrão+ posição_com_padrão* [estrela_etc] 
    | posição_com_padrão+ [estrela_etc] 
    | estrela_etc 

# Some duplication here because we can't write (',' | &')'),
# which is because we don't support empty alternatives (yet).

posição_sem_padrão:
    | parâmetro_sem_padrão+ '/' ',' 
    | parâmetro_sem_padrão+ '/' &')' 
posição_com_padrão:
    | parâmetro_sem_padrão* parâmetro_com_padrão+ '/' ',' 
    | parâmetro_sem_padrão* parâmetro_com_padrão+ '/' &')' 

estrela_etc:
    | '*' parâmetro_sem_padrão parâmetro_talvez_padrão* [kwds]  #kwds é palavra-chave
    | '*' parâmetro_sem_padrão_anotação_estrela parâmetro_talvez_padrão* [kwds]  #param_no_default_star_annotation param_maybe_default* [kwds] 
    | '*' ',' parâmetro_talvez_padrão+ [kwds] 
    | kwds 

kwds:
    | '**' parâmetro_sem_padrão 

# One parameter.  This *includes* a following comma and type comment.
#
# There are three styles:
# - No default
# - With default
# - Maybe with default
#
# There are two alternative forms of each, to deal with type comments:
# - Ends in a comma followed by an optional type comment
# - No comma, optional type comment, must be followed by close paren
# The latter form is for a final parameter without trailing comma.
#

parâmetro_sem_padrão:
    | lista_parâmetros ',' TYPE_COMMENT? 
    | lista_parâmetros TYPE_COMMENT? &')' 
parâmetro_sem_padrão_anotação_estrela:
    | parâmetro_anotação_estrela ',' TYPE_COMMENT? 
    | parâmetro_anotação_estrela TYPE_COMMENT? &')' 
parâmetro_com_padrão:
    | lista_parâmetros padrão ',' TYPE_COMMENT? 
    | lista_parâmetros padrão TYPE_COMMENT? &')' 
param_maybe_default:
    | lista_parâmetros padrão? ',' TYPE_COMMENT? 
    | lista_parâmetros padrão? TYPE_COMMENT? &')' 
lista_parâmetros: NOME anotação? 
parâmetro_anotação_estrela: NOME anotação_estrela 
anotação: ':' expressão 
anotação_estrela: ':' expressão_estrela 
padrão: '=' expressão  | padrão_invalido

# If statement
# ------------

if_stmt:
    | 'if' named_expression ':' block elif_stmt 
    | 'if' named_expression ':' block [else_block] 
elif_stmt:
    | 'elif' named_expression ':' block elif_stmt 
    | 'elif' named_expression ':' block [else_block] 
else_block:
    | 'else' ':' block 

# While statement
# ---------------

while_stmt:
    | 'while' named_expression ':' block [else_block] 

# For statement
# -------------

for_stmt:
    | 'for' star_targets 'in' ~ star_expressions ':' [TYPE_COMMENT] block [else_block] 
    | 'async' 'for' star_targets 'in' ~ star_expressions ':' [TYPE_COMMENT] block [else_block] 

# With statement
# --------------

with_stmt:
    | 'with' '(' ','.with_item+ ','? ')' ':' [TYPE_COMMENT] block 
    | 'with' ','.with_item+ ':' [TYPE_COMMENT] block 
    | 'async' 'with' '(' ','.with_item+ ','? ')' ':' block 
    | 'async' 'with' ','.with_item+ ':' [TYPE_COMMENT] block 

with_item:
    | expression 'as' star_target &(',' | ')' | ':') 
    | expression 

# Try statement
# -------------

try_stmt:
    | 'try' ':' block finally_block 
    | 'try' ':' block except_block+ [else_block] [finally_block] 
    | 'try' ':' block except_star_block+ [else_block] [finally_block] 


# Except statement
# ----------------

except_block:
    | 'except' expression ['as' NAME ] ':' block 
    | 'except' ':' block 
except_star_block:
    | 'except' '*' expression ['as' NAME ] ':' block 
finally_block:
    | 'finally' ':' block 

# Match statement
# ---------------

match_stmt:
    | "match" subject_expr ':' NEWLINE INDENT case_block+ DEDENT 

subject_expr:
    | star_named_expression ',' star_named_expressions? 
    | named_expression

case_block:
    | "case" patterns guard? ':' block 

guard: 'if' named_expression 

patterns:
    | open_sequence_pattern 
    | pattern

pattern:
    | as_pattern
    | or_pattern

as_pattern:
    | or_pattern 'as' pattern_capture_target 

or_pattern:
    | '|'.closed_pattern+ 

closed_pattern:
    | literal_pattern
    | capture_pattern
    | wildcard_pattern
    | value_pattern
    | group_pattern
    | sequence_pattern
    | mapping_pattern
    | class_pattern

# Literal patterns are used for equality and identity constraints
literal_pattern:
    | signed_number !('+' | '-') 
    | complex_number 
    | strings 
    | 'None' 
    | 'True' 
    | 'False' 

# Literal expressions are used to restrict permitted mapping pattern keys
literal_expr:
    | signed_number !('+' | '-')
    | complex_number
    | strings
    | 'None' 
    | 'True' 
    | 'False' 

complex_number:
    | signed_real_number '+' imaginary_number 
    | signed_real_number '-' imaginary_number  

signed_number:
    | NUMBER
    | '-' NUMBER 

signed_real_number:
    | real_number
    | '-' real_number 

real_number:
    | NUMBER 

imaginary_number:
    | NUMBER 

capture_pattern:
    | pattern_capture_target 

pattern_capture_target:
    | !"_" NAME !('.' | '(' | '=') 

wildcard_pattern:
    | "_" 

value_pattern:
    | attr !('.' | '(' | '=') 

attr:
    | name_or_attr '.' NAME 

name_or_attr:
    | attr
    | NAME

group_pattern:
    | '(' pattern ')' 

sequence_pattern:
    | '[' maybe_sequence_pattern? ']' 
    | '(' open_sequence_pattern? ')' 

open_sequence_pattern:
    | maybe_star_pattern ',' maybe_sequence_pattern? 

maybe_sequence_pattern:
    | ','.maybe_star_pattern+ ','? 

maybe_star_pattern:
    | star_pattern
    | pattern

star_pattern:
    | '*' pattern_capture_target 
    | '*' wildcard_pattern 

mapping_pattern:
    | '{' '}' 
    | '{' double_star_pattern ','? '}' 
    | '{' items_pattern ',' double_star_pattern ','? '}' 
    | '{' items_pattern ','? '}' 

items_pattern:
    | ','.key_value_pattern+

key_value_pattern:
    | (literal_expr | attr) ':' pattern 

double_star_pattern:
    | '**' pattern_capture_target 

class_pattern:
    | name_or_attr '(' ')' 
    | name_or_attr '(' positional_patterns ','? ')' 
    | name_or_attr '(' keyword_patterns ','? ')' 
    | name_or_attr '(' positional_patterns ',' keyword_patterns ','? ')' 

positional_patterns:
    | ','.pattern+ 

keyword_patterns:
    | ','.keyword_pattern+

keyword_pattern:
    | NAME '=' pattern 

# Type statement
# ---------------

type_alias:
    | "type" NAME [type_params] '=' expression 

# Type parameter declaration
# --------------------------

type_params: 
    | invalid_type_params
    | '[' type_param_seq ']' 

type_param_seq: ','.type_param+ [','] 

type_param:
    | NAME [type_param_bound] [type_param_default] 
    | '*' NAME [type_param_starred_default] 
    | '**' NAME [type_param_default] 

type_param_bound: ':' expression 
type_param_default: '=' expression 
type_param_starred_default: '=' star_expression 

# EXPRESSIONS
# -----------

expressions:
    | expression (',' expression )+ [','] 
    | expression ',' 
    | expression

expression:
    | disjunction 'if' disjunction 'else' expression 
    | disjunction
    | lambdef

yield_expr:
    | 'yield' 'from' expression 
    | 'yield' [star_expressions] 

star_expressions:
    | star_expression (',' star_expression )+ [','] 
    | star_expression ',' 
    | star_expression

star_expression:
    | '*' bitwise_or 
    | expression

star_named_expressions: ','.star_named_expression+ [','] 

star_named_expression:
    | '*' bitwise_or 
    | named_expression

assignment_expression:
    | NAME ':=' ~ expression 

named_expression:
    | assignment_expression
    | expression !':='

disjunction:
    | conjunction ('or' conjunction )+ 
    | conjunction

conjunction:
    | inversion ('and' inversion )+ 
    | inversion

inversion:
    | 'not' inversion 
    | comparison

# Comparison operators
# --------------------

comparison:
    | bitwise_or compare_op_bitwise_or_pair+ 
    | bitwise_or

compare_op_bitwise_or_pair:
    | eq_bitwise_or
    | noteq_bitwise_or
    | lte_bitwise_or
    | lt_bitwise_or
    | gte_bitwise_or
    | gt_bitwise_or
    | notin_bitwise_or
    | in_bitwise_or
    | isnot_bitwise_or
    | is_bitwise_or

eq_bitwise_or: '==' bitwise_or 
noteq_bitwise_or:
    | ('!=' ) bitwise_or 
lte_bitwise_or: '<=' bitwise_or 
lt_bitwise_or: '<' bitwise_or 
gte_bitwise_or: '>=' bitwise_or 
gt_bitwise_or: '>' bitwise_or 
notin_bitwise_or: 'not' 'in' bitwise_or 
in_bitwise_or: 'in' bitwise_or 
isnot_bitwise_or: 'is' 'not' bitwise_or 
is_bitwise_or: 'is' bitwise_or 

# Bitwise operators
# -----------------

bitwise_or:
    | bitwise_or '|' bitwise_xor 
    | bitwise_xor

bitwise_xor:
    | bitwise_xor '^' bitwise_and 
    | bitwise_and

bitwise_and:
    | bitwise_and '&' shift_expr 
    | shift_expr

shift_expr:
    | shift_expr '<<' sum 
    | shift_expr '>>' sum 
    | sum

# Arithmetic operators
# --------------------

sum:
    | sum '+' term 
    | sum '-' term 
    | term

term:
    | term '*' factor 
    | term '/' factor 
    | term '//' factor 
    | term '%' factor 
    | term '@' factor 
    | factor

factor:
    | '+' factor 
    | '-' factor 
    | '~' factor 
    | power

power:
    | await_primary '**' factor 
    | await_primary

# Primary elements
# ----------------

# Primary elements are things like "obj.something.something", "obj[something]", "obj(something)", "obj" ...

await_primary:
    | 'await' primary 
    | primary

primary:
    | primary '.' NAME 
    | primary genexp 
    | primary '(' [arguments] ')' 
    | primary '[' slices ']' 
    | atom

slices:
    | slice !',' 
    | ','.(slice | starred_expression)+ [','] 

slice:
    | [expression] ':' [expression] [':' [expression] ] 
    | named_expression 

atom:
    | NAME
    | 'True' 
    | 'False' 
    | 'None' 
    | strings
    | NUMBER
    | (tuple | group | genexp)
    | (list | listcomp)
    | (dict | set | dictcomp | setcomp)
    | '...' 

group:
    | '(' (yield_expr | named_expression) ')' 

# Lambda functions
# ----------------

lambdef:
    | 'lambda' [lambda_params] ':' expression 

lambda_params:
    | lambda_parameters

# lambda_parameters etc. duplicates parameters but without annotations
# or type comments, and if there's no comma after a parameter, we expect
# a colon, not a close parenthesis.  (For more, see parameters above.)
#
lambda_parameters:
    | lambda_slash_no_default lambda_param_no_default* lambda_param_with_default* [lambda_star_etc] 
    | lambda_slash_with_default lambda_param_with_default* [lambda_star_etc] 
    | lambda_param_no_default+ lambda_param_with_default* [lambda_star_etc] 
    | lambda_param_with_default+ [lambda_star_etc] 
    | lambda_star_etc 

lambda_slash_no_default:
    | lambda_param_no_default+ '/' ',' 
    | lambda_param_no_default+ '/' &':' 

lambda_slash_with_default:
    | lambda_param_no_default* lambda_param_with_default+ '/' ',' 
    | lambda_param_no_default* lambda_param_with_default+ '/' &':' 

lambda_star_etc:
    | '*' lambda_param_no_default lambda_param_maybe_default* [lambda_kwds] 
    | '*' ',' lambda_param_maybe_default+ [lambda_kwds] 
    | lambda_kwds 

lambda_kwds:
    | '**' lambda_param_no_default 

lambda_param_no_default:
    | lambda_param ',' 
    | lambda_param &':' 
lambda_param_with_default:
    | lambda_param default ',' 
    | lambda_param default &':' 
lambda_param_maybe_default:
    | lambda_param default? ',' 
    | lambda_param default? &':' 
lambda_param: NAME 

# LITERALS
# ========

fstring_middle:
    | fstring_replacement_field
    | FSTRING_MIDDLE 
fstring_replacement_field:
    | '{' annotated_rhs '='? [fstring_conversion] [fstring_full_format_spec] '}' 
fstring_conversion:
    | "!" NAME 
fstring_full_format_spec:
    | ':' fstring_format_spec* 
fstring_format_spec:
    | FSTRING_MIDDLE 
    | fstring_replacement_field
fstring:
    | FSTRING_START fstring_middle* FSTRING_END 

string: STRING 
strings: (fstring|string)+ 

list:
    | '[' [star_named_expressions] ']' 

tuple:
    | '(' [star_named_expression ',' [star_named_expressions]  ] ')' 

set: '{' star_named_expressions '}' 

# Dicts
# -----

dict:
    | '{' [double_starred_kvpairs] '}' 

double_starred_kvpairs: ','.double_starred_kvpair+ [','] 

double_starred_kvpair:
    | '**' bitwise_or 
    | kvpair

kvpair: expression ':' expression 

# Comprehensions & Generators
# ---------------------------

for_if_clauses:
    | for_if_clause+ 

for_if_clause:
    | 'async' 'for' star_targets 'in' ~ disjunction ('if' disjunction )* 
    | 'for' star_targets 'in' ~ disjunction ('if' disjunction )* 

listcomp:
    | '[' named_expression for_if_clauses ']' 

setcomp:
    | '{' named_expression for_if_clauses '}' 

genexp:
    | '(' ( assignment_expression | expression !':=') for_if_clauses ')' 

dictcomp:
    | '{' kvpair for_if_clauses '}' 

# FUNCTION CALL ARGUMENTS
# =======================

arguments:
    | args [','] &')' 

args:
    | ','.(starred_expression | ( assignment_expression | expression !':=') !'=')+ [',' kwargs ] 
    | kwargs 

kwargs:
    | ','.kwarg_or_starred+ ',' ','.kwarg_or_double_starred+ 
    | ','.kwarg_or_starred+
    | ','.kwarg_or_double_starred+

starred_expression:
    | '*' expression 

kwarg_or_starred:
    | NAME '=' expression 
    | starred_expression 

kwarg_or_double_starred:
    | NAME '=' expression 
    | '**' expression 

# ASSIGNMENT TARGETS
# ==================

# Generic targets
# ---------------

# NOTE: star_targets may contain *bitwise_or, targets may not.
star_targets:
    | star_target !',' 
    | star_target (',' star_target )* [','] 

star_targets_list_seq: ','.star_target+ [','] 

star_targets_tuple_seq:
    | star_target (',' star_target )+ [','] 
    | star_target ',' 

star_target:
    | '*' (!'*' star_target) 
    | target_with_star_atom

target_with_star_atom:
    | t_primary '.' NAME !t_lookahead 
    | t_primary '[' slices ']' !t_lookahead 
    | star_atom

star_atom:
    | NAME 
    | '(' target_with_star_atom ')' 
    | '(' [star_targets_tuple_seq] ')' 
    | '[' [star_targets_list_seq] ']' 

single_target:
    | single_subscript_attribute_target
    | NAME 
    | '(' single_target ')' 

single_subscript_attribute_target:
    | t_primary '.' NAME !t_lookahead 
    | t_primary '[' slices ']' !t_lookahead 

t_primary:
    | t_primary '.' NAME &t_lookahead 
    | t_primary '[' slices ']' &t_lookahead 
    | t_primary genexp &t_lookahead 
    | t_primary '(' [arguments] ')' &t_lookahead 
    | atom &t_lookahead 

t_lookahead: '(' | '[' | '.'

# Targets for del statements
# --------------------------

del_targets: ','.del_target+ [','] 

del_target:
    | t_primary '.' NAME !t_lookahead 
    | t_primary '[' slices ']' !t_lookahead 
    | del_t_atom

del_t_atom:
    | NAME 
    | '(' del_target ')' 
    | '(' [del_targets] ')' 
    | '[' [del_targets] ']' 

# TYPING ELEMENTS
# ---------------

# type_expressions allow */** but ignore them
type_expressions:
    | ','.expression+ ',' '*' expression ',' '**' expression 
    | ','.expression+ ',' '*' expression 
    | ','.expression+ ',' '**' expression 
    | '*' expression ',' '**' expression 
    | '*' expression 
    | '**' expression 
    | ','.expression+ 

func_type_comment:
    | NEWLINE TYPE_COMMENT &(NEWLINE INDENT)   # Must be followed by indented block
    | TYPE_COMMENT