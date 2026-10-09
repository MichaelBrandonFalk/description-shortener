import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from engine import LocalModel, ReviewNeeded, hard_errors
samples = [
'This durable stainless steel bottle is designed to hold 500 ml of water and is safe to clean in the dishwasher.',
'The Acme X2 camera records 4K video at 60 fps, weighs 450 g, includes a 24 mm lens, and carries a 2-year warranty.',
'This product does not contain nuts and is manufactured in a facility that does not process peanuts or tree nuts.',
'The kit includes 12 red bolts, 24 blue washers, 18 green nuts, 6 yellow brackets, 9 silver screws, 3 black handles, and 15 white spacers.'
]
model = LocalModel(Path('vendor'))
try:
    for original in samples:
        start=time.monotonic()
        try:
            result=model.shorten(original)
            print(json.dumps({'original':original,'result':result,'length':len(result),'errors':hard_errors(original,result),'seconds':round(time.monotonic()-start,1)}),flush=True)
        except ReviewNeeded as exc:
            print(json.dumps({'original':original,'blocked':str(exc),'seconds':round(time.monotonic()-start,1)}),flush=True)
finally:model.close()
