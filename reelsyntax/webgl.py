PROBE = r'''() => {
  let canvas=document.querySelector('#rs-webgl');
  if(!canvas){canvas=document.createElement('canvas');canvas.id='rs-webgl';document.body.appendChild(canvas);}
  const gl=canvas.getContext('webgl2',{preserveDrawingBuffer:true,alpha:false,antialias:false});
  if(!gl) throw new Error('WebGL2 is unavailable in the isolated Chromium worker; no visual substitution is made');
  const debug=gl.getExtension('WEBGL_debug_renderer_info');
  return {version:gl.getParameter(gl.VERSION),shading_language:gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
    renderer:gl.getParameter(debug?debug.UNMASKED_RENDERER_WEBGL:gl.RENDERER),max_texture_size:gl.getParameter(gl.MAX_TEXTURE_SIZE)};
}'''

DRAW = r'''({width,height,params,frame,frames,seed}) => {
  const canvas=document.querySelector('#rs-webgl');
  const gl=canvas.getContext('webgl2');
  canvas.width=width;canvas.height=height;
  if(!canvas.rsProgram){
    function compile(type,source){
      const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
      return shader;
    }
    const vertex=compile(gl.VERTEX_SHADER,`#version 300 es
      void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.-1.,0.,1.);}`);
    const fragment=compile(gl.FRAGMENT_SHADER,`#version 300 es
precision highp float;
uniform vec2 resolution;
uniform float phase;
uniform vec3 background;
uniform vec3 primary;
uniform vec3 accent;
out vec4 fragColor;
mat2 rotate(float a){return mat2(cos(a),-sin(a),sin(a),cos(a));}
float torus(vec3 p,vec2 r){return length(vec2(length(p.xz)-r.x,p.y))-r.y;}
vec2 field(vec3 p){
  vec3 q=p-vec3(0.,0.08,0.);q.xz=rotate(phase*.24)*q.xz;
  vec3 a=q;a.xy=rotate(.65+.12*sin(phase))*a.xy;
  float outer=torus(a,vec2(1.03,.17));
  vec3 b=q;b.yz=rotate(1.17)*b.yz;
  float inner=torus(b,vec2(.70,.115));
  float sculpture=min(outer,inner);
  float floorDistance=p.y+1.24;
  return floorDistance<sculpture?vec2(floorDistance,0.):vec2(sculpture,outer<inner?1.:2.);
}
vec3 normalAt(vec3 p){vec2 e=vec2(.001,0.);return normalize(vec3(field(p+e.xyy).x-field(p-e.xyy).x,field(p+e.yxy).x-field(p-e.yxy).x,field(p+e.yyx).x-field(p-e.yyx).x));}
float shadow(vec3 p,vec3 light){float result=1.,t=.025;for(int i=0;i<28;i++){float h=field(p+light*t).x;result=min(result,12.*h/t);t+=clamp(h,.025,.25);if(t>7.)break;}return clamp(result,0.,1.);}
vec3 lightAt(vec3 p,vec3 n,vec3 v,vec3 l,vec3 energy,vec3 color,float metal,float rough){
  float nl=max(dot(n,l),0.),nv=max(dot(n,v),.001);
  vec3 h=normalize(l+v);float nh=max(dot(n,h),0.),vh=max(dot(v,h),0.);
  float a=rough*rough,a2=a*a,den=nh*nh*(a2-1.)+1.;
  float d=a2/(3.141593*den*den);
  float k=(rough+1.)*(rough+1.)/8.;
  float g=(nl/(nl*(1.-k)+k))*(nv/(nv*(1.-k)+k));
  vec3 f0=mix(vec3(.04),color,metal),f=f0+(1.-f0)*pow(1.-vh,5.);
  vec3 brdf=(1.-f)*(1.-metal)*color/3.141593+(d*g*f)/(4.*max(nl,.001)*nv);
  return brdf*energy*nl*shadow(p+n*.006,l);
}
void main(){
  vec2 uv=(gl_FragCoord.xy*2.-resolution)/resolution.y;
  vec3 origin=vec3(2.65,1.5,4.9),target=vec3(0.,-.1,0.);
  vec3 forward=normalize(target-origin),right=normalize(cross(forward,vec3(0.,1.,0.))),up=cross(right,forward);
  vec3 ray=normalize(forward*2.35+right*uv.x+up*uv.y);
  float t=0.;vec2 hit=vec2(0.);bool found=false;
  for(int i=0;i<112;i++){hit=field(origin+ray*t);if(hit.x<.001){found=true;break;}t+=hit.x*.85;if(t>22.)break;}
  vec3 color=background;
  if(found){
    vec3 p=origin+ray*t,n=normalAt(p),v=-ray;
    vec3 base=hit.y<.5?background:(hit.y<1.5?accent:primary);
    float metal=hit.y<.5?.08:.88,rough=hit.y<.5?.5:.28;
    float ao=clamp(field(p+n*.13).x/.13,.3,1.);
    color=base*.12*ao;
    color+=lightAt(p,n,v,normalize(vec3(-2.,5.,3.)),vec3(5.8,5.1,4.1),base,metal,rough);
    color+=lightAt(p,n,v,normalize(vec3(3.,2.,-2.)),vec3(3.4,4.5,5.5),base,metal,rough);
    color+=lightAt(p,n,v,normalize(vec3(-1.,.3,-3.)),vec3(2.4,2.0,1.5),base,metal,rough);
    color=mix(color,background,1.-exp(-t*.018));
  }
  color=color/(vec3(1.)+color);
  color=mix(color*12.92,1.055*pow(max(color,vec3(0.)),vec3(1./2.4))-.055,step(vec3(.0031308),color));
  fragColor=vec4(color,1.);
}`);
    const program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.deleteShader(vertex);gl.deleteShader(fragment);canvas.rsProgram=program;
  }
  const program=canvas.rsProgram;gl.useProgram(program);gl.viewport(0,0,width,height);
  gl.uniform2f(gl.getUniformLocation(program,'resolution'),width,height);
  gl.uniform1f(gl.getUniformLocation(program,'phase'),frame/Math.max(1,frames-1)*Math.PI*2+seed*.001);
  function linear(hex){return [1,3,5].map(i=>{const c=parseInt(hex.slice(i,i+2),16)/255;return c<=.04045?c/12.92:Math.pow((c+.055)/1.055,2.4);});}
  for(const [name,hex] of [['background',params.background||'#181e23'],['primary',params.foreground||'#526268'],['accent',params.accent||'#c3a16e']])
    gl.uniform3fv(gl.getUniformLocation(program,name),linear(hex));
  gl.drawArrays(gl.TRIANGLES,0,3);gl.finish();
  if(gl.isContextLost() || gl.getError()!==gl.NO_ERROR)throw new Error('WebGL draw failed or context was lost');
  return [];
}'''
