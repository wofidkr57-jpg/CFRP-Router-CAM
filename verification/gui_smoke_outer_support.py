"""Verify automatic mode, warnings, ordering and persisted settings in real Tk."""
import sys,os,tempfile,copy,re
from pathlib import Path
from unittest import mock
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import cfrp_router_cam as cam
from test_outer_support import rect
with tempfile.TemporaryDirectory() as tmp:
 os.environ['CFRP_CAM_LANGUAGE']='en'
 with mock.patch.object(cam.App,'executable_dir',return_value=tmp),mock.patch.object(cam.App,'appdata_settings_path',return_value=str(Path(tmp)/'fallback.json')):
  app=cam.App()
  try:
   assert app.vars['outer_safe_strategy'].get()
   host=cam.Contour([(60,20),(90,20),(90,90),(20,90),(20,20),(30,20),(30,80),(80,80),(80,30),(60,30)],role='outer',forced_role='outer',object_name='U',layer='U')
   guest=rect(40,10,15,60,'GUEST');guest.layer='GUEST'
   app.contours=[host,guest];app.vars['sheet_w'].set(100);app.vars['sheet_h'].set(100)
   app.vars['tab_count'].set(0);app.vars['tool_wear_enabled'].set(False);app.vars['tool_change_enabled'].set(False)
   app.redraw();app.update()
   assert app.order_tree.get_children()[0]=='c1'
   with mock.patch.object(cam.messagebox,'askokcancel',return_value=True) as warning,mock.patch.object(cam.messagebox,'showerror') as error:
    app.make_gcode();assert not error.called,error.call_args_list
    assert warning.called
   assert re.findall(r'\(Contour \d+: .*?layer=([^,]+)',app.gcode)==['GUEST','U']
   assert id(host) in app.support_risk_ids and id(guest) in app.support_risk_ids
   assert app.config()['outer_safe_strategy'] is True
  finally:app.destroy()
print('OUTER_SUPPORT_GUI_OK')

