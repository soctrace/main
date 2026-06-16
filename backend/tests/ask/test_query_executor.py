import unittest

from app.ask.sql.query_executor import QueryExecutor


class FailingSession:
    def __init__(self):
        self.calls = 0
        self.rolled_back = False

    def execute(self, _statement):
        self.calls += 1
        if self.calls == 1:
            return None
        raise RuntimeError("missing column")

    def rollback(self):
        self.rolled_back = True


class QueryExecutorTest(unittest.TestCase):
    def test_execute_rolls_back_after_sql_error(self):
        session = FailingSession()
        executor = QueryExecutor(session)

        with self.assertRaises(RuntimeError):
            executor.execute("SELECT total_population FROM marts.ask_population_profile")

        self.assertTrue(session.rolled_back)


if __name__ == "__main__":
    unittest.main()
