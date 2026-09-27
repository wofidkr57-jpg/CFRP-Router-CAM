import json,re,unittest,shutil,subprocess
from unittest import mock
from pathlib import Path
import cfrp_router_cam as cam


class GPUViewerTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node is required for the isolated JavaScript logic test')
    def test_js_batch_buffers_modes_camera_and_playback(self):
        # Pure JS with fake GL/DOM: no browser or actual GPU rendering is invoked.
        moves=[cam.Move3D((i,0,-2),(i+1,0,-2),False,1,restart=(i==50)) for i in range(20000)]
        html=cam.gpu_viewer_html(moves,dict(stock=6,tool_d=2))
        payload=re.search(r'<script id="data" type="application/json">(.*?)</script>',html).group(1)
        script=html.split('</script><script>')[1].split('</script>')[0]
        harness=r'''
const assert=require('node:assert/strict'),vm=require('node:vm');
const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
let bound,uploads=[],draws=[],uniforms={},queue=[],now=100;
const gl={ARRAY_BUFFER:1,STATIC_DRAW:2,DYNAMIC_DRAW:3,LINES:4,TRIANGLES:5,POINTS:6,
 createShader:()=>({}),shaderSource:()=>{},compileShader:()=>{},getShaderParameter:()=>true,
 createProgram:()=>({}),attachShader:()=>{},linkProgram:()=>{},getProgramParameter:()=>true,
 useProgram:()=>{},getAttribLocation:n=>0,getUniformLocation:(p,n)=>n,
 createBuffer:()=>({}),bindBuffer:(t,b)=>{bound=b},bufferData:(t,d,u)=>{bound.data=Array.from(d);uploads.push({b:bound,u})},
 bufferSubData:(t,o,d)=>{assert([...d].every(Number.isFinite));bound.data=Array.from(d)},
 enableVertexAttribArray:()=>{},vertexAttribPointer:()=>{},drawArrays:(m,o,n)=>{assert(n*6<=bound.data.length);draws.push({m,n,b:bound})},
 viewport:()=>{},clearColor:()=>{},clear:()=>{},uniformMatrix4fv:(n,t,v)=>{assert([...v].every(Number.isFinite));uniforms[n]=Array.from(v)},
 uniform1f:(n,v)=>{uniforms[n]=v},disable:()=>{},enable:()=>{},depthFunc:()=>{}};
const els={};function element(id){return els[id]??=( {value:id==='mode'?'line':id==='speed'?'20':0,checked:true,textContent:id==='data'?input.payload:'',style:{},dataset:{},clientWidth:1000,clientHeight:700,width:1000,height:700,
 getContext:()=>gl,addEventListener(n,f){this[n]=f},setPointerCapture:()=>{},getBoundingClientRect:()=>({left:0,top:0,width:1000,height:700}),click(){this.onclick()}})}
const ctx={document:{getElementById:element},window:{},devicePixelRatio:1,performance:{now:()=>now},requestAnimationFrame:f=>{queue.push(f);return queue.length}};
vm.runInNewContext(input.script,ctx);const canvas=element('view');assert.equal(canvas.dataset.ready,'true',element('error').textContent);
function frame(){draws=[];const todo=queue;queue=[];now+=16;todo.forEach(f=>f(now));assert.equal(draws.length,4)}
frame();assert.equal(uploads.length,5);assert.equal(draws[1].n,40000);const geometry=uploads.map(v=>v.b.data);
for(let i=0;i<10;i++){element('mode').value=i%2?'line':'depth';element('mode').onchange();frame();assert.equal(draws[1].m,i%2?gl.LINES:gl.TRIANGLES);assert.equal(draws[1].n,i%2?40000:120000)}
const initialMatrix=uniforms.u_matrix.slice();canvas.onpointerdown({pointerId:1,clientX:0,clientY:0,button:0});canvas.onpointermove({clientX:30,clientY:10});canvas.onpointerup();frame();assert.notDeepEqual(uniforms.u_matrix,initialMatrix);
canvas.wheel({preventDefault(){},deltaY:-100,clientX:400,clientY:200});frame();
element('seek').value=50.5;element('seek').oninput();frame();assert.equal(uploads[3].b.data[0],50.5);
element('stop').onclick();frame();assert.equal(uniforms.u_elapsed,0);element('play').onclick();frame();frame();assert(uniforms.u_elapsed>0);
assert.equal(uploads.length,5);[0,1,2,4].forEach(i=>assert.equal(uploads[i].b.data,geometry[i]));
assert.equal(uploads[2].b.data[0],50);assert.equal(uploads[0].b.data[12*50],50);
canvas.webglcontextlost({preventDefault(){}});assert.equal(canvas.dataset.ready,'error');
console.log('JS_LOGIC_OK 20000 moves, four batches, static buffers reused; no real GPU tested');
'''
        result=subprocess.run([shutil.which('node'),'-e',harness],input=json.dumps(dict(payload=payload,script=script)),text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_offline_payload_retains_discontinuities_and_time(self):
        moves=cam.parse_gcode_moves('G0 X0 Y0 Z5\nG1 Z-2 F500\nG1 X10\nM881\nG53 G0 Z-70\nG0 X20 Y10\nG0 Z5\nG1 Z-2\nG1 X30')
        html=cam.gpu_viewer_html(moves,dict(stock=6,tool_d=2,z_origin='Top'))
        payload=json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',html).group(1))
        self.assertEqual(len(payload['moves']),len(moves)*9)
        self.assertEqual(sum(payload['moves'][8::9]),1)
        self.assertEqual(sum(payload['moves'][6::9]),sum(m.seconds for m in moves))
        self.assertNotIn('src="http',html);self.assertIn("connect-src 'none'",html)
        self.assertIn('gl.STATIC_DRAW',html)

    def test_launcher_writes_actual_self_contained_local_file(self):
        with mock.patch.object(cam.webbrowser,'open',return_value=True) as opener:
            path=cam.open_gpu_viewer([cam.Move3D((0,0,5),(10,0,-2),False,1)],dict(stock=6,tool_d=2))
            try:
                self.assertTrue(Path(path).is_file());self.assertIn('CarbonCAM',Path(path).read_text(encoding='utf-8'))
                self.assertEqual(opener.call_args.args[0],Path(path).as_uri())
            finally:Path(path).unlink();Path(path).parent.rmdir()


if __name__=='__main__':unittest.main()
