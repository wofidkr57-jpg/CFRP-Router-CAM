"""Spacing of hand-placed mixed-size parts, without changing their geometry."""
import unittest

from cfrp_router_cam import even_box_spacing


class EvenBoxSpacingTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b, self.c = (1, 1), (2, 1), (3, 1)
        self.bounds = {
            self.a: (0.0, 0.0, 10.0, 10.0),
            self.b: (16.0, 0.0, 26.0, 10.0),
            self.c: (0.0, 17.0, 6.0, 27.0),
        }

    def test_tightens_rows_and_columns_with_default_gap(self):
        shifts = even_box_spacing(self.bounds, 2.0, (30.0, 30.0))
        self.assertEqual(shifts[self.a], (0.0, 0.0))
        self.assertEqual(shifts[self.b], (-4.0, 0.0))
        self.assertEqual(shifts[self.c], (0.0, -5.0))
        self.assertEqual(self.bounds[self.b], (16.0, 0.0, 26.0, 10.0))

    def test_uses_sum_of_each_part_clearance(self):
        clearances = {self.a: 1.5, self.b: 2.5, self.c: 1.0}
        shifts = even_box_spacing(self.bounds, 2.0, (30.0, 30.0), 0, clearances)
        self.assertEqual(shifts[self.b], (-2.0, 0.0))
        self.assertEqual(shifts[self.c], (0.0, -4.5))

    def test_rejects_infeasible_sheet_without_mutating_input(self):
        original = self.bounds.copy()
        with self.assertRaises(ValueError):
            even_box_spacing(self.bounds, 2.0, (18.0, 30.0))
        self.assertEqual(self.bounds, original)


if __name__ == "__main__":
    unittest.main()
