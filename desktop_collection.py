"""Read-only folder collection: files are opened in place, never moved."""
from pathlib import Path

def entries(folder):
 folder=Path(folder).expanduser()
 # Bound the displayed collection. Large folders remain available in Files.
 result=[]
 for path in folder.iterdir():
  if path.name.startswith('.'):continue
  result.append(path)
  if len(result)>=500:break
 return sorted(result,key=lambda path:path.name.casefold())
