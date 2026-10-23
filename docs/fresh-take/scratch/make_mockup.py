import json
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/docs/fresh-take/'
t = open(D+'scratch/template.html', encoding='utf-8').read()
j = open(D+'scratch/frames.json', encoding='utf-8').read()
open(D+'mockup.html', 'w', encoding='utf-8').write(t.replace('/*FRAMES_JSON*/', j))
print('ok', len(t)+len(j))
