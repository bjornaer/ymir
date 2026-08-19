import cProfile
import timeit

from ymir.core.lexer import Lexer
from ymir.core.parser import Parser
from ymir.interpreter import YmirInterpreter


def benchmark_interpreter(source_code):
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    interpreter = YmirInterpreter()

    def run():
        interpreter.execute(ast)

    cProfile.runctx("run()", globals(), locals())
    print(timeit.timeit(run, number=100))


source_code = """
class Model {
    def train(data: int, labels: int) -> int {
        return 0
    }
}

def train_model(data: int, labels: int) -> int {
    model = Model()
    model.train(data, labels)
    return model
}

x = 5 + 3
arr = [1, 2, 3]
str = "hello"
"""

benchmark_interpreter(source_code)
