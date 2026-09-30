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

    def test_spreads_rows_and_columns_across_sheet(self):
        shifts = even_box_spacing(self.bounds, 2.0, (30.0, 30.0))
        self.assertAlmostEqual(shifts[self.a][0], 1.0, places=5)
        self.assertAlmostEqual(shifts[self.a][1], 1.0, places=5)
        self.assertAlmostEqual(shifts[self.b][0], 3.0, places=5)
        self.assertAlmostEqual(shifts[self.c][0], 3.0, places=5)
        self.assertAlmostEqual(shifts[self.c][1], 2.0, places=5)
        self.assertEqual(self.bounds[self.b], (16.0, 0.0, 26.0, 10.0))

    def test_equal_gap_for_a_row_of_mixed_widths(self):
        a, b, c = self.a, self.b, self.c
        boxes = {a: (0, 0, 10, 8), b: (15, 0, 20, 8), c: (25, 0, 32, 8)}
        shifts = even_box_spacing(boxes, 2.0, (50, 20))
        placed = {key: (box[0]+shifts[key][0], box[2]+shifts[key][0])
                  for key, box in boxes.items()}
        self.assertAlmostEqual(placed[b][0]-placed[a][1], placed[c][0]-placed[b][1], places=5)
        self.assertGreater(placed[b][0]-placed[a][1], 2.0)
        self.assertAlmostEqual(placed[a][0], 1.0, places=5)
        self.assertAlmostEqual(placed[c][1], 49.0, places=5)

    def test_uses_each_part_clearance_at_borders_and_between_boxes(self):
        clearances = {self.a: 1.5, self.b: 2.5, self.c: 1.0}
        shifts = even_box_spacing(self.bounds, 2.0, (30.0, 30.0), 0, clearances)
        ax = self.bounds[self.a][0]+shifts[self.a][0]
        ar = self.bounds[self.a][2]+shifts[self.a][0]
        bx = self.bounds[self.b][0]+shifts[self.b][0]
        br = self.bounds[self.b][2]+shifts[self.b][0]
        self.assertGreaterEqual(ax+1e-5, clearances[self.a])
        self.assertGreaterEqual(bx-ar+1e-5, clearances[self.a]+clearances[self.b])
        self.assertGreaterEqual(30-br+1e-5, clearances[self.b])

    def test_custom_clearance_can_make_sheet_infeasible(self):
        clearances = {self.a: 1.5, self.b: 2.5, self.c: 1.0}
        with self.assertRaises(ValueError):
            even_box_spacing(self.bounds, 2.0, (24.0, 30.0), 0, clearances)

    def test_second_spacing_does_not_move_parts_again(self):
        shifts = even_box_spacing(self.bounds, 2.0, (30.0, 30.0))
        placed = {key: (box[0]+shifts[key][0], box[1]+shifts[key][1],
                        box[2]+shifts[key][0], box[3]+shifts[key][1])
                  for key, box in self.bounds.items()}
        second = even_box_spacing(placed, 2.0, (30.0, 30.0))
        self.assertTrue(all(abs(dx)<1e-6 and abs(dy)<1e-6 for dx, dy in second.values()))

    def test_diagonal_order_is_preserved(self):
        boxes = {self.a: (2, 2, 7, 7), self.b: (15, 15, 21, 21)}
        shifts = even_box_spacing(boxes, 2.0, (30.0, 30.0))
        a = boxes[self.a];b = boxes[self.b]
        self.assertLess(a[2]+shifts[self.a][0], b[0]+shifts[self.b][0])
        self.assertLess(a[3]+shifts[self.a][1], b[1]+shifts[self.b][1])

    def test_rejects_infeasible_sheet_without_mutating_input(self):
        original = self.bounds.copy()
        with self.assertRaises(ValueError):
            even_box_spacing(self.bounds, 2.0, (18.0, 30.0))
        self.assertEqual(self.bounds, original)

    def test_rejects_originally_overlapping_boxes(self):
        bounds = {self.a: (0, 0, 10, 10), self.b: (5, 5, 15, 15)}
        with self.assertRaisesRegex(ValueError, "겹친 외곽 박스"):
            even_box_spacing(bounds, 2.0, (30.0, 30.0))


if __name__ == "__main__":
    unittest.main()
