"""Named profiles: isolated scopes, persistence, job snapshots and failed writes.

Run with the project Python; Tk is required. All settings/jobs use a temporary
directory. This generates text only and never connects to CNC hardware.
"""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam


def set_code(app,attr,text):
    widget=getattr(app,attr)
    widget.configure(state="normal");widget.delete("1.0","end");widget.insert("1.0",text)
    app.sync_onion_split()


def save_as(app,kind,name):
    with mock.patch.object(cam.simpledialog,"askstring",return_value=name):
        assert app.save_profile(kind,save_as=True)


def select(app,kind,name):
    app.profile_names[kind].set(name)
    # Exercise the actual combobox event, not only the handler.
    app.profile_combos[kind][0].event_generate("<<ComboboxSelected>>")
    app.update()
    assert app.profile_active[kind]==name


with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ,{"CFRP_CAM_LANGUAGE":"en"}):
    root=Path(tmp)
    legacy={"version":"1.43","language":"en","vars":{"feed":500.,"stock":6.,"rpm":16500.,"z_origin":"Bottom"},
            "start_code":cam.DEFAULT_START_CODE+"\n(START A)","end_code":"(END A)\n"+cam.DEFAULT_END_CODE}
    (root/"settings.json").write_text(json.dumps(legacy),encoding="utf-8")
    with mock.patch.object(cam.App,"executable_dir",return_value=tmp),mock.patch.object(cam.App,"appdata_settings_path",return_value=str(root/"settings.json")):
        app=cam.App()
        try:
            app.update()
            assert app.profile_active=={"machine":"기존 기계","setup":"기존 가공 셋업"}
            assert tuple(app.profile_combos["machine"][0]["values"])==("기존 기계",)
            app.geometry("980x700");app.update()
            for widget in app.profile_combos["machine"][0].master.winfo_children():
                assert widget.winfo_viewable() and widget.winfo_x()+widget.winfo_width()<=widget.master.winfo_width()
            assert app.vars["feed"].get()==500 and app.vars["rpm"].get()==16500
            a=app.capture_profile("machine");thick=app.capture_profile("setup")
            assert "START A" in a["codes"]["start_text"]
            set_code(app,"start_text",cam.DEFAULT_START_CODE+"\n(START B)")
            set_code(app,"end_text","(END B)\n"+cam.DEFAULT_END_CODE)
            set_code(app,"onion_start_text","(FINISH B)")
            app.vars["machine_park_x"].set(325);app.vars["tool_change_macro"].set("M882")
            app.vars["tool_change_return_z"].set(-60)
            save_as(app,"machine","Machine B")
            b=app.capture_profile("machine")
            app.vars["stock"].set(2);app.vars["feed"].set(600);app.vars["rpm"].set(22000)
            app.vars["safe_z_auto"].set(False);app.vars["safe_z"].set(15)
            app.vars["finish_scope"].set("Outer only")
            save_as(app,"setup","2T carbon")
            thin=app.capture_profile("setup")
            app.example()
            app.vars["sheet_w"].set(477);app.vars["sheet_h"].set(477)
            geometry=copy.deepcopy(app._history_state())
            select(app,"machine","기존 기계")
            assert app.capture_profile("machine")==a and app.capture_profile("setup")==thin
            select(app,"setup","기존 가공 셋업")
            assert app.capture_profile("machine")==a and app.capture_profile("setup")==thick
            app.gcode="STALE";app.gcode_parts=[("FULL","STALE")];app.gcode_signature="STALE"
            select(app,"setup","2T carbon")
            assert app.capture_profile("machine")==a and app.capture_profile("setup")==thin
            assert app.vars["safe_z"].get()==15 and not app.vars["safe_z_auto"].get()
            assert app._history_state()==geometry and app.vars["sheet_w"].get()==477
            assert not app.gcode and not app.gcode_parts and app.gcode_signature is None
            code_a=cam.generate_gcode(app.contours,app.config())
            select(app,"machine","Machine B")
            code_b=cam.generate_gcode(app.contours,app.config())
            assert "START A" in code_a and "END A" in code_a and "START B" not in code_a
            assert "START B" in code_b and "END B" in code_b and "START A" not in code_b
            assert cam.parse_gcode_moves(code_a)==cam.parse_gcode_moves(code_b)
            assert app.capture_profile("machine")==b
            app.vars["feed"].set(610);app.update()
            assert "Modified" in app.profile_states["setup"].get()
            assert app.profiles["setup"]["2T carbon"]["vars"]["feed"]==600
            assert app.save_profile("setup")
            assert app.profiles["setup"]["2T carbon"]["vars"]["feed"]==610
            app.vars["feed"].set(600);assert app.save_profile("setup")

            # Applying an invalid payload leaves all actual values and geometry intact.
            app.vars["onion_split"].set(True)
            app.vars["wall_finish"].set(False);app.vars["onion_skin_enabled"].set(False)
            baseline=app.job_snapshot()
            app.profiles["setup"]["bad"]=copy.deepcopy(thin)
            app.profiles["setup"]["bad"]["vars"]["feed"]=-1
            app.profile_names["setup"].set("bad")
            with mock.patch.object(cam.messagebox,"showerror") as error:
                assert not app.load_profile("setup") and error.called
            assert app.job_snapshot()==baseline and app.profile_active["setup"]=="2T carbon"
            del app.profiles["setup"]["bad"]
            app.vars["onion_split"].set(False);app.sync_onion_split()
            before=(root/"profiles.json").read_bytes();library=copy.deepcopy(app.profiles)
            app.vars["feed"].set(620)
            with mock.patch.object(app,"write_settings_file",side_effect=OSError("read-only")),mock.patch.object(cam.messagebox,"showerror"):
                assert not app.save_profile("setup")
            assert app.profiles==library and (root/"profiles.json").read_bytes()==before
            app.vars["feed"].set(600)

            # The job restores snapshots even when the identically named library entry changes.
            job=root/"profile-test.cfrpcam"
            with mock.patch.object(cam.filedialog,"asksaveasfilename",return_value=str(job)):
                assert app.save_job()
            saved=app.job_snapshot()
            app.vars["feed"].set(650);assert app.save_profile("setup")
            select(app,"machine","기존 기계")
            with mock.patch.object(app,"confirm_job_replace",return_value=True):assert app.load_job_file(str(job))
            actual=json.loads(app.job_snapshot());expected=json.loads(saved)
            assert actual==expected, {k:(expected[k],actual[k]) for k in expected if expected[k]!=actual[k]}
            assert app.profile_active["setup"]=="" and app.profiles["setup"]["2T carbon"]["vars"]["feed"]==650
            select(app,"setup","2T carbon")
            with mock.patch.object(cam.simpledialog,"askstring",return_value="Thin plate"):
                assert app.rename_profile("setup")
            assert "2T carbon" not in app.profiles["setup"] and app.vars["feed"].get()==650
            app.save_settings();expected_profiles=copy.deepcopy(app.profiles)
            app.update();app.destroy();app=cam.App();app.update()
            assert app.profiles==expected_profiles and app.vars["feed"].get()==650
            assert app.profile_active["setup"]=="Thin plate"
            app.show_profile_settings();app.update()
            assert app.settings_notebook.select()==str(app.settings_tab)
            assert app.profile_combos["machine"][1].winfo_viewable()
            # A read-only EXE directory falls back to AppData and reads that same library next time.
            writer=app.write_settings_file
            portable=root/"readonly"/"profiles.json";fallback=root/"appdata"/"profiles.json"
            def reject_portable(path,data):
                if Path(path)==portable:raise PermissionError("test portable read-only")
                writer(path,data)
            with mock.patch.object(app,"executable_dir",return_value=str(portable.parent)),mock.patch.object(app,"appdata_settings_path",return_value=str(fallback.parent/"settings.json")),mock.patch.object(app,"write_settings_file",side_effect=reject_portable):
                app.write_profiles()
                assert Path(app.profile_file_path())==fallback
                assert json.loads(fallback.read_text(encoding="utf-8"))["setup"]==app.profiles["setup"]
            with mock.patch.object(cam.messagebox,"askyesno",return_value=True):assert app.delete_profile("setup")
            assert "Thin plate" not in app.profiles["setup"] and app.vars["feed"].get()==650

            # Malformed library never overwrites the original on startup or Save.
            app.update();app.destroy();(root/"profiles.json").write_text('{"broken":true}',encoding="utf-8")
            app=cam.App();app.update()
            assert app._profiles_load_error
            before=(root/"profiles.json").read_bytes()
            with mock.patch.object(cam.simpledialog,"askstring",return_value="New"),mock.patch.object(cam.messagebox,"showerror"):
                assert not app.save_profile("machine",save_as=True)
            assert (root/"profiles.json").read_bytes()==before
        finally:
            app.update();app.destroy()
print("PROFILES_GUI_OK")
