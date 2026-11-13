import json

with open('/Users/nb/google/Antigravity/工作/运营/价单/sandbox/hk_landmarks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 1. 为已有学校补全 gender (性别) 和 curriculum (课程体系)
SCHOOL_GENDER_CURRICULUM = {
    'hku': {'gender': '男女校', 'curriculum': '高等教育学士/硕博学位课程'},
    'polyu': {'gender': '男女校', 'curriculum': '高等教育学士/硕博学位课程'},
    'cityu': {'gender': '男女校', 'curriculum': '高等教育学士/硕博学位课程'},
    'hkbu': {'gender': '男女校', 'curriculum': '高等教育学士/硕博学位课程'},
    'cuhk': {'gender': '男女校', 'curriculum': '高等教育学士/硕博学位课程'},
    'hkust': {'gender': '男女校', 'curriculum': '高等教育学士/硕博学位课程'},
    'univ_lingnan': {'gender': '男女校', 'curriculum': '高等教育学士/硕博学位课程'},
    'univ_eduhk': {'gender': '男女校', 'curriculum': '高等教育学士/硕博学位课程'},
    'school_dbs': {'gender': '纯男校', 'curriculum': '香港 DSE / 国际 IB DP 双轨'},
    'school_dgs': {'gender': '纯女校', 'curriculum': '香港 DSE / 英国 A-Level 双轨'},
    'school_lasalle_col': {'gender': '纯男校', 'curriculum': '香港 DSE 文凭试 (Band 1A)'},
    'school_lasalle_pri': {'gender': '纯男校', 'curriculum': '全免资助名校精英课程'},
    'school_maryknoll': {'gender': '纯女校', 'curriculum': '香港 DSE 文凭试 (Band 1A)'},
    'school_spcc': {'gender': '男女校', 'curriculum': '香港 DSE / 国际 IB DP 双轨顶尖'},
    'school_spccps': {'gender': '男女校', 'curriculum': '直资一条龙校本优质双语课程'},
    'school_st_paul_col': {'gender': '纯男校', 'curriculum': '香港 DSE / 英国 IAL 国际课程'},
    'school_queens_col': {'gender': '纯男校', 'curriculum': '香港 DSE 文凭试 (官立状元首选)'},
    'school_kings_col': {'gender': '纯男校', 'curriculum': '香港 DSE 文凭试 (Band 1A)'},
    'school_st_paul_convent': {'gender': '纯女校', 'curriculum': '香港 DSE / 英国 IGCSE & A-Level'},
    'school_st_stephen_girls': {'gender': '纯女校', 'curriculum': '香港 DSE 文凭试 (Band 1A)'},
    'school_wah_yan_hk': {'gender': '纯男校', 'curriculum': '香港 DSE 文凭试 (耶稣会精英通识)'},
    'school_wah_yan_kln': {'gender': '纯男校', 'curriculum': '香港 DSE 文凭试 (理科与全人见长)'},
    'school_heep_yunn': {'gender': '纯女校', 'curriculum': '香港 DSE 文凭试 (文理体艺顶尖)'},
    'school_heep_yunn_pri': {'gender': '纯女校', 'curriculum': '34校网首屈一指名牌女小课程'},
    'school_st_mary': {'gender': '纯女校', 'curriculum': '香港 DSE 文凭试 (Band 1A)'},
    'school_dps': {'gender': '男女校', 'curriculum': '41校网名牌男女资助课程'},
    'school_st_joseph': {'gender': '纯男校', 'curriculum': '香港 DSE 文凭试 (喇沙修士会名门)'},
    'school_ying_wa': {'gender': '纯男校', 'curriculum': '香港 DSE 文凭试 (一条龙男校)'},
    'school_good_hope': {'gender': '纯女校', 'curriculum': '香港 DSE / 英国 GCE A-Level'},
    'school_st_peter_pri': {'gender': '男女校', 'curriculum': '11校网圣公会名门资助课程'},
    'school_hennessy_pri': {'gender': '男女校', 'curriculum': '12校网名牌官立小学课程'},
    'school_cis': {'gender': '男女校', 'curriculum': '国际文凭全阶段 (IB PYP / MYP / DP)'},
    'school_gsis': {'gender': '男女校', 'curriculum': '德国国际毕业文凭 (DIAP) / 国际 IB DP'},
    'school_isf': {'gender': '男女校', 'curriculum': '中文双语国际文凭 (IB 全阶段)'},
    'school_harrow': {'gender': '男女校', 'curriculum': '英国英格兰课程 / IGCSE / A-Level'},
    'school_hkis': {'gender': '男女校', 'curriculum': '美制课程标准 / 大学先修课程 AP'},
    'school_cdnis': {'gender': '男女校', 'curriculum': '国际文凭全阶段 IB (PYP / MYP / DP)'},
    'school_sis': {'gender': '男女校', 'curriculum': '新加坡教育部课程 / Cambridge IGCSE / IB DP'},
    'school_ycis': {'gender': '男女校', 'curriculum': '双语双文化校本课程 / IGCSE / IB DP'},
    'school_fis': {'gender': '男女校', 'curriculum': '法国国家教育部课程 / 国际部 IB DP 双轨'},
    'school_malvern': {'gender': '男女校', 'curriculum': '全阶段国际文凭 IB (PYP / MYP / DP)'},
    'school_vsa': {'gender': '男女校', 'curriculum': '一条龙双语国际文凭 (IB 全阶段)'},
    'school_rchk': {'gender': '男女校', 'curriculum': '英基旗下私立一条龙 IB (PYP / MYP / DP)'},
    'school_cais': {'gender': '男女校', 'curriculum': '加拿大亚伯达省课程 / 美制 AP'},
    'school_esf_island': {'gender': '男女校', 'curriculum': '英基国际课程 / IB DP / IBCP'},
    'school_esf_kgv': {'gender': '男女校', 'curriculum': '英基百年国际课程 / IB DP / BTEC'},
    'school_cky': {'gender': '男女校', 'curriculum': '校本一条龙双语课程 / IGCSE / IB DP'},
    'school_pui_ching': {'gender': '男女校', 'curriculum': '香港 DSE 文凭试 (百年中文母语顶流教学)'},
    'school_dbspd': {'gender': '纯男校', 'curriculum': '拔萃校本全人精英双语课程 (直升男拔)'},
    'school_dgjs': {'gender': '纯女校', 'curriculum': '全港第一私立女小神校课程 (直升女拔)'},
    'school_munsang': {'gender': '男女校', 'curriculum': '香港 DSE 文凭试 (41校网全人名校)'},
    'school_ying_wa_primary': {'gender': '纯男校', 'curriculum': '英华一条龙特色男校课程 (直升英华)'},
    'school_ktlms': {'gender': '纯女校', 'curriculum': '香港 DSE 文凭试 (41校网基督教女校)'},
    'school_wa_ying': {'gender': '男女校', 'curriculum': '香港 DSE 文凭试 (34校网 Band 1A)'},
    'school_ssc': {'gender': '男女校', 'curriculum': '香港 DSE / 国际 IB DP 双轨 (赤柱寄宿名校)'},
    'school_sjps': {'gender': '纯男校', 'curriculum': '12校网天主教传统名牌男小课程'},
    'school_shcc': {'gender': '纯女校', 'curriculum': '香港 DSE 文凭试 (薄扶林修会名门女校)'},
    'school_hkuga': {'gender': '男女校', 'curriculum': '港大同学会校本探究型双语课程 (一条龙直升)'},
    'school_stamford': {'gender': '男女校', 'curriculum': '美制课程标准 (AERO) / 国际 IB DP'},
    'school_aishk': {'gender': '男女校', 'curriculum': '澳洲新南威尔士高中文凭 (HSC) / 国际 IB DP'},
    'school_ais': {'gender': '男女校', 'curriculum': '纯美制课程标准 / 大学先修课程 AP'},
    'school_esf_peak': {'gender': '男女校', 'curriculum': '国际文凭小学项目 (IB PYP)'},
    'school_esf_bradbury': {'gender': '男女校', 'curriculum': '国际文凭小学项目 (IB PYP)'},
    'school_esf_south_island': {'gender': '男女校', 'curriculum': '英基国际课程 / IB DP / IBCP'},
    'school_wycombe_abbey': {'gender': '男女校', 'curriculum': '英格兰国家课程 (直通英美顶级寄宿公学)'},
    'school_shrewsbury': {'gender': '男女校', 'curriculum': '纯正英国国家小学课程 (Early Years & Primary)'},
    'school_nord_anglia': {'gender': '男女校', 'curriculum': '国际文凭 IB DP / 麻省理工及茱莉亚学院联名课程'}
}

for item in data:
    cid = item.get('id')
    if cid in SCHOOL_GENDER_CURRICULUM:
        item['gender'] = SCHOOL_GENDER_CURRICULUM[cid]['gender']
        item['curriculum'] = SCHOOL_GENDER_CURRICULUM[cid]['curriculum']

# 2. 新增 16 所全港关键名校
NEW_SCHOOLS = [
    {
        'id': 'school_pui_kiu_college',
        'category': 'famous_school',
        'sub_type': 'band1',
        'tier': 1,
        'name': '培侨书院 (Pui Kiu College)',
        'name_en': 'Pui Kiu College',
        'region': '新界',
        'district': '沙田/大围',
        'lat': 22.3638,
        'lng': 114.1755,
        'gender': '男女校',
        'school_type': '直资',
        'school_type_desc': '享有政府津贴并自收学费，课程与招生自主权极高，全港传统顶尖名门集中',
        'school_level': '一条龙贯通 (小一至中六)',
        'curriculum': '香港 DSE / 英国 IGCSE & A-Level / 国内高校直通双轨',
        'school_feature': '内地背景高净值家庭知名度断层第一 · 深港双轨直通清北与海外名校，覆盖沙田及大围新盘',
        'highlight': '内地高净值家庭首选直资神校，深港双轨教育标杆'
    },
    {
        'id': 'school_gt_college',
        'category': 'famous_school',
        'sub_type': 'band1',
        'tier': 1,
        'name': '优才（杨殷有娣）书院 (G.T. College)',
        'name_en': 'G.T. (Ellen Yeung) College',
        'region': '新界',
        'district': '将军澳/调景岭',
        'lat': 22.3082,
        'lng': 114.2520,
        'gender': '男女校',
        'school_type': '直资',
        'school_type_desc': '享有政府津贴并自收学费，课程与招生自主权极高，全港传统顶尖名门集中',
        'school_level': '一条龙贯通 (小一至中六)',
        'curriculum': '香港 DSE / 国际 IB DP 双轨',
        'school_feature': '全港资优天才儿童教育先锋 · 新港人家庭极抢手一条龙直资神校，IB成绩出众',
        'highlight': '资优教育一条龙直资名校，IB/DSE双轨顶流'
    },
    {
        'id': 'school_hkbuas',
        'category': 'famous_school',
        'sub_type': 'band1',
        'tier': 1,
        'name': '香港浸会大学附属学校王锦辉中小学 (HKBUAS)',
        'name_en': 'HKBUAS Wong Kam Fai Secondary & Primary School',
        'region': '新界',
        'district': '沙田/石门',
        'lat': 22.3892,
        'lng': 114.2115,
        'gender': '男女校',
        'school_type': '直资',
        'school_type_desc': '享有政府津贴并自收学费，课程与招生自主权极高，全港传统顶尖名门集中',
        'school_level': '一条龙贯通 (小一至中六)',
        'curriculum': '香港 DSE / 英国 GCE A-Level 双轨',
        'school_feature': '新界东第一直资一条龙名校 · 浸会大学大学资源支持，科技人文并重，考生成绩优异',
        'highlight': '新界东直资一条龙第一梯队神校，石门站旁现代名门'
    },
    {
        'id': 'school_logos_academy',
        'category': 'famous_school',
        'sub_type': 'band1',
        'tier': 1,
        'name': '香港华人基督教联会真道书院 (Logos Academy)',
        'name_en': 'HKCCCU Logos Academy',
        'region': '新界',
        'district': '将军澳/调景岭',
        'lat': 22.3075,
        'lng': 114.2542,
        'gender': '男女校',
        'school_type': '直资',
        'school_type_desc': '享有政府津贴并自收学费，课程与招生自主权极高，全港传统顶尖名门集中',
        'school_level': '一条龙贯通 (11年制贯通基础至高中)',
        'curriculum': '香港 DSE / 国际 IB DP 双轨',
        'school_feature': '全港首创11年贯通制直资名校 · 明星名流子女云集，学制紧凑高效',
        'highlight': '11年一贯制特色直资神校，明星家庭与社会精英首选'
    },
    {
        'id': 'school_st_margaret',
        'category': 'famous_school',
        'sub_type': 'band1',
        'tier': 1,
        'name': '圣玛加利男女英文中小学 (SMCESPS)',
        'name_en': 'St. Margaret Co-educational English Secondary & Primary',
        'region': '九龙',
        'district': '西九龙/南昌',
        'lat': 22.3278,
        'lng': 114.1552,
        'gender': '男女校',
        'school_type': '直资',
        'school_type_desc': '享有政府津贴并自收学费，课程与招生自主权极高，全港传统顶尖名门集中',
        'school_level': '一条龙贯通 (小一至中六)',
        'curriculum': '香港 DSE 文凭试 / 三语四语国际多语种',
        'school_feature': '西九龙核心直资一条龙神校 · 南昌站汇玺上盖优质生活圈，三语兼修及法德日西外语优势',
        'highlight': '西九龙高净值家庭争相报考直资一条龙，多语言特色卓越'
    },
    {
        'id': 'school_belilios',
        'category': 'famous_school',
        'sub_type': 'secondary',
        'tier': 1,
        'name': '庇理罗士女子中学 (Belilios Public School)',
        'name_en': 'Belilios Public School',
        'region': '港岛',
        'district': '天后/铜锣湾 (12校网)',
        'lat': 22.2848,
        'lng': 114.1950,
        'gender': '纯女校',
        'school_type': '官立',
        'school_type_desc': '政府全资开办与管理，免学费，完全按官立派位机制录取',
        'school_level': '中学阶段 (中一至中六)',
        'curriculum': '香港 DSE 文凭试 (Band 1A 女状元摇篮)',
        'school_feature': '全港官立女校之首 · 与皇仁书院齐名并列，联系轩尼诗道官小等，状元与政界菁英辈出',
        'highlight': '全港第一官立名门女校，与皇仁并称官校双璧'
    },
    {
        'id': 'school_hkuga_college',
        'category': 'famous_school',
        'sub_type': 'secondary',
        'tier': 1,
        'name': '港大同学会书院 (HKUGA College)',
        'name_en': 'HKUGA College',
        'region': '港岛',
        'district': '黄竹坑/深湾 (港岛南岸)',
        'lat': 22.2452,
        'lng': 114.1652,
        'gender': '男女校',
        'school_type': '直资',
        'school_type_desc': '享有政府津贴并自收学费，课程与招生自主权极高，全港传统顶尖名门集中',
        'school_level': '中学阶段 (中一至中六)',
        'curriculum': '香港 DSE / 国际 IB DP 双轨',
        'school_feature': '一条龙直升附中 · 紧邻黄竹坑港岛南岸豪宅圈与深湾游艇会，学术成绩全港名列前茅',
        'highlight': '港岛南区Band 1A顶尖直资中学，黄竹坑港岛南岸核心配套'
    },
    {
        'id': 'school_spc_primary',
        'category': 'famous_school',
        'sub_type': 'primary',
        'tier': 1,
        'name': '圣保罗书院小学 (SPCPS)',
        'name_en': "St. Paul's College Primary School",
        'region': '港岛',
        'district': '薄扶林/钢线湾',
        'lat': 22.2698,
        'lng': 114.1292,
        'gender': '纯男校',
        'school_type': '直资',
        'school_type_desc': '享有政府津贴并自收学费，课程与招生自主权极高，全港传统顶尖名门集中',
        'school_level': '小学阶段 (小一至小六)',
        'curriculum': '圣保罗校本男校精英双语课程',
        'school_feature': '直属升中直通圣保罗书院 (高比例直升) · 港岛西薄扶林百年名门男校附小',
        'highlight': '百年男校圣保罗书院直属小学，港岛西豪宅家庭首选'
    },
    {
        'id': 'school_st_stephen_prep',
        'category': 'famous_school',
        'sub_type': 'primary',
        'tier': 1,
        'name': '圣士提反书院附属小学 (SSCPC)',
        'name_en': "St. Stephen's College Preparatory School",
        'region': '港岛',
        'district': '赤柱 (东头湾道)',
        'lat': 22.2132,
        'lng': 114.2158,
        'gender': '男女校',
        'school_type': '直资',
        'school_type_desc': '享有政府津贴并自收学费，课程与招生自主权极高，全港传统顶尖名门集中',
        'school_level': '小学阶段 (小一至小六)',
        'curriculum': '寄宿制全人精英素质教育课程',
        'school_feature': '全港最美私家海湾寄宿附小 · 一条龙直升圣士提反书院，名流高净值家庭首选',
        'highlight': '全港唯一寄宿制名门直资附小，赤柱超大临海校园'
    },
    {
        'id': 'school_marymount_sec',
        'category': 'famous_school',
        'sub_type': 'secondary',
        'tier': 1,
        'name': '玛利曼中学 (Marymount Secondary School)',
        'name_en': 'Marymount Secondary School',
        'region': '港岛',
        'district': '跑马地 (12校网)',
        'lat': 22.2708,
        'lng': 114.1865,
        'gender': '纯女校',
        'school_type': '津贴',
        'school_type_desc': '非牟利机构办学、政府全额资助，免学费，按官方校网统一派位',
        'school_level': '中学阶段 (中一至中六)',
        'curriculum': '香港 DSE 文凭试 (Band 1A 名门女校)',
        'school_feature': '湾仔12校网传统名门天主教女校 · 直属玛利曼小学，跑马地豪宅家庭极度推崇',
        'highlight': '跑马地传统名门天主教女校，湾仔12校网核心代表'
    },
    {
        'id': 'school_marymount_pri',
        'category': 'famous_school',
        'sub_type': 'primary',
        'tier': 1,
        'name': '玛利曼小学 (Marymount Primary School)',
        'name_en': 'Marymount Primary School',
        'region': '港岛',
        'district': '跑马地/大坑 (12校网)',
        'lat': 22.2718,
        'lng': 114.1882,
        'gender': '纯女校',
        'school_type': '津贴',
        'school_type_desc': '非牟利机构办学、政府全额资助，免学费，按官方校网统一派位',
        'school_level': '小学阶段 (小一至小六)',
        'curriculum': '12校网优质资助名校课程',
        'school_feature': '直属玛利曼中学 (升中直通优势) · 跑马地与大坑豪宅圈极抢手名牌女小',
        'highlight': '12校网龙头名牌女小，直属玛利曼中学'
    },
    {
        'id': 'school_pui_ching_primary',
        'category': 'famous_school',
        'sub_type': 'primary',
        'tier': 1,
        'name': '香港培正小学 (Pui Ching Primary School)',
        'name_en': 'Pui Ching Primary School',
        'region': '九龙',
        'district': '何文田 (34校网)',
        'lat': 22.3168,
        'lng': 114.1752,
        'gender': '男女校',
        'school_type': '私立',
        'school_type_desc': '自负盈亏自主办学，全港公开自主面试招生，不受校网户籍限制',
        'school_level': '幼小贯通 (幼稚园至小学六年级)',
        'curriculum': '培正百年名门双语母语并重特色课程',
        'school_feature': '何文田核心地标名门私立附小 · 联系直升香港培正中学，政商文豪与学界泰斗摇篮',
        'highlight': '何文田百年私立名牌附小，联系香港培正中学'
    },
    {
        'id': 'school_wah_yan_primary',
        'category': 'famous_school',
        'sub_type': 'primary',
        'tier': 1,
        'name': '番禺会所华仁小学 (PUA Wah Yan Primary)',
        'name_en': 'Pun U Association Wah Yan School',
        'region': '港岛',
        'district': '北角/宝马山 (14校网)',
        'lat': 22.2905,
        'lng': 114.2045,
        'gender': '纯男校',
        'school_type': '津贴',
        'school_type_desc': '非牟利机构办学、政府全额资助，免学费，按官方校网统一派位',
        'school_level': '小学阶段 (小一至小六)',
        'curriculum': '天主教耶稣会名门男小素质教育课程',
        'school_feature': '直属香港华仁书院 (WYCHK，升中大比例直升) · 港岛东首屈一指名门男小',
        'highlight': '直属香港华仁书院名牌男小，港岛东名门首选'
    },
    {
        'id': 'school_true_light_hk',
        'category': 'famous_school',
        'sub_type': 'secondary',
        'tier': 1,
        'name': '香港真光中学 (True Light Middle School of HK)',
        'name_en': 'True Light Middle School of Hong Kong',
        'region': '港岛',
        'district': '铜锣湾/大坑 (12校网)',
        'lat': 22.2768,
        'lng': 114.1932,
        'gender': '纯女校',
        'school_type': '津贴',
        'school_type_desc': '非牟利机构办学、政府全额资助，免学费，按官方校网统一派位',
        'school_level': '幼小中贯通 (幼稚园至高中六年级)',
        'curriculum': '香港 DSE 文凭试 (百年基督教传统名门)',
        'school_feature': '港岛大坑百年传统名门女校 · 幼小中一体，学风端庄严谨，与九龙真光遥相呼应',
        'highlight': '大坑百年名门女校，幼小中一体化优质教育'
    },
    {
        'id': 'school_uwc_hk',
        'category': 'famous_school',
        'sub_type': 'international',
        'tier': 1,
        'name': '香港李宝椿联合世界书院 (Li Po Chun UWC)',
        'name_en': 'Li Po Chun United World College of Hong Kong',
        'region': '新界',
        'district': '沙田/马鞍山 (乌溪沙)',
        'lat': 22.4342,
        'lng': 114.2422,
        'gender': '男女校',
        'school_type': '国际',
        'school_type_desc': '采用全英/双语国际课程(IB/AP/英国体系)，面向海外名校升学，高净值家庭首选',
        'school_level': '国际预科高中寄宿 (Grade 11-12)',
        'curriculum': '国际文凭预科课程 (IB DP)',
        'school_feature': '全球仅18所的UWC联合世界书院之一 · 联合国式跨国多元文化，牛剑常春藤录取神话',
        'highlight': '全球18所UWC之一，常春藤与牛剑传奇名校'
    },
    {
        'id': 'school_esf_shatin_college',
        'category': 'famous_school',
        'sub_type': 'international',
        'tier': 1,
        'name': '英基沙田学院 (ESF Sha Tin College)',
        'name_en': 'ESF Sha Tin College',
        'region': '新界',
        'district': '沙田/火炭 (丽坪路)',
        'lat': 22.3985,
        'lng': 114.2028,
        'gender': '男女校',
        'school_type': '国际',
        'school_type_desc': '采用全英/双语国际课程(IB/AP/英国体系)，面向海外名校升学，高净值家庭首选',
        'school_level': '中学阶段 (Year 7至Year 13)',
        'curriculum': '国际文凭中学及预科课程 (IB MYP / DP)',
        'school_feature': '英基旗下学术成绩常年全港排第一的分校 · IB状元摇篮，九龙及新界东豪宅家庭顶尖之选',
        'highlight': '英基学术表现全港第一分校，火炭豪宅圈顶尖IB名门'
    }
]

# 3. 新增 3 家全港超级商业新地标
NEW_MALLS = [
    {
        'id': 'mall_kai_tak_sports_park',
        'category': 'shopping_mall',
        'sub_type': 'mega_flagship',
        'tier': 1,
        'name': '启德体育园零售馆 (Kai Tak Sports Park Retail)',
        'name_en': 'Kai Tak Sports Park Retail Mall',
        'region': '九龙',
        'district': '启德',
        'lat': 22.3218,
        'lng': 114.1972,
        'mall_level': '区域枢纽旗舰',
        'mall_scale': '约 70 万平方呎',
        'mall_feature': '2025全新超级地标，全港最大运动生活休闲购物中心，三大场馆海滨露天餐饮与逾200间旗舰名店',
        'highlight': '2025启德超级新地标，70万呎全港最大运动生活休闲零售综合体'
    },
    {
        'id': 'mall_west_kowloon_hsr',
        'category': 'shopping_mall',
        'sub_type': 'mega_luxury',
        'tier': 1,
        'name': '西九高铁路巨无霸商业 (新鸿基西九地标)',
        'name_en': 'West Kowloon HSR Station Mega Hub',
        'region': '九龙',
        'district': '西九龙/高铁站',
        'lat': 22.3055,
        'lng': 114.1672,
        'mall_level': '全港顶奢旗舰',
        'mall_scale': '约 260 万平方呎 (商办巨无霸)',
        'mall_feature': '新鸿基西九龙高铁上盖超级商业地标，全港罕见超大规模商业与绿色连廊，直接连通全国高铁网',
        'highlight': '新鸿基西九高铁上盖260万呎超级商业地标，辐射西九龙全境豪宅'
    },
    {
        'id': 'mall_tai_po_mega',
        'category': 'shopping_mall',
        'sub_type': 'mega_flagship',
        'tier': 1,
        'name': '大埔超级城 (Tai Po Mega Mall)',
        'name_en': 'Tai Po Mega Mall',
        'region': '新界',
        'district': '大埔市中心',
        'lat': 22.4518,
        'lng': 114.1702,
        'mall_level': '区域枢纽旗舰',
        'mall_scale': '约 60 万平方呎 (A-E五大区)',
        'mall_feature': '新界东北规模最大旗舰综合购物中心，逾180间国际名店与大型超市，覆盖科学园白石角与大埔新盘',
        'highlight': '新界东北规模最大型购物中心，白石角与大埔新盘核心商业配套'
    }
]

# 合并去重检查
existing_ids = {x.get('id') for x in data}

added_schools = 0
for s in NEW_SCHOOLS:
    if s['id'] not in existing_ids:
        data.append(s)
        existing_ids.add(s['id'])
        added_schools += 1
    else:
        # update
        idx = next(i for i, x in enumerate(data) if x.get('id') == s['id'])
        data[idx].update(s)

added_malls = 0
for m in NEW_MALLS:
    if m['id'] not in existing_ids:
        data.append(m)
        existing_ids.add(m['id'])
        added_malls += 1
    else:
        idx = next(i for i, x in enumerate(data) if x.get('id') == m['id'])
        data[idx].update(m)

print(f"Successfully added/updated {added_schools} new schools!")
print(f"Successfully added/updated {added_malls} new malls!")
print(f"Total landmarks in database now: {len(data)}")

# 写入
with open('/Users/nb/google/Antigravity/工作/运营/价单/sandbox/hk_landmarks.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("hk_landmarks.json completely upgraded to 100 points version!")
