import requests, time
time.sleep(3)

BASE = 'http://localhost:8000'

# Sign up
r = requests.post(f'{BASE}/api/v1/auth/signup', json={'name':'Test','email':'t@t.com','password':'test123'})
token = r.json()['token']
h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
print('=== Signed up OK ===\n')

# Test 1: Short claim (< 10 words)
text1 = 'Is Modi prime minister of India?'
r = requests.post(f'{BASE}/api/v1/analyze', headers=h, json={'text': text1})
d = r.json()
print(f'SHORT CLAIM: "{text1}"')
print(f'  Result: {d["prediction"]} | Confidence: {d["confidence"]:.1f}% | Tier: {d["confidence_tier"]} | Quality: {d["input_quality"]}\n')

# Test 2: Headline (10-30 words)
text2 = 'Breaking news the government has announced new renewable energy subsidies that will reduce carbon emissions significantly over next decade'
r = requests.post(f'{BASE}/api/v1/analyze', headers=h, json={'text': text2})
d = r.json()
print(f'HEADLINE: "{text2[:60]}..."')
print(f'  Result: {d["prediction"]} | Confidence: {d["confidence"]:.1f}% | Tier: {d["confidence_tier"]} | Quality: {d["input_quality"]}\n')

# Test 3: Full article (30+ words)
text3 = 'The government has announced new renewable energy subsidies that will reduce carbon emissions by 30 percent over the next decade according to official reports from the energy department and climate scientists who have been studying the effects of current policies on global warming trends and atmospheric carbon levels.'
r = requests.post(f'{BASE}/api/v1/analyze', headers=h, json={'text': text3})
d = r.json()
print(f'FULL ARTICLE: "{text3[:60]}..."')
print(f'  Result: {d["prediction"]} | Confidence: {d["confidence"]:.1f}% | Tier: {d["confidence_tier"]} | Quality: {d["input_quality"]}\n')

# Test 4: Too short (should be rejected)
r = requests.post(f'{BASE}/api/v1/analyze', headers=h, json={'text': 'hi'})
print(f'TOO SHORT: status={r.status_code}, response={r.json()}')
