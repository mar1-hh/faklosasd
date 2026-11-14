#!/usr/bin/env python3
"""Original code-drawn 4K landscapes; no downloads or extra Python packages."""
from pathlib import Path
import math
import random
import subprocess
root = Path(__file__).resolve().parent / 'wallpapers'
palettes = [
 ('01-cyberpunk-rose','#080714','#291335','#f369b1','#5b97ff'),
 ('02-violet-horizon','#070713','#1c1740','#a085ff','#ee78b7'),
 ('03-teal-midnight','#030d15','#0d3039','#50dfc8','#9a91ff'),
 ('04-sakura-dusk','#130917','#432238','#f5b0c9','#b78bdc'),
 ('05-amber-orbit','#0c0a18','#332237','#f5b96c','#ed719d'),
 ('06-blue-solitude','#030915','#10264a','#72c4ed','#8b7ed8')]
for index,(name,bg,haze,accent,second) in enumerate(palettes):
 rng=random.Random(42+index)
 stars=''.join(f'<circle cx="{rng.randrange(3840)}" cy="{rng.randrange(1750)}" r="{rng.choice([1,1,2])}" fill="#ddd5ee" opacity="{rng.uniform(.15,.65):.2f}"/>' for _ in range(420))
 ridges=[]
 for layer in range(4):
  base=1400+layer*150
  points=[(0,2160),(0,base)]
  for x in range(0,4001,160): points.append((x,base-rng.randrange(80,430)))
  points += [(3840,2160)]
  ridges.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="{bg}" opacity="{.35+layer*.18}"/>')
 grid=''.join(f'<path d="M 1920 1440 L {x} 2160"/>' for x in range(-4800,9000,400))
 grid+=''.join(f'<path d="M 0 {1440+int((i/12)**2*720)} H 3840"/>' for i in range(1,13))
 svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="3840" height="2160" viewBox="0 0 3840 2160">
 <defs><radialGradient id="sky"><stop stop-color="{haze}"/><stop offset="1" stop-color="{bg}"/></radialGradient><linearGradient id="moon" x2=".3" y2="1"><stop stop-color="{accent}"/><stop offset="1" stop-color="{second}"/></linearGradient><linearGradient id="fade" x2="0" y2="1"><stop stop-color="{accent}" stop-opacity=".4"/><stop offset="1" stop-color="{bg}" stop-opacity="0"/></linearGradient></defs>
 <rect width="3840" height="2160" fill="url(#sky)"/>{stars}
 <ellipse cx="2000" cy="1100" rx="900" ry="680" fill="{accent}" opacity=".025"/>
 <circle cx="2030" cy="850" r="330" fill="url(#moon)" opacity=".8"/>
 <circle cx="2030" cy="850" r="359" fill="none" stroke="{accent}" stroke-width="2" opacity=".22"/>
 <path d="M 1400 1090 Q 2040 950 2680 600" fill="none" stroke="{second}" stroke-width="3" opacity=".5"/>
 {''.join(ridges)}<g stroke="{accent}" fill="none" opacity=".13" stroke-width="2">{grid}</g>
 <path d="M 0 1840 Q 1080 1780 1920 1900 T 3840 1810" stroke="{second}" opacity=".3" fill="none" stroke-width="3"/>
 </svg>'''
 source=root/(name+'.svg'); source.write_text(svg)
 subprocess.run(['convert','-background',bg,str(source),str(root/(name+'.png'))],check=True)
 print(name,flush=True)
