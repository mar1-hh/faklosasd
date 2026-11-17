"""Desktop-card placement using final allocated sizes, in monitor coordinates."""
ORDER=('logtime','links','clock','system','calendar','notes','launcher','pomodoro')
def positions(width,height,sizes,prefs):
 margin=prefs['margin'];gap=round(18*prefs['scale']);top=62
 visible=prefs['visible'];saved=prefs['positions'];result={}
 def put(name,x,y):
  w,h=sizes[name];x,y=saved.get(name,(x,y))
  result[name]=(max(0,min(int(x),max(0,width-w))),max(32,min(int(y),max(32,height-h-12))))
 left=top
 for name in ('logtime','links'):
  put(name,margin,left)
  if visible[name]:left+=sizes[name][1]+gap
 put('clock',(width-sizes['clock'][0])//2,82)
 right=top
 for name in ('system','calendar','notes'):
  put(name,width-sizes[name][0]-margin,right)
  if visible[name]:right+=sizes[name][1]+gap
 put('launcher',(width-sizes['launcher'][0])//2,height-sizes['launcher'][1]-24)
 if 'pomodoro' in sizes:
  pw,ph=sizes['pomodoro']
  # Prefer the left edge; on smaller displays search free space along card edges.
  xs=[margin,width-pw-margin]
  ys=[left,top,height-ph-24]
  for name,(x,y) in list(result.items()):
   if visible[name]:
    w,h=sizes[name];xs.extend([x+w+gap,x-pw-gap]);ys.append(y+h+gap)
  candidates=[(x,y) for x in xs for y in ys]
  def free(x,y):
   if x<0 or y<32 or x+pw>width or y+ph>height-12:return False
   for name,(ox,oy) in result.items():
    if not visible[name]:continue
    ow,oh=sizes[name]
    if x<ox+ow+gap and ox<x+pw+gap and y<oy+oh+gap and oy<y+ph+gap:return False
   return True
  chosen=next(((x,y) for x,y in candidates if free(x,y)),(margin,left))
  put('pomodoro',*chosen)
 return result
