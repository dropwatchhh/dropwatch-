import re, json, glob
rows=[]
for f in glob.glob('/tmp/rl_*.log'):
    for l in open(f):
        if 'GAITCHK' in l: rows.append(json.loads(l.split('GAITCHK ')[1]))
mins=[r['min'] for r in rows]
print('gait frames checked:',len(rows),' lowest sole point (m): %.4f  (negative = sinking)'%min(mins),' highest planted sole: %.4f'%max(m for r,m in zip(rows,mins) if True))
slip={'L':[],'R':[]}
for a,b in zip(rows,rows[1:]):
    if a['mode']!=b['mode'] or b['t']<=a['t']: continue
    for k in 'LR':
        if a['stance'][k] and b['stance'][k]: slip[k].append(abs(b[k][2]-a[k][2]))
for k in 'LR': print(k,'stance-foot drift per frame: mean %.4f m, max %.4f m over %d frame pairs'%(sum(slip[k])/max(1,len(slip[k])),max(slip[k]+[0]),len(slip[k])))
g=[json.loads(l.split('GRABCHK ')[1]) for f in glob.glob('/tmp/rl_*.log') for l in open(f) if 'GRABCHK' in l]
print('grab frames:',len(g),' max hand-to-bumper error (m): dz %.3f dy %.3f ; feet height min %.3f'%(max(abs(x['dz']) for x in g),max(abs(x['dy']) for x in g),min(x['foot'] for x in g)))
