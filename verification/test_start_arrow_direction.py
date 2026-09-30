"""The selected start arrow follows the first profile cut in either milling mode."""
import unittest

import cfrp_router_cam as cam


class StartArrowDirectionTests(unittest.TestCase):
    def test_outer_and_inner_reverse_with_climb_switch(self):
        square = [(0., 0.), (40., 0.), (40., 20.), (0., 20.)]
        for role in ("outer", "inner"):
            contour = cam.Contour(square, role=role, start_s=10.)
            for climb in (True, False):
                direction = cam.start_cut_direction(contour, climb)
                expected_x = -1. if (role == "outer") == climb else 1.
                self.assertAlmostEqual(direction[0], expected_x)
                self.assertAlmostEqual(direction[1], 0.)

    def test_vertex_uses_outgoing_edge_and_reversed_source(self):
        for points in ([(0., 0.), (40., 0.), (40., 20.), (0., 20.)],
                       [(0., 0.), (0., 20.), (40., 20.), (40., 0.)]):
            contour = cam.Contour(points, role="outer")
            contour.start_s = cam.nearest_path_distance(points, (40., 0.), True)[1]
            direction = cam.start_cut_direction(contour, True)
            self.assertAlmostEqual(direction[0], -1.)
            self.assertAlmostEqual(direction[1], 0.)

    def test_pocket_has_no_profile_cut_direction(self):
        contour = cam.Contour([(0., 0.), (10., 0.), (10., 10.), (0., 10.)],
                              start_s=5., operation="pocket")
        self.assertIsNone(cam.start_cut_direction(contour, True))


if __name__ == "__main__":
    unittest.main()
