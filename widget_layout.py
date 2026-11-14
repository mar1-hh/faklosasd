"""Desktop-card placement using final allocated sizes, in monitor coordinates."""
ORDER=('logtime','links','clock','system','calendar','notes','launcher')
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
 return result
