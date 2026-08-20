# 09 — Grammar

Consolidated EBNF. Where this and a prose chapter disagree, **the prose chapter is
normative** and the grammar is the defect.

Notation: `{ x }` zero or more, `[ x ]` optional, `|` alternation, `"x"` literal.

```ebnf
SourceFile   = ModuleDecl { ImportDecl } { TopDecl } .
ModuleDecl   = "module" QualifiedIdent .
ImportDecl   = "import" QualifiedIdent [ "as" ident ] .
QualifiedIdent = ident { "." ident } .

TopDecl      = [ "export" ] ( FuncDecl | GateDecl | StructDecl | EnumDecl
                            | ConstDecl | VarDecl | MethodDecl ) .

(* --- declarations --- *)

FuncDecl     = "func" ident Signature Block .
MethodDecl   = "func" "(" Receiver ")" ident Signature Block .
GateDecl     = "gate" ident "(" [ ParamList ] ")" Block .
Receiver     = ident ":" [ "mut" ] TypeName .
Signature    = "(" [ ParamList ] ")" [ "->" ResultType ] .
ParamList    = Param { "," Param } [ "," ] .
Param        = ident ":" [ "mut" ] Type .
ResultType   = Type | "(" Type { "," Type } ")" .

StructDecl   = "struct" ident "{" { FieldDecl } "}" .
FieldDecl    = ident ":" Type "," .

EnumDecl     = "enum" ident "{" { VariantDecl } "}" .
VariantDecl  = ident [ "(" Type { "," Type } ")" ] "," .

ConstDecl    = "const" ident ":" Type "=" Expr .
VarDecl      = "var" ident ( ":" Type [ "=" Expr ] | ":=" Expr ) .

(* --- types --- *)

Type         = UnionType .
UnionType    = BaseType { "|" BaseType } .        (* members must all be enum types *)
BaseType     = "?" ( BaseType | "(" Type ")" )    (* nullable; ?A|B not accepted *)
             | TypeName
             | "array" "[" Type "]"
             | "map" "[" Type "," Type "]"
             | "tuple" "[" Type { "," Type } "]"
             | "matrix" "[" Type "]"
             | "chan" "[" Type "]"
             | "qreg" "[" IntLit "]"
             | FuncType .
TypeName     = ident | QualifiedIdent .
FuncType     = "func" "(" [ Type { "," Type } ] ")" [ "->" ResultType ] .

(* --- statements --- *)

Block        = "{" { Stmt } "}" .
Stmt         = VarDecl | ShortVarDecl | Assignment | IncDecStmt
             | IfStmt | WhileStmt | ForStmt | MatchStmt | SelectStmt
             | SpawnStmt | ReturnStmt | BreakStmt | ContinueStmt
             | SendStmt | ExprStmt | Block .

ShortVarDecl = IdentList ":=" ExprList .
IdentList    = ident { "," ident } .
ExprList     = Expr { "," Expr } .
Assignment   = TargetList AssignOp ExprList .
TargetList   = Target { "," Target } .
Target       = ident | IndexExpr | SelectorExpr | "_" .
AssignOp     = "=" | "+=" | "-=" | "*=" | "/=" | "%=" | "**=" .
IncDecStmt   = Target ( "++" | "--" ) .

IfStmt       = "if" Expr Block [ "else" ( IfStmt | Block ) ] .
WhileStmt    = "while" Expr Block .
ForStmt      = "for" ( RangeClause | CStyleClause ) Block .
RangeClause  = IdentList "in" Expr .
CStyleClause = [ SimpleStmt ] ";" [ Expr ] ";" [ SimpleStmt ] .
SimpleStmt   = ShortVarDecl | Assignment | IncDecStmt | ExprStmt .

MatchStmt    = "match" Expr "{" { MatchArm } "}" .
MatchArm     = Pattern "=>" ( Stmt "," | Block ) .
Pattern      = "_" | "nil"
             | [ ident "." ] ident [ "(" PatternElem { "," PatternElem } ")" ] .
PatternElem  = ident | "_" .

SelectStmt   = "select" "{" { SelectCase } "}" .
SelectCase   = "case" ( RecvStmt | SendStmt ) ":" { Stmt }
             | "case" "default" ":" { Stmt } .
RecvStmt     = [ IdentList ( ":=" | "=" ) ] "<-" Expr .
SendStmt     = Expr "<-" Expr .

SpawnStmt    = "spawn" CallExpr .
ReturnStmt   = "return" [ ExprList ] .
BreakStmt    = "break" .
ContinueStmt = "continue" .
ExprStmt     = CallExpr .

(* --- expressions, loosest to tightest --- *)

Expr         = OrExpr .
OrExpr       = AndExpr { "||" AndExpr } .
AndExpr      = EqExpr { "&&" EqExpr } .
EqExpr       = RelExpr { ( "==" | "!=" ) RelExpr } .
RelExpr      = AddExpr { ( "<" | "<=" | ">" | ">=" ) AddExpr } .
AddExpr      = MulExpr { ( "+" | "-" ) MulExpr } .
MulExpr      = PowExpr { ( "*" | "/" | "%" | "@" ) PowExpr } .
PowExpr      = UnaryExpr [ "**" PowExpr ] .            (* right-associative *)
UnaryExpr    = [ "-" | "!" | "<-" ] PostfixExpr
             | TryExpr .
TryExpr      = "try" PostfixExpr .                (* operand must be a call *)
PostfixExpr  = PrimaryExpr { CallSuffix | IndexSuffix | SelectorSuffix } .
CallSuffix   = "(" [ ExprList [ "," ] ] ")" .
IndexSuffix  = "[" Expr "]" .
SelectorSuffix = "." ( ident | IntLit ) .

PrimaryExpr  = Literal | ident | "(" Expr ")" | CompositeLit | FuncLit .
CompositeLit = ArrayLit | MapLit | TupleLit | StructLit .
ArrayLit     = "[" [ ExprList [ "," ] ] "]" .
MapLit       = "{" [ KeyVal { "," KeyVal } [ "," ] ] "}" .
KeyVal       = Expr ":" Expr .
TupleLit     = "(" Expr "," [ ExprList ] [ "," ] ")" .
StructLit    = TypeName "{" [ FieldInit { "," FieldInit } [ "," ] ] "}" .
FieldInit    = ident ":" Expr .
FuncLit      = "func" Signature Block .

CallExpr     = PostfixExpr CallSuffix .
IndexExpr    = PostfixExpr IndexSuffix .
SelectorExpr = PostfixExpr SelectorSuffix .

Literal      = IntLit | FloatLit | ComplexLit | StringLit | "true" | "false" | "nil" .
```

## Known ambiguities

1. **`{` after an `if`/`while`/`for` header.** A map literal and a block both start
   with `{`. Resolved as in Go: a composite literal **MUST NOT** appear unparenthesized
   at the top level of a control-flow header. Write `if (m == map[string,int]{})`.

2. **`TupleLit` vs. parenthesized expression.** `(x)` is parenthesization; `(x,)` and
   `(x, y)` are tuples. The trailing comma in a one-element tuple is required.

3. **`<-` in `UnaryExpr` and `SendStmt`.** `a <- b` at statement level is a send;
   `<-a` in expression position is a receive. Since `<-` is one token (chapter 01),
   this is resolved by position, not by lexing.

4. **`ExprStmt = CallExpr`** deliberately excludes other expressions — chapter 05
   makes a bare `x + 1` statement a compile error.

5. **`|` in `UnionType` vs. `||`.** Maximal munch (chapter 01) lexes `||` as one token,
   so a union separator is never confused with logical-or. They also never occur in the
   same position: `UnionType` appears only where a `Type` is expected.

6. **`?` takes a base type or a parenthesized type**, never a bare union: write
   `?(A | B)`, not `?A | B`. There is therefore no precedence relation between `?`
   and `|` to define.

7. **`try` binds tighter than any binary operator.** `try f() + 1` is `(try f()) + 1`.
   Its operand must be a call, so `try x` for a non-call `x` is a syntax error.
