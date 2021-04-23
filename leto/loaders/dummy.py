import random
from ..loaders import Loader


class DummyLoader(Loader):
    def __init__(self, n_tuples: int) -> None:
        self.n_tuples = n_tuples

    def load(self):
        for _ in range(self.n_tuples):
            yield (
                f"X_{random.randint(0, 10)}",
                f"r_{random.randint(0,  10)}",
                f"Y_{random.randint(0, 10)}",
            )
