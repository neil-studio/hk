import json

with open('/Users/nb/google/Antigravity/工作/运营/价单/sandbox/hk_project_coords.json', 'r', encoding='utf-8') as f:
    projs = json.load(f)

# 精准微调坐标映射表
CALIBRATED_COORDS = {
    # 1. 东半山 Central Peak (司徒拔道18号)
    'Central Peak I': {'lat': 22.267850, 'lng': 114.179150},
    'Central Peak II': {'lat': 22.267230, 'lng': 114.179620},
    
    # 2. 何文田 朗贤峰 (忠孝街1号何文田站)
    '朗贤峰第IIA期': {'lat': 22.311380, 'lng': 114.182500},
    '朗贤峰第IIB期': {'lat': 22.310940, 'lng': 114.182900},
    
    # 3. 启德 天玺·天 (协调道10号)
    '天玺．天': {'lat': 22.332300, 'lng': 114.199100},
    '天玺．天第2期': {'lat': 22.331920, 'lng': 114.198600},
    
    # 4. 启德 天玺·海 (承丰道26号)
    '天玺．海第1期': {'lat': 22.312100, 'lng': 114.206650},
    '天玺．海第2A期': {'lat': 22.311805, 'lng': 114.206991},
    '天玺．海第2B期': {'lat': 22.311510, 'lng': 114.207330},
    
    # 5. 启德 维港·湾畔 (承丰道15号)
    '维港．湾畔第1A期': {'lat': 22.315350, 'lng': 114.203050},
    '维港．湾畔第1B期': {'lat': 22.315111, 'lng': 114.203313},
    '维港．湾畔第2B期': {'lat': 22.314870, 'lng': 114.203580},
    
    # 6. 启德 The Henley (沐泰街7号)
    'The Henley I': {'lat': 22.327050, 'lng': 114.198050},
    'The Henley II': {'lat': 22.326832, 'lng': 114.198228},
    'The Henley III': {'lat': 22.326620, 'lng': 114.198420},
    
    # 7. 启德 启德海湾 (承丰道15号)
    '启德海湾 1': {'lat': 22.316120, 'lng': 114.204050},
    '启德海湾 2': {'lat': 22.315740, 'lng': 114.204490},
    
    # 8. 红磡 首岸 (机利士南路)
    '首岸第1期': {'lat': 22.312980, 'lng': 114.188250},
    '首岸第2期': {'lat': 22.312620, 'lng': 114.188550},
    
    # 9. 启德 柏蔚森 (承景街2号)
    '柏蔚森 I': {'lat': 22.310900, 'lng': 114.209600},
    '柏蔚森 II': {'lat': 22.311380, 'lng': 114.209100},
    '柏蔚森 III': {'lat': 22.311150, 'lng': 114.209350},
    
    # 10. 笔架山 The Monet (延坪道9号)
    'The Monet 第2期': {'lat': 22.344400, 'lng': 114.180050},
    'The Monet 第3期': {'lat': 22.344700, 'lng': 114.180300},
    
    # 11. 马头角 壹沐 (木厂街)
    '壹沐第1期': {'lat': 22.316150, 'lng': 114.189150},
    '壹沐第2期': {'lat': 22.316400, 'lng': 114.189400},
    
    # 12. 启德 Miami Quay (承丰道23号)
    'Miami Quay I': {'lat': 22.311950, 'lng': 114.208250},
    'Miami Quay II': {'lat': 22.312400, 'lng': 114.207980}
}

calibrated_count = 0
for p in projs:
    name = p.get('name')
    if name in CALIBRATED_COORDS:
        old_lat, old_lng = p.get('lat'), p.get('lng')
        new_coords = CALIBRATED_COORDS[name]
        p['lat'] = new_coords['lat']
        p['lng'] = new_coords['lng']
        print(f"Calibrated: {name} from ({old_lat:.6f}, {old_lng:.6f}) to ({p['lat']:.6f}, {p['lng']:.6f})")
        calibrated_count += 1

print(f"\nSuccessfully calibrated {calibrated_count} project coordinates!")

with open('/Users/nb/google/Antigravity/工作/运营/价单/sandbox/hk_project_coords.json', 'w', encoding='utf-8') as f:
    json.dump(projs, f, ensure_ascii=False, indent=2)

print("hk_project_coords.json updated!")
