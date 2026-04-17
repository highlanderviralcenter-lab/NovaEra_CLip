import json
def build_analysis_prompt(segments, duration, ctx): return "prompt"
def parse_ai_response(resp):
    try: return json.loads(resp) if isinstance(json.loads(resp), list) else json.loads(resp).get("cortes",[])
    except: return [{"start":0,"end":10,"title":"exemplo"}]
