"""Extract the strongest meaningful hue instead of averaging unrelated colors."""
import colorsys
from collections import defaultdict

def dominant_color(pixels):
 colored=[];neutral=[]
 for pixel in pixels:
  if len(pixel)>3 and pixel[3]<128:continue
  r,g,b=[max(0,min(255,int(c))) for c in pixel[:3]]
  h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
  if v<.12:continue
  neutral.append((r,g,b))
  if s>=.18 and v>=.20:colored.append((r,g,b,h,s,v))
 if not colored:
  if not neutral:return '#a8a8b0'
  value=round(sum(sum(p)/3 for p in neutral)/len(neutral));value=max(125,min(220,value))
  return '#'+f'{value:02x}'*3
 # Merge neighboring hue bins so reds across the 0/360 boundary stay together.
 bins=defaultdict(list)
 for sample in colored:bins[int(sample[3]*36)%36].append(sample)
 def weight(sample):return (.35+.65*sample[4])*(sample[5]**1.5)
 scores={key:sum(weight(p) for neighbor in ((key-1)%36,key,(key+1)%36) for p in bins[neighbor]) for key in list(bins)}
 winning=max(scores,key=lambda key:(scores[key],-key))
 group=[p for neighbor in ((winning-1)%36,winning,(winning+1)%36) for p in bins[neighbor]]
 total=sum(weight(p) for p in group)
 rgb=[sum(p[i]*weight(p) for p in group)/total/255 for i in range(3)]
 hue,saturation,value=colorsys.rgb_to_hsv(*rgb)
 # Preserve the winning hue while keeping text/borders legible on dark cards.
 rgb=colorsys.hsv_to_rgb(hue,min(.72,max(.22,saturation)),min(.95,max(.72,value)))
 return '#'+''.join(f'{round(c*255):02x}' for c in rgb)

def from_image(path):
 import gi
 gi.require_version('GdkPixbuf','2.0')
 from gi.repository import GdkPixbuf
 image=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path),80,80,True)
 raw=image.get_pixels();stride=image.get_rowstride();channels=image.get_n_channels()
 pixels=[tuple(raw[y*stride+x*channels:y*stride+x*channels+channels]) for y in range(image.get_height()) for x in range(image.get_width())]
 return dominant_color(pixels)

def tinted_surface(accent):
 rgb=[int(accent[i:i+2],16) for i in (1,3,5)]
 return '#'+''.join(f'{round(16+c*.10):02x}' for c in rgb)
