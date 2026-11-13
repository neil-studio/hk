import json

with open('/Users/nb/google/Antigravity/工作/运营/价单/sandbox/hk_landmarks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 权威规范校名/商场名更正字典
NAME_CORRECTIONS = {
    # 1. 沪江维多利亚学校 (VSA)
    'school_vsa': {
        'name': '沪江维多利亚学校 (VSA)',
        'name_en': 'Victoria Shanghai Academy',
        'highlight': '港岛深湾知名一条龙双语IB名校，沪江大学香港同学会创办'
    },
    # 2. 宣道国际学校 (CAIS)
    'school_cais': {
        'name': '宣道国际学校 (CAIS)',
        'name_en': 'Christian Alliance International School',
        'highlight': '九龙知名国际学校，加拿大亚伯达省课程与AP体系，蝴蝶谷旗舰校舍'
    },
    # 3. 圣保罗男女中学附属小学 (SPCCPS)
    'school_spccps': {
        'name': '圣保罗男女中学附属小学 (SPCCPS)',
        'name_en': "St. Paul's Co-educational College Primary School",
        'highlight': '港岛南区顶尖直资小学，100%直升圣保罗男女中学神校'
    },
    # 4. 哈罗香港国际学校 (Harrow)
    'school_harrow': {
        'name': '哈罗香港国际学校 (Harrow)',
        'name_en': 'Harrow International School Hong Kong',
        'highlight': '全港唯一纯正英国贵族寄宿制名校，英国九大公学名门传承'
    },
    # 5. 香港加拿大国际学校 (CDNIS)
    'school_cdnis': {
        'name': '香港加拿大国际学校 (CDNIS)',
        'name_en': 'Canadian International School of Hong Kong',
        'highlight': '港岛南区全阶段 IB 一条龙顶尖国际名校 (PYP/MYP/DP)'
    },
    # 6. 新加坡国际学校(香港) (SISHK)
    'school_sis': {
        'name': '新加坡国际学校 (SISHK)',
        'name_en': 'Singapore International School (Hong Kong)',
        'highlight': '新加坡教育部在港唯一海外名校，数理与中英双语顶尖'
    },
    # 7. 保良局蔡继有学校 (PLK CKY)
    'school_cky': {
        'name': '保良局蔡继有学校 (PLK CKY)',
        'name_en': 'Po Leung Kuk Choi Kai Yau School',
        'highlight': '知名一条龙非牟利私立名校，IB成绩顶尖，状元辈出'
    },
    # 8. 西九龙高铁站上盖商业地标 (新鸿基地标商业)
    'mall_west_kowloon_hsr': {
        'name': '西九龙高铁站上盖商业地标 (新鸿基地标商业)',
        'name_en': 'West Kowloon High Speed Rail Station Landmark Commercial',
        'highlight': '新鸿基西九高铁上盖260万呎超级商业地标，辐射西九龙全境豪宅'
    },
    # 9. 双子汇 (The Twins / 启德崇光百货)
    'mall_twins_sogo': {
        'name': '双子汇 (The Twins / 启德崇光百货)',
        'name_en': 'The Twins (SOGO Kai Tak)',
        'highlight': '启德双子塔全新商业地标，涵盖九龙最大日式百货与生活零售娱乐综合体'
    }
}

corrected_count = 0
for item in data:
    cid = item.get('id')
    if cid in NAME_CORRECTIONS:
        corr = NAME_CORRECTIONS[cid]
        print(f"Correcting [{cid}]: {item.get('name')} -> {corr['name']}")
        item['name'] = corr['name']
        if 'name_en' in corr:
            item['name_en'] = corr['name_en']
        if 'highlight' in corr:
            item['highlight'] = corr['highlight']
        corrected_count += 1

print(f"Total corrected landmarks: {corrected_count}")

with open('/Users/nb/google/Antigravity/工作/运营/价单/sandbox/hk_landmarks.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("hk_landmarks.json updated with canonical names!")
