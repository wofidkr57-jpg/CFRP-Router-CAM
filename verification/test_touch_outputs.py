"""Offline output-selection regressions; no Mach3 or physical outputs are used."""
import copy
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
from test_tool_replacement import cfg as replacement_config, lines


def settings(mode="legacy",**changes):
    result=replacement_config()
    result.update(touch_aux=mode,touch_aux_reviewed=True,
                  touch_coolant_on="M8",touch_coolant_off="M9",
                  touch_dust_on="M901",touch_dust_off="M902")
    result.update(changes)
    return result


def commands(code):
    return [value for line in code.splitlines()
            if (value:=re.sub(r"\([^)]*\)","",line).split(";",1)[0].strip())]


def mcodes(code):
    return [int(n) for line in commands(code) for n in re.findall(r"M(\d+)(?![\d.])",line,re.I)]


class TouchOutputTests(unittest.TestCase):
    def test_legacy_is_unchanged_and_retains_original_change_sequence(self):
        for enabled in (False,True):
            raw=settings(m8_enabled=enabled,start_code="G21 G90 G17 G54\nM7\nS{RPM} M3")
            before=copy.deepcopy(raw)
            applied=cam.apply_touch_machine_options(raw)
            self.assertEqual(raw,before)
            self.assertEqual(applied,raw)
            code=cam.generate_gcode(lines(),applied)
            self.assertEqual(code,cam.generate_gcode(lines(),raw))
            self.assertEqual(code.count("G90 G0 Z11\nM5\nM9\nM881"),2)
            restart="G90 G53 G0 Z-70\n"+("M8\n" if enabled else "")+"S18000 M3\nG4 P3"
            self.assertEqual(code.count(restart),2)

    def test_none_removes_known_outputs_even_at_tool_changes(self):
        raw=settings("none",start_code="G21\nM7 M08 M901\nM880\nS{RPM} M3",
                     end_code="M902\nM9\nM5\nM30")
        applied=cam.apply_touch_machine_options(raw)
        code=cam.generate_gcode(lines(),applied)
        self.assertTrue({7,8,9,901,902}.isdisjoint(mcodes(code)))
        self.assertEqual(mcodes(code).count(881),2)
        self.assertEqual(mcodes(code).count(880),1)
        self.assertEqual(code.count("G90 G0 Z11\nM5\nM881"),2)
        self.assertEqual(code.count("G90 G53 G0 Z-70\nS18000 M3"),2)
        self.assertFalse(applied["m8_enabled"])

    def test_dust_restarts_registered_output_after_each_change(self):
        raw=settings("dust",start_code="G21\nM7\nM901\nS{RPM} M3",
                     end_code="M9\nM902\nM5\nM30")
        code=cam.generate_gcode(lines(),cam.apply_touch_machine_options(raw))
        self.assertTrue({7,8,9}.isdisjoint(mcodes(code)))
        self.assertEqual(mcodes(code).count(901),3)
        self.assertEqual(mcodes(code).count(902),3)
        self.assertEqual(code.count("G90 G0 Z11\nM5\nM902\nM881"),2)
        self.assertEqual(code.count("G90 G53 G0 Z-70\nM901\nS18000 M3"),2)
        self.assertIn("M902\nM30",code)

    def test_coolant_uses_registered_commands_through_tool_changes(self):
        raw=settings("coolant",touch_coolant_on="M7\nM123",touch_coolant_off="M124",
                     start_code="G21\nM901\nM08\nS{RPM} M3",end_code="M9\nM902\nM30")
        code=cam.generate_gcode(lines(),cam.apply_touch_machine_options(raw))
        self.assertTrue({8,9,901,902}.isdisjoint(mcodes(code)))
        for number in (7,123,124):self.assertEqual(mcodes(code).count(number),3)
        self.assertEqual(code.count("G90 G53 G0 Z-70\nM7\nM123\nS18000 M3"),2)
        self.assertEqual(code.count("M5\nM124\nM881"),2)

    def test_split_programs_retain_same_output_mapping(self):
        contours=[cam.Contour([(i*400.,0.),(i*400.+250.,0.),
                              (i*400.+250.,250.),(i*400.,250.)],role="outer") for i in range(3)]
        raw=settings("dust",onion_split=True,onion_split_percent=10.,tool_change_limit_m=1.1,
                     onion_start_code="G21\nM7\nM901\nS{RPM} M3",onion_end_code="M9\nM902\nM30")
        for label,cfg in cam.machining_jobs(contours,cam.apply_touch_machine_options(raw)):
            with self.subTest(label=label):
                code=cam.generate_gcode(contours,cfg)
                self.assertTrue({7,8,9}.isdisjoint(mcodes(code)))
                self.assertEqual(mcodes(code).count(881),2)
                self.assertEqual(mcodes(code).count(901),3)
                self.assertEqual(mcodes(code).count(902),3)

    def test_comments_and_unknown_macros_are_preserved_not_treated_as_outputs(self):
        raw=settings("dust",start_code="(M3 M8 M901)\n; M3\nM700\nM880\nS{RPM} M3",
                     end_code="(M30 M9 M902)\nM701\nM5\nM30")
        applied=cam.apply_touch_machine_options(raw)
        self.assertEqual(commands(applied["start_code"]),["M700","M880","M901","S{RPM} M3"])
        self.assertEqual(commands(applied["end_code"]),["M701","M5","M902","M30"])
        self.assertIn("(M3 M8 M901)",applied["start_code"])
        self.assertIn("(M30 M9 M902)",applied["end_code"])

    def test_none_does_not_activate_default_spindle_from_emptied_template(self):
        raw=settings("none",tool_change_enabled=False,start_code="M8",end_code="M9")
        code=cam.generate_gcode(lines(1),cam.apply_touch_machine_options(raw))
        self.assertEqual(mcodes(code),[])

    def test_selected_output_requires_review_and_explicit_valid_commands(self):
        for changes in ({"touch_aux_reviewed":False},{"touch_dust_on":""},
                        {"touch_dust_off":""},{"touch_dust_on":"M901\nG0 X0"}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                cam.apply_touch_machine_options(settings("dust",**changes))

    def test_reapplying_output_mapping_does_not_duplicate_commands(self):
        first=cam.apply_touch_machine_options(settings("dust"))
        second=cam.apply_touch_machine_options(first)
        self.assertEqual(first,second)

    def test_current_origin_replaces_numbered_m880_preserving_comments(self):
        raw=settings(touch_xy_mode="current",touch_origin_x=123.25,touch_origin_y=-40.,
                     start_code="%\nO0001\nG21 G90 G54\nN10 (fixed datum M880) M0880 ; setup\nS{RPM} M3")
        applied=cam.apply_touch_machine_options(raw)
        self.assertIn("G21 G90 G54\nN10 (fixed datum M880) G10 L2 P1 X123.25 Y-40 ; setup",applied["start_code"])
        self.assertNotIn(880,mcodes(applied["start_code"]))
        self.assertEqual(cam.apply_touch_machine_options(applied),applied)
        # Machine-coordinate XY is written as the same absolute G54 offset on
        # every execution, never added to the previous work offset.
        code=cam.generate_gcode(lines(),applied)
        self.assertEqual(code.count("G10 L2 P1 X123.25 Y-40"),1)
        self.assertEqual(mcodes(code).count(881),2)

    def test_current_origin_without_macro_inserts_after_program_header(self):
        raw=settings(touch_xy_mode="current",touch_origin_x=10.,touch_origin_y=20.,
                     start_code="%\nO0001 (part)\n; start\n(M880 G10) G0 Z{SAFE_Z}\nS{RPM} M3")
        applied=cam.apply_touch_machine_options(raw)
        executable=commands(applied["start_code"])
        self.assertEqual(executable[:5],["%","O0001","G21 G90 G54","G10 L2 P1 X10 Y20","G0 Z{SAFE_Z}"])
        self.assertEqual(cam.apply_touch_machine_options(applied),applied)

    def test_current_origin_rejects_conflicting_offsets_modes_or_combined_macro(self):
        for conflict in ("N10 G52X10","G92 X10","G92.3","G68 X0 Y0 R10",
                         "G10L2P1X1Y2","G20","G91","G55","G59.3","G54.1",
                         "N10 M880 G0 X0","M880 M3"):
            raw=settings(touch_xy_mode="current",touch_origin_x=10.,touch_origin_y=20.,
                         start_code="G21 G90 G54\n"+conflict+"\nS{RPM} M3")
            with self.subTest(conflict=conflict),self.assertRaises(ValueError):
                cam.apply_touch_machine_options(raw)
            raw["touch_xy_mode"]="fixture"
            self.assertEqual(cam.apply_touch_machine_options(raw),raw)

    def test_current_origin_allows_clear_commands_and_ignores_commented_conflicts(self):
        raw=settings(touch_xy_mode="current",touch_origin_x=10.,touch_origin_y=20.,
                     start_code="(G52 G92 G68 G20 G91 G55)\nG21 G90 G54\nG92.1\nG92.2\nG69\nG91.1\nM880\n; G10 L2 P1 X9")
        applied=cam.apply_touch_machine_options(raw)
        for command in ("G92.1","G92.2","G69","G91.1"):
            self.assertIn(command,commands(applied["start_code"]))
        self.assertIn("G10 L2 P1 X10 Y20",commands(applied["start_code"]))

    def test_current_origin_applies_to_both_split_templates(self):
        raw=settings("dust",touch_xy_mode="current",touch_origin_x=10.,touch_origin_y=20.,
                     onion_split=True,start_code="G21\nN10 M880\nS{RPM} M3",
                     onion_start_code="G21\nN20 M880 (finish)\nS{RPM} M3")
        applied=cam.apply_touch_machine_options(raw)
        for key in ("start_code","onion_start_code"):
            self.assertEqual(applied[key].count("G10 L2 P1 X10 Y20"),1)
            self.assertNotIn(880,mcodes(applied[key]))
            self.assertEqual(mcodes(applied[key]).count(901),1)
        self.assertEqual(cam.apply_touch_machine_options(applied),applied)


if __name__=="__main__":unittest.main()
