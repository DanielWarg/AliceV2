import json, subprocess, sys, textwrap

def run(text):
    out = subprocess.check_output([sys.executable, "services/rl/verifier/response_verifier.py", "--text", text])
    return json.loads(out.decode("utf-8"))

# 1. Svenskt kort svar -> OK
def test_sv_ok_short():
    r = run("Detta är ett kort svenskt svar med åäö.")
    assert r["ok"] is True

# 2. För långt svar -> FAIL
def test_too_long_fails():
    r = run("långt " * 400)
    assert r["ok"] is False

# 3. Engelsk meta -> FAIL (banned pattern)
def test_english_meta_banned():
    r = run("As an AI, I cannot access the internet.")
    assert r["ok"] is False

# 4. Policy-ord -> FAIL
def test_policy_flag():
    r = run("Detta handlar om illegala instruktioner och bör fällas.")
    assert r["ok"] is False

# 5. Mattetal utan verktyg -> FAIL (claim_math_detected)
def test_claim_math_requires_tool():
    r = run("Svaret är 2+2 = 4 men jag räknar utan verktyg.")
    assert r["ok"] is False

# 6. Obalanserade code-fences -> FAIL
def test_unbalanced_code_fences():
    r = run("```python\nprint('hej')")
    assert r["ok"] is False
    assert any("unbalanced_code_fences" in x for x in r["reasons"])

# 7. För många markdown-headrar -> FAIL
def test_too_many_headers():
    md = "\n".join("# Rubrik" for _ in range(20))
    r = run(md)
    assert r["ok"] is False
    assert any(x.startswith("too_many_headers") for x in r["reasons"])

# 8. JSON välformad i code-fence -> OK
def test_json_block_ok():
    txt = """Detta är svenska text med åäö.
```json
{"text":"hej","ok":true}
```"""
    r = run(txt)
    assert r["ok"] is True

# 9. JSON med trailing comma -> repareras -> OK
def test_json_trailing_comma_repair():
    txt = """Svensk text med åäö.
```json
{"a":1,}
```"""
    r = run(txt)
    assert r["ok"] is True or any("json_parse_error_after_repair" not in x for x in r["reasons"])

# 10. JSON för många keys -> FAIL
def test_json_too_many_keys():
    inner = ",".join([f"\"k{i}\":{i}" for i in range(40)])
    txt = f"Svensk text med åäö.\n```json\n{{{inner}}}\n```"
    r = run(txt)
    assert r["ok"] is False
    assert any("json_too_many_keys" in x for x in r["reasons"])

# 11. Tid-claim utan verktyg -> FAIL
def test_time_claim_requires_tool():
    r = run("Klockan är 12:30 just nu.")
    assert r["ok"] is False
    assert any("claim_time_detected" in x for x in r["reasons"])

# 12. Väder-claim utan verktyg -> FAIL
def test_weather_claim_requires_tool():
    r = run("Vädret är 20 grader och soligt.")
    assert r["ok"] is False
    assert any("claim_weather_detected" in x for x in r["reasons"])

# 13. Språkdetektering – engelska utan svenska markörer -> FAIL
def test_language_detection():
    r = run("This is a short answer without Swedish words.")
    assert r["ok"] is False
    assert any("lang_check_failed" in x for x in r["reasons"])

# 14. Markdown + JSON i samma svar korrekt -> OK
def test_mixed_markdown_json_ok():
    txt = textwrap.dedent("""
    ## Sammanfattning
    Kort svensk text med åäö.
    ```json
    {"note":"ok"}
    ```
    """).strip()
    r = run(txt)
    assert r["ok"] is True

# 15. JSON-värde för långt -> FAIL
def test_json_value_too_long():
    long_val = "a"*9000
    txt = f"Svensk text med åäö.\n```json\n{{\"text\":\"{long_val}\"}}\n```"
    r = run(txt)
    assert r["ok"] is False
    assert any("json_value_too_long" in x for x in r["reasons"])