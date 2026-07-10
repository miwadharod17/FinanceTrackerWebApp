import unittest

from sqlalchemy import inspect

import database
import models


class DatabaseIndexesTest(unittest.TestCase):
    def test_important_indexes_exist(self):
        database.Base.metadata.create_all(bind=database.engine)
        inspector = inspect(database.engine)

        transaction_indexes = {idx["name"] for idx in inspector.get_indexes("transactions")}
        planned_expense_indexes = {idx["name"] for idx in inspector.get_indexes("planned_expenses")}
        mutual_fund_indexes = {idx["name"] for idx in inspector.get_indexes("mutual_funds")}

        self.assertIn("ix_transactions_user_id_date", transaction_indexes)
        self.assertIn("ix_planned_expenses_user_id_due_date_status", planned_expense_indexes)
        self.assertIn("ix_mutual_funds_category_risk_level", mutual_fund_indexes)


if __name__ == "__main__":
    unittest.main()
